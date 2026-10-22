"""One small client for every LLM the project talks to (hosted API or a replayed local-model run), built for repeatable results.

* Deterministic settings are the default: temperature 0, top_p 1, a fixed seed (where the provider honours it). Even so, hosted
  APIs are not guaranteed to return identical text twice, so every request is cached by a hash of (provider, model, messages and
  all sampling parameters); a cache hit returns the stored answer and a run can be repeated exactly. `scripts/llm_stability_check.py`
  measures how much the live answers drift when the cache is bypassed.
* Keys are never stored or logged: a provider names the environment variable that holds its key (`api_key_env`).
* `kind: cache_only` replays answers produced elsewhere (for example local models run on a Kaggle GPU, which write the same
  cache format); a missing entry is an error, not a silent fallback.
* Standard library only (urllib), so it runs in every virtual environment of the project.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

Transport = Callable[[str, dict, dict, float], dict]


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    kind: str                      # openai_compatible | cache_only
    model: str
    base_url: str = ""
    api_key_env: str = ""
    temperature: float = 0.0
    top_p: float = 1.0
    seed: int | None = 20261010   # None: the provider rejects the field (Gemini's OpenAI endpoint does), so it is not sent
    max_tokens: int = 256
    timeout_s: float = 60.0
    retries: int = 4
    extra_body: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    cached: bool
    prompt_hash: str
    usage: dict
    fingerprint: str | None = None
    finish_reason: str | None = None
    latency_s: float = 0.0


def request_hash(cfg: ProviderConfig, messages: list[dict], params: dict) -> str:
    payload = {"provider": cfg.name, "model": cfg.model, "messages": messages, "params": params}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _http_post(url: str, headers: dict, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class LLMClient:
    def __init__(self, cfg: ProviderConfig, cache_path: Path | None = None, transport: Transport | None = None,
                 use_cache: bool = True):
        self.cfg, self.use_cache = cfg, use_cache
        self.cache_path = cache_path
        self._transport = transport
        self._cache: dict[str, dict] = {}
        if cache_path and cache_path.exists():
            for line in cache_path.read_text(encoding="utf-8").split("\n"):
                if line.strip():
                    row = json.loads(line)
                    self._cache[row["hash"]] = row

    def params(self, **override) -> dict:
        p = {"temperature": self.cfg.temperature, "top_p": self.cfg.top_p, "max_tokens": self.cfg.max_tokens, **self.cfg.extra_body}
        if self.cfg.seed is not None:
            p["seed"] = self.cfg.seed
        p.update(override)
        return p

    def complete(self, messages: list[dict], **override) -> LLMResponse:
        params = self.params(**override)
        key = request_hash(self.cfg, messages, params)
        if self.use_cache and key in self._cache:
            row = self._cache[key]
            return LLMResponse(row["text"], self.cfg.name, row["model"], True, key, row.get("usage", {}), row.get("fingerprint"),
                               row.get("finish_reason"), 0.0)
        if self.cfg.kind == "cache_only":
            raise KeyError(f"{self.cfg.name}: no cached answer for request {key[:12]} (cache_only provider)")
        start = time.perf_counter()
        data = self._call(messages, params)
        latency = time.perf_counter() - start
        choice = data["choices"][0]
        row = {"hash": key, "provider": self.cfg.name, "model": data.get("model", self.cfg.model), "messages": messages, "params": params,
               "text": choice["message"]["content"], "usage": data.get("usage", {}), "fingerprint": data.get("system_fingerprint"),
               "finish_reason": choice.get("finish_reason"), "latency_s": round(latency, 3)}
        if self.use_cache:
            self._cache[key] = row
            if self.cache_path:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with self.cache_path.open("a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return LLMResponse(row["text"], self.cfg.name, row["model"], False, key, row["usage"], row["fingerprint"], row["finish_reason"], latency)

    def _call(self, messages: list[dict], params: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.cfg.api_key_env:
            key = os.environ.get(self.cfg.api_key_env)
            if not key:
                raise RuntimeError(f"environment variable {self.cfg.api_key_env} is not set for provider {self.cfg.name}")
            headers["Authorization"] = f"Bearer {key}"
        body = {"model": self.cfg.model, "messages": messages, **params}
        url = self.cfg.base_url.rstrip("/") + "/chat/completions"
        post = self._transport or _http_post
        delay = 2.0
        for attempt in range(self.cfg.retries + 1):
            try:
                return post(url, headers, body, self.cfg.timeout_s)
            except urllib.error.HTTPError as err:
                if err.code not in (429, 500, 502, 503, 504) or attempt == self.cfg.retries:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.cfg.retries:
                    raise
            time.sleep(delay)
            delay *= 2
        raise RuntimeError("unreachable")


def load_providers(path: Path) -> dict[str, ProviderConfig]:
    import yaml
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {name: ProviderConfig(name=name, **spec) for name, spec in raw["providers"].items()}
