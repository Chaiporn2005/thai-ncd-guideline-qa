"""Run the query-rewrite requests through one hosted API provider, cached and resumable (Track B).

Reads `requests.jsonl` (id "qid:mode", mode, messages; from export_llm_requests.py) and writes rows in the same shape as the Kaggle LLM
kernel (`id, mode, model, repeat, batch_size, text, new_tokens`) so scripts/eval_query_rewrite.py can score them next to the local models.
`model` is the provider name from the providers file. Repeat 0 uses the cache; repeat 1 (only for the modes listed in --repeat-modes)
bypasses it, to measure how much a live API drifts at temperature 0. Rows are appended as they arrive; a re-run skips what is done.
Only questions that passed `sendable` were exported, so no personal identifiers leave the machine. Keys are never printed.

Usage:
    python -X utf8 scripts/run_llm_provider.py --provider typhoon_api --requests data/index/llm-requests/requests.jsonl \
        --out data/index/llm_api/typhoon_api.jsonl --workers 4 --repeat-modes rewrite
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.llm.client import LLMClient, load_providers  # noqa: E402
from ncdqa.llm.env import load_env  # noqa: E402

MAX_NEW = {"rewrite": 120, "hyde": 200, "q2d": 180}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--provider", required=True)
    ap.add_argument("--requests", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--modes", nargs="+", default=["rewrite", "hyde", "q2d"])
    ap.add_argument("--repeat-modes", nargs="*", default=["rewrite"])
    ap.add_argument("--limit", type=int, help="only the first N requests per mode (smoke test)")
    args = ap.parse_args(argv)

    load_env()
    cfg = load_providers(ROOT / "configs/llm/providers.yaml")[args.provider]
    cache = ROOT / "data/index/llm_cache" / f"{args.provider}.jsonl"
    cached, live = LLMClient(cfg, cache), LLMClient(cfg, None, use_cache=False)
    reqs = [json.loads(x) for x in args.requests.read_text(encoding="utf-8").split("\n") if x.strip() and json.loads(x)["mode"] in args.modes]
    if args.limit:
        reqs = [r for m in args.modes for r in [x for x in reqs if x["mode"] == m][:args.limit]]
    done = set()
    if args.out.exists():
        done = {(r["id"], r["repeat"]) for r in (json.loads(x) for x in args.out.read_text(encoding="utf-8").split("\n") if x.strip())}
    jobs = [(r, 0) for r in reqs] + [(r, 1) for r in reqs if r["mode"] in args.repeat_modes]
    jobs = [(r, k) for r, k in jobs if (r["id"], k) not in done]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    lock, stats = threading.Lock(), {"ok": 0, "failed": 0, "latency": [], "errors": {}}

    def work(job):
        r, repeat = job
        client = cached if repeat == 0 else live
        for attempt in range(3):
            try:
                resp = client.complete(r["messages"], max_tokens=MAX_NEW[r["mode"]])
                row = {"id": r["id"], "mode": r["mode"], "model": args.provider, "repeat": repeat, "batch_size": args.workers,
                       "text": resp.text, "new_tokens": resp.usage.get("completion_tokens", 0), "cached": resp.cached,
                       "latency_s": round(resp.latency_s, 2), "finish": resp.finish_reason}
                with lock:
                    with args.out.open("a", encoding="utf-8", newline="\n") as f:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    stats["ok"] += 1
                    if not resp.cached:
                        stats["latency"].append(resp.latency_s)
                return
            except urllib.error.HTTPError as err:
                code = f"HTTP {err.code}"
                with lock:
                    stats["errors"][code] = stats["errors"].get(code, 0) + 1
                time.sleep(5 * (attempt + 1))
            except Exception as err:  # never print headers or keys
                with lock:
                    stats["errors"][type(err).__name__] = stats["errors"].get(type(err).__name__, 0) + 1
                time.sleep(3)
        with lock:
            stats["failed"] += 1

    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, jobs))
    lat = sorted(stats["latency"])
    print(json.dumps({"provider": args.provider, "jobs": len(jobs), "ok": stats["ok"], "failed": stats["failed"], "errors": stats["errors"],
                      "wall_s": round(time.time() - started, 1),
                      "latency_s": {"median": lat[len(lat) // 2] if lat else None, "p95": lat[int(len(lat) * .95)] if lat else None}}))
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
