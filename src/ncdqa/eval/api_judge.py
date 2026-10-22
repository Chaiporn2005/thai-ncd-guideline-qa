"""The same judge model through the Gemini API instead of the Antigravity CLI (Track C).

Why it exists: on 2026-10-11 the Antigravity account's quota ran out mid-evaluation ("Individual quota reached ... Resets in 3h21m"), and the CLI
spends ~14k input tokens per call on its own agent prompt. The Gemini API serves the same model family (`gemini-3.8-flash`, reasoning_effort high)
with only our prompt, and with no agent tools at all, which is also the safer way to show a judge text from an untrusted corpus.
`AgyJudge` takes a runner; this module supplies one that calls the OpenAI-compatible endpoint with the key from GEMINI_API_KEY (never printed). The
cache key contains the model id, so answers from the two routes are stored side by side and a manifest can say which route produced each metric.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

from .agy_client import AgyJudge, JudgeError, QuotaExhausted

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
API_MODEL = "gemini-3.8-flash"


# The free tier of the API allows 5 requests per minute for this model (measured 2026-10-11: 5 of 14 simultaneous calls passed, the rest got
# 429 "limit: 5 ... retry in 3.26s"). One global limiter spaces the calls; a 429 that still happens waits for the advised time and tries again.
MIN_INTERVAL_S = 12.5
_gate, _last = threading.Lock(), [0.0]


def _wait_turn() -> None:
    with _gate:
        pause = _last[0] + MIN_INTERVAL_S - time.monotonic()
        if pause > 0:
            time.sleep(pause)
        _last[0] = time.monotonic()


def api_runner(prompt: str, model: str, schema: dict | None, timeout_s: float) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise JudgeError("GEMINI_API_KEY is not set")
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "reasoning_effort": "high", "max_tokens": 8192}
    if schema is not None:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "judge", "schema": schema}}

    def post(payload: dict) -> dict:
        for attempt in range(6):
            _wait_turn()
            try:
                return _post_once(payload)
            except urllib.error.HTTPError as err:
                if err.code != 429:
                    raise
                text = err.read().decode("utf-8", "replace")
                if re.search(r"per[ _]?day|PerDay", text, re.I):
                    raise QuotaExhausted("daily quota: " + text[:160]) from err
                m = re.search(r"retry in ([\d.]+)s", text)
                time.sleep(float(m.group(1)) + 2 if m else 15)
        raise QuotaExhausted("still rate limited after 6 tries")

    def _post_once(payload: dict) -> dict:
        req = urllib.request.Request(BASE_URL + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

    try:
        try:
            data = post(body)
        except urllib.error.HTTPError as err:
            if err.code == 400 and "response_format" in body:       # schema mode refused for this model: ask again with the schema in words only
                body.pop("response_format")
                data = post(body)
            else:
                raise
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", "replace")[:200]
        if err.code == 429:
            raise QuotaExhausted(f"HTTP 429: {text}") from err
        raise JudgeError(f"HTTP {err.code}: {text}") from err
    except (urllib.error.URLError, TimeoutError) as err:
        raise JudgeError(f"{type(err).__name__}") from err
    choice = data["choices"][0]
    content = choice["message"].get("content") or ""
    if not content.strip():
        raise JudgeError(f"empty response (finish_reason {choice.get('finish_reason')})")
    usage = data.get("usage", {})
    return {"response": content, "usage": {"total_tokens": usage.get("total_tokens"), "input_tokens": usage.get("prompt_tokens"),
                                           "output_tokens": usage.get("completion_tokens")}, "conversation_id": None, "status": "SUCCESS"}


def ApiJudge(cache_path=None, model: str = API_MODEL, timeout_s: float = 240, retries: int = 1) -> AgyJudge:
    return AgyJudge(cache_path, model=model, timeout_s=timeout_s, retries=retries, runner=api_runner)
