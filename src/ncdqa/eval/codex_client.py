"""A judge through the Codex CLI (`codex exec`), cached and bounded like the others (Track C).

Owner's choice 2026-10-11: `gpt-5.6-luna` with reasoning effort high, run alongside Claude Sonnet 4.6 (through agy) so that every metric has two judges
from different model families and their agreement can be reported (there is no human check of the judge, decision E5).
Like agy, codex is an agent with tools, and the prompt carries corpus text. So each call runs in a fresh EMPTY temporary directory with the `read-only`
sandbox, never the bypass flag; the prompt goes in through stdin; the final message is read from a file written with `--output-last-message` (stdout
also carries logs). Replies are parsed leniently by the callers (first JSON object that has the key we asked for).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from .agy_client import AgyJudge, JudgeError, QuotaExhausted

MODEL = "gpt-5.6-luna"
EFFORT = "high"


def codex_runner(prompt: str, model: str, schema: dict | None, timeout_s: float) -> dict:
    """`model` is "<model>:<effort>", e.g. "gpt-5.6-luna:high". `schema` is not sent (codex wants a strict schema); the prompt states the JSON shape."""
    name, _, effort = model.partition(":")
    with tempfile.TemporaryDirectory(prefix="codex-judge-") as empty:
        out_file = Path(empty) / "last_message.txt"
        cmd = ["codex", "exec", "-m", name, "-c", f'model_reasoning_effort="{effort or EFFORT}"', "--sandbox", "read-only", "--skip-git-repo-check",
               "--ephemeral", "-C", empty, "-o", str(out_file), "-"]
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=timeout_s, cwd=empty)
        log = (proc.stdout or "") + (proc.stderr or "")
        if re.search(r"usage limit|rate limit|quota|too many requests|429", log, re.I) and proc.returncode != 0:
            raise QuotaExhausted(log.strip()[-200:])
        if proc.returncode != 0:
            raise JudgeError(f"codex exited with {proc.returncode}: {log.strip()[-200:]}")
        text = out_file.read_text(encoding="utf-8") if out_file.exists() else ""
    if not text.strip():
        raise JudgeError("codex returned an empty final message")
    m = re.search(r"tokens used\s*([\d,]+)", log)
    return {"response": text, "usage": {"total_tokens": int(m.group(1).replace(",", "")) if m else None}, "conversation_id": None, "status": "SUCCESS"}


def CodexJudge(cache_path=None, model: str = MODEL, effort: str = EFFORT, timeout_s: float = 300, retries: int = 1) -> AgyJudge:
    return AgyJudge(cache_path, model=f"{model}:{effort}", timeout_s=timeout_s, retries=retries, runner=codex_runner)
