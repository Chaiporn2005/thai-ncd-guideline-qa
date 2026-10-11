"""Chat with native tool calling (OpenAI-compatible `tools`), cached the same way as src/ncdqa/llm/client.py (Track C, ReAct agents).

`LLMClient.complete` returns only the reply text, so a `tool_calls` reply would be lost. This wrapper reuses the client's provider settings, HTTP call and retry logic
and keeps the whole assistant message (content and tool_calls). Every request is cached by a hash of (provider, model, messages, all parameters including the tool list),
in its own JSONL file next to the text cache, so an agent run can be repeated exactly from the cache. A cache hit costs nothing and returns the stored message.
Typhoon (typhoon-v2.5-30b-a3b-instruct) was tested on 2026-10-11: it returns well-formed tool_calls, several in one turn, and accepts role "tool" results.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .client import LLMClient, ProviderConfig, request_hash


class ToolLLM:
    def __init__(self, cfg: ProviderConfig, cache_path: Path | None = None, transport=None):
        self.cfg = cfg
        self._client = LLMClient(cfg, None, transport=transport, use_cache=False)     # only used for its HTTP call and retries
        self.cache_path, self._cache = cache_path, {}
        if cache_path and cache_path.exists():
            for line in cache_path.read_text(encoding="utf-8").split(chr(10)):
                if line.strip():
                    row = json.loads(line)
                    self._cache[row["hash"]] = row

    @classmethod
    def from_client(cls, client: LLMClient, suffix: str = "_tools") -> "ToolLLM":
        path = client.cache_path.with_name(client.cache_path.stem + suffix + client.cache_path.suffix) if client.cache_path else None
        return cls(client.cfg, path, getattr(client, "_transport", None))

    def chat(self, messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 1000, tool_choice: str = "auto") -> dict:
        """Returns {"message": {...}, "finish_reason", "usage", "cached", "latency_s", "hash"}. `tools=None` sends no tools (the model must answer in text); tool_choice "required" makes the model call a tool in this turn."""
        extra = {"tools": tools, "tool_choice": tool_choice} if tools else {}
        params = self._client.params(max_tokens=max_tokens, **extra)
        key = request_hash(self.cfg, messages, params)
        if key in self._cache:
            row = self._cache[key]
            return {"message": row["message"], "finish_reason": row["finish_reason"], "usage": row.get("usage", {}), "cached": True, "latency_s": 0.0, "hash": key}
        start = time.perf_counter()
        data = self._client._call(messages, params)
        latency = time.perf_counter() - start
        choice = data["choices"][0]
        raw = choice["message"]
        message = {"role": "assistant", "content": raw.get("content") or ""}
        if raw.get("tool_calls"):
            message["tool_calls"] = [{"id": c["id"], "type": "function", "function": {"name": c["function"]["name"], "arguments": c["function"]["arguments"]}}
                                     for c in raw["tool_calls"]]
        row = {"hash": key, "message": message, "finish_reason": choice.get("finish_reason"), "usage": data.get("usage", {}), "latency_s": round(latency, 3)}
        self._cache[key] = row
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8", newline=chr(10)) as f:
                f.write(json.dumps(row, ensure_ascii=False) + chr(10))
        return {"message": message, "finish_reason": row["finish_reason"], "usage": row["usage"], "cached": False, "latency_s": latency, "hash": key}
