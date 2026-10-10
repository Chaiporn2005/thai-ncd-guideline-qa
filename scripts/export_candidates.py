"""Export the candidate lists a reranker will re-score, plus the unit texts (Track B).

For each dev question: the top `--depth` parent chunks of the chain a finished hybrid sweep carried forward. Output folder:
`candidates.jsonl` (qid, question, candidates [{chunk_id, hybrid_score}]) and `units.jsonl` (chunk_id, text as embedded:
header + text). The Kaggle reranker kernel reads both; scores come back as `rerank_scores.jsonl`.

Usage:
    python -X utf8 scripts/export_candidates.py --sweep data/index/sweeps/hybrid-v1-bge-m3 --model bge-m3 --questions ... \
        --parents data/index/chunks-v11-t512 --children data/index/chunks-v11-t128 --index data/index/kaggle/dense-bge-m3-t128 \
        --depth 30 --out data/index/rerank-candidates-bge-m3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sweep_hybrid import Sweep  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sweep", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--parents", type=Path, required=True)
    ap.add_argument("--children", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=ROOT / "configs/retrieval/hybrid_sweep_v1.json")
    ap.add_argument("--depth", type=int, default=30)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: choose a new --out")
    sw = Sweep(args)
    prior = json.loads((args.sweep / "sweep_results.json").read_text(encoding="utf-8"))
    fused, chain = sw.provisional_hybrid(prior)
    args.out.mkdir(parents=True)
    need: set[str] = set()
    with (args.out / "candidates.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for q, lst in zip(sw.questions, fused):
            cands = [{"chunk_id": u, "hybrid_score": round(s, 5)} for u, s in lst[:args.depth]]
            need.update(c["chunk_id"] for c in cands)
            f.write(json.dumps({"qid": q["qid"], "question": q["question"], "candidates": cands}, ensure_ascii=False) + "\n")
    with (args.out / "units.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for c in sw.parents:
            if c["chunk_id"] in need:
                f.write(json.dumps({"chunk_id": c["chunk_id"], "text": (c["header_text"] + "\n" if c["header_text"] else "") + c["text"]},
                                   ensure_ascii=False) + "\n")
    (args.out / "meta.json").write_text(json.dumps({"chain": chain, "depth": args.depth, "questions": len(sw.questions), "units": len(need)}, indent=1), encoding="utf-8")
    print(json.dumps({"chain": chain, "questions": len(sw.questions), "units": len(need)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
