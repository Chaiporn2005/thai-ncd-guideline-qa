"""bge-m3's own sparse and ColBERT scores against BM25 and the frozen hybrid, on gold dev only (Track B, exploration).

Inputs come from infra/kaggle_bgem3_sparse (sparse top-100 children per question, and colbert/sparse/dense scores for the top-30
hybrid parents). Tested, all against the frozen hybrid B (dense + BM25 char3, convex alpha 0.6) with a paired bootstrap:
  sparse only / BM25 only / dense only               the three signals alone (children matched, parents returned)
  dense + bge sparse                                  convex, alpha 0.6 (replaces BM25)
  dense + BM25 + bge sparse                           min-max each, weights (dense, BM25, sparse) from a small grid of our own
  re-order B's top-30 by colbert / sparse / dense / colbert+sparse+dense   (the model's weighted sum 0.4/0.2/0.4 is the weighting its
                                                      own documentation uses)
The 3-way weights are our grid (no paper fixes them); this is exploration on dev: a change would need a new freeze, and the test split
is not touched here.

Usage:
    python -X utf8 scripts/eval_bgem3_sparse.py --sparse data/index/kaggle_sparse/sparse_top100.jsonl --pairs data/index/kaggle_sparse/pair_scores.jsonl \
        --questions data/agent_runs/20261010-silver-questions/questions_gold_dev.jsonl --out data/index/sweeps/bgem3-sparse
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from sweep_hybrid import Sweep, read_jsonl  # noqa: E402
from ncdqa.retrieval import evaluate, fusion  # noqa: E402
from ncdqa.retrieval.parent_child import build_parent_map  # noqa: E402


def three_way(dense, bm25, sparse, w, top=10):
    a, b, c = fusion.minmax(dense), fusion.minmax(bm25), fusion.minmax(sparse)
    docs = set(a) | set(b) | set(c)
    fused = {d: w[0] * a.get(d, 0.0) + w[1] * b.get(d, 0.0) + w[2] * c.get(d, 0.0) for d in docs}
    return sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:top]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sparse", type=Path, required=True)
    ap.add_argument("--pairs", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--parents", type=Path, default=ROOT / "data/index/chunks-v12-t512")
    ap.add_argument("--children", type=Path, default=ROOT / "data/index/chunks-v12-t128")
    ap.add_argument("--index", type=Path, default=ROOT / "data/index/dense-bge-m3-t128-v12")
    ap.add_argument("--config", type=Path, default=ROOT / "configs/retrieval/hybrid_sweep_v1.json")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: choose a new --out")
    ns = argparse.Namespace(config=args.config, questions=args.questions, model="bge-m3", parents=args.parents,
                            children=args.children, index=args.index)
    sw = Sweep(ns)
    pmap = build_parent_map(read_jsonl(args.children / "chunks.jsonl"), sw.parents)
    sparse_hits = {r["qid"]: r["hits"] for r in read_jsonl(args.sparse)}
    sparse_lists = []
    for q in sw.questions:
        best: dict[str, float] = {}
        for h in sparse_hits[q["qid"]]:
            p = pmap.get(h["chunk_id"])
            if p is not None and h["score"] > best.get(p, -1):
                best[p] = h["score"]
        sparse_lists.append(sorted(best.items(), key=lambda kv: -kv[1])[:sw.pool])
    bm25 = sw.bm25_lists("char3", None, 2.18, 0.86)
    dense = sw.dense

    top = lambda lists: [[u for u, _ in l[:10]] for l in lists]
    base = sw.record("0_reference", "B frozen: dense + BM25 (convex 0.6)", {}, [[u for u, _ in fusion.convex(d, b, 0.6, 10)] for d, b in zip(dense, bm25)])
    cands = [base]
    cands.append(sw.record("single_signal", "dense only (A)", {}, top(dense)))
    cands.append(sw.record("single_signal", "BM25 only", {}, top(bm25)))
    cands.append(sw.record("single_signal", "bge-m3 sparse only", {}, top(sparse_lists)))
    cands.append(sw.record("fusion", "dense + bge sparse (convex 0.6)", {}, [[u for u, _ in fusion.convex(d, s, 0.6, 10)] for d, s in zip(dense, sparse_lists)]))
    for w in ((0.5, 0.25, 0.25), (0.6, 0.2, 0.2), (0.6, 0.3, 0.1), (0.6, 0.1, 0.3), (0.4, 0.3, 0.3)):
        cands.append(sw.record("fusion", f"dense + BM25 + bge sparse weights {w}", {"weights": w},
                               [[u for u, _ in three_way(d, b, s, w)] for d, b, s in zip(dense, bm25, sparse_lists)]))
    pair = {}
    for r in read_jsonl(args.pairs):
        pair[(r["qid"], r["chunk_id"])] = r
    fused30 = [fusion.convex(d, b, 0.6, 30) for d, b in zip(dense, bm25)]
    for mode in ("colbert", "sparse", "dense", "colbert+sparse+dense"):
        lists = []
        for q, lst in zip(sw.questions, fused30):
            head = sorted(lst, key=lambda x: -pair[(q["qid"], x[0])][mode])
            lists.append([u for u, _ in head[:10]])
        cands.append(sw.record("rerank_top30_of_B", f"re-order B top-30 by {mode} score", {"mode": mode}, lists))
    for e in cands:
        e["paired_vs_reference"] = evaluate.paired_bootstrap({q: v["recall@5"] for q, v in base["per_question"].items()},
                                                             {q: v["recall@5"] for q, v in e["per_question"].items()})
        e["paired_mrr"] = evaluate.paired_bootstrap({q: v["mrr@10"] for q, v in base["per_question"].items()},
                                                    {q: v["mrr@10"] for q, v in e["per_question"].items()})
    sw.cfg = {**sw.cfg, "id": "bgem3_sparse_v1"}
    sw.save(args.out)
    print((args.out / "report.md").read_text(encoding="utf-8"))
    for e in cands:
        m = e["paired_mrr"]
        print(f"{e['name'][:62]:62s} MRR diff {m['mean_diff']:+.3f} ({m['ci95'][0]:+.3f}, {m['ci95'][1]:+.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
