"""Time the cross-encoder reranker on the CPU (the machine the demo runs on) for N candidates per query (Track B).

Uses real candidate lists from `export_candidates.py`. Reports seconds per query for each depth, after one warm-up query, with the
number of threads torch used. Float32 on CPU (the GPU run used float16).

Usage:
    python -X utf8 scripts/measure_rerank_latency.py --candidates data/index/rerank-candidates-bge-m3 --queries 5 --depths 10 20 30
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--queries", type=int, default=5)
    ap.add_argument("--depths", type=int, nargs="+", default=[10, 20, 30])
    ap.add_argument("--model", default="BAAI/bge-reranker-v2-m3")
    args = ap.parse_args()
    import torch
    from sentence_transformers import CrossEncoder

    rows = [json.loads(x) for x in (args.candidates / "candidates.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()][:args.queries + 1]
    units = {r["chunk_id"]: r["text"] for r in (json.loads(x) for x in (args.candidates / "units.jsonl").read_text(encoding="utf-8").split("\n") if x.strip())}
    model = CrossEncoder(args.model, max_length=512, device="cpu")
    model.predict([(rows[0]["question"], units[c["chunk_id"]]) for c in rows[0]["candidates"][:4]])  # warm-up
    out = {"model": args.model, "threads": torch.get_num_threads(), "machine": platform.processor(), "dtype": "float32", "seconds_per_query": {}}
    for depth in args.depths:
        times = []
        for r in rows[1:]:
            pairs = [(r["question"], units[c["chunk_id"]]) for c in r["candidates"][:depth]]
            t = time.perf_counter()
            model.predict(pairs, batch_size=8, show_progress_bar=False)
            times.append(time.perf_counter() - t)
        out["seconds_per_query"][str(depth)] = {"mean": round(sum(times) / len(times), 2), "max": round(max(times), 2)}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
