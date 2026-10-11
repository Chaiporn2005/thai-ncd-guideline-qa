"""LLM-as-a-judge through the Antigravity CLI (`agy -p`), cached and bounded (Track C).

The owner chose the judge: `agy --model gemini-3.8-flash-high` (decision 2026-10-11). `agy` is an agent with tools, not a bare completion API,
and the prompts carry text from the corpus, which is untrusted data. So every call:
  * runs in a fresh EMPTY temporary directory (nothing there to read or change),
  * uses `--sandbox` and `--disable-slash-commands`, never `--dangerously-skip-permissions`,
  * asks for a JSON answer checked against a schema (`--json-schema`) and the caller parses it strictly.
Every request is cached by a hash of (model, prompt, schema) in the same JSONL style as src/ncdqa/llm/client.py, so a run can be repeated from the
cache; a thinking model does not return identical text twice. Each cached row keeps the agy conversation id and token usage.
`map_calls` runs prompts in a small thread pool and stops the batch after repeated failures instead of retrying forever (quota unknown).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

DEFAULT_MODEL = "gemini-3.8-flash-high"
MAX_PROMPT_CHARS = 28000      # Windows command lines stop at 32,767 characters


class JudgeError(RuntimeError):
    pass


class QuotaExhausted(JudgeError):
    """The account's quota is used up: retrying is pointless, a batch stops at once (the message says when it resets)."""


@dataclass
class JudgeResponse:
    text: str
    model: str
    cached: bool
    prompt_hash: str
    usage: dict
    conversation_id: str | None = None
    latency_s: float = 0.0


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(text: str) -> str:
    """Drop control characters (PDF extraction leaves NULs and the like in some chunks); a NUL stops Windows from starting the process.
    Tab and newline are kept. Applied before hashing, so the cache key is the text that was really sent."""
    return _CONTROL.sub("", text)


def request_hash(model: str, prompt: str, schema: dict | None) -> str:
    payload = {"model": model, "prompt": prompt, "schema": schema}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def run_agy(prompt: str, model: str, schema: dict | None, timeout_s: float) -> dict:
    """One `agy -p` call in an empty directory; returns the CLI's JSON envelope."""
    cmd = ["agy", "-p", prompt, "--model", model, "--output-format", "json", "--sandbox", "--disable-slash-commands"]
    if schema is not None:
        cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
    with tempfile.TemporaryDirectory(prefix="agy-judge-") as empty:
        proc = subprocess.run(cmd, cwd=empty, capture_output=True, text=True, encoding="utf-8", timeout=timeout_s)
    out, err_text = proc.stdout, proc.stderr
    if "quota" in (out + err_text).lower() and "reached" in (out + err_text).lower():
        raise QuotaExhausted((err_text.strip() or out.strip())[:200])
    if proc.returncode != 0:
        raise JudgeError(f"agy exited with {proc.returncode}: {err_text.strip()[:200]}")
    try:
        env = json.loads(out)
    except json.JSONDecodeError as err:
        raise JudgeError(f"agy printed non-JSON output: {out[:120]!r}") from err
    if env.get("status") != "SUCCESS":
        raise JudgeError(f"agy status {env.get('status')}: {str(env.get('error'))[:120]}")
    if not str(env.get("response", "")).strip():
        raise JudgeError("agy returned SUCCESS with an empty response")      # seen 2026-10-11 near the quota limit; never cache it
    return env


class AgyJudge:
    def __init__(self, cache_path: Path | None = None, model: str = DEFAULT_MODEL, timeout_s: float = 240, retries: int = 1,
                 runner: Callable[[str, str, dict | None, float], dict] = run_agy):
        self.model, self.timeout_s, self.retries, self._runner = model, timeout_s, retries, runner
        self.cache_path, self._cache, self._lock = cache_path, {}, threading.Lock()
        if cache_path and cache_path.exists():
            for line in cache_path.read_text(encoding="utf-8").split("\n"):
                if line.strip():
                    row = json.loads(line)
                    self._cache[row["hash"]] = row

    def complete(self, prompt: str, schema: dict | None = None) -> JudgeResponse:
        prompt = clean(prompt)
        if len(prompt) > MAX_PROMPT_CHARS:
            raise JudgeError(f"prompt is {len(prompt)} characters; the command-line limit is {MAX_PROMPT_CHARS}")
        key = request_hash(self.model, prompt, schema)
        with self._lock:
            row = self._cache.get(key)
        if row:
            return JudgeResponse(row["text"], self.model, True, key, row.get("usage", {}), row.get("conversation_id"), 0.0)
        for attempt in range(self.retries + 1):
            start = time.perf_counter()
            try:
                env = self._runner(prompt, self.model, schema, self.timeout_s)
                break
            except QuotaExhausted:
                raise
            except (JudgeError, subprocess.TimeoutExpired, OSError, ValueError) as err:
                if attempt == self.retries:
                    raise JudgeError(f"{type(err).__name__}: {err}") from err
                time.sleep(3 * (attempt + 1))
        latency = time.perf_counter() - start
        row = {"hash": key, "model": self.model, "text": env["response"], "usage": env.get("usage", {}),
               "conversation_id": env.get("conversation_id"), "latency_s": round(latency, 3)}
        with self._lock:
            self._cache[key] = row
            if self.cache_path:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with self.cache_path.open("a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return JudgeResponse(row["text"], self.model, False, key, row["usage"], row["conversation_id"], latency)

    def map_calls(self, jobs: list[tuple[str, dict | None]], workers: int = 6, max_consecutive_failures: int = 5) -> list[JudgeResponse | JudgeError]:
        """Run (prompt, schema) jobs in order; a failed job yields its JudgeError in the result list. After `max_consecutive_failures`
        failures in a row the remaining jobs are not started (their slots hold a JudgeError) so a quota problem stops the batch."""
        results: list[JudgeResponse | JudgeError | None] = [None] * len(jobs)
        state = {"streak": 0, "stop": False}
        guard = threading.Lock()

        def one(i: int) -> None:
            if state["stop"]:
                results[i] = JudgeError("batch stopped after repeated failures")
                return
            try:
                results[i] = self.complete(*jobs[i])
                with guard:
                    state["streak"] = 0
            except JudgeError as err:
                results[i] = err
                with guard:
                    state["streak"] += 1
                    state["stop"] = state["stop"] or isinstance(err, QuotaExhausted) or state["streak"] >= max_consecutive_failures

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, range(len(jobs))))
        return results  # type: ignore[return-value]
