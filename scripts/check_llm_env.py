"""Check the LLM API setup without exposing a key: which variables are set, which model ids each key may use, one tiny test call (Track B).

Default: for every hosted provider in configs/llm/providers.yaml (or the example file) say whether its key variable is set (yes/no,
never the value) and whether the configured model id is still a placeholder.
--list-models  ask each provider with a key for its model list (GET {base_url}/models) and print the ids, so the model id is copied from
               the provider's answer. Only the HTTP status and the ids are printed.
--ping         send one tiny question ("ตอบเพียงคำว่า ok") with temperature 0 and print the answer, latency and token usage (cache off).

Usage:
    python -X utf8 scripts/check_llm_env.py
    python -X utf8 scripts/check_llm_env.py --list-models
    python -X utf8 scripts/check_llm_env.py --ping --provider glm_4_7_flash
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.llm.client import LLMClient, load_providers  # noqa: E402
from ncdqa.llm.env import is_set, load_env  # noqa: E402


def list_models(base_url: str, key: str) -> tuple[int, list[str]]:
    req = urllib.request.Request(base_url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, []
    except (urllib.error.URLError, TimeoutError) as err:
        return 0, [f"unreachable: {type(err).__name__}"]
    items = data if isinstance(data, list) else data.get("data", data.get("models", []))  # some providers answer a bare list
    items = [m if isinstance(m, dict) else {"id": str(m)} for m in items]
    ids = [(m.get("id") or m.get("name") or "") for m in items]
    return 200, sorted(i.replace("models/", "") for i in ids if i)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--providers", type=Path, default=None)
    ap.add_argument("--provider", help="only this provider")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--ping", action="store_true")
    args = ap.parse_args(argv)

    path = args.providers or (ROOT / "configs/llm/providers.yaml")
    if not path.exists():
        path = ROOT / "configs/llm/providers.example.yaml"
    loaded = load_env()
    print(f"providers file: {path.relative_to(ROOT)}; variables loaded from .env: {', '.join(loaded) if loaded else '(none new)'}")
    providers = {k: v for k, v in load_providers(path).items() if v.kind == "openai_compatible" and (not args.provider or k == args.provider)}
    status = 0
    for name, cfg in providers.items():
        key_set = is_set(cfg.api_key_env)
        placeholder = cfg.model.startswith("<")
        print(f"\n[{name}] key variable {cfg.api_key_env}: {'set' if key_set else 'NOT set'}; model: {'PLACEHOLDER' if placeholder else cfg.model}; base_url: {cfg.base_url}")
        if not key_set:
            status = 1
            continue
        if args.list_models:
            code, ids = list_models(cfg.base_url, os.environ[cfg.api_key_env])
            print(f"  GET /models -> HTTP {code}")
            for i in ids[:60]:
                print("   ", i)
            if code != 200:
                status = 1
        if args.ping:
            if placeholder:
                print("  skipped: fill in the model id first (use --list-models)")
                status = 1
                continue
            client = LLMClient(cfg, None, use_cache=False)
            try:
                r = client.complete([{"role": "user", "content": "ตอบเพียงคำว่า ok"}], max_tokens=64)
                print(f"  answer: {r.text.strip()[:80]!r}; finish: {r.finish_reason}; latency {r.latency_s:.2f}s; usage {r.usage}")
            except urllib.error.HTTPError as err:  # the body explains a rejected parameter; it never contains the key
                print(f"  call failed: HTTP {err.code}: {err.read().decode("utf-8", "replace")[:1500]}")
                status = 1
            except Exception as err:  # never print headers or the key
                print(f"  call failed: {type(err).__name__}: {str(err)[:160]}")
                status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
