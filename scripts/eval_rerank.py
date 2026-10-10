"""Score the reranker's re-ordering of the hybrid candidates against the hybrid order itself (Track B, technique 2).

Reads `candidates.jsonl` (hybrid order) and `rerank_scores_<model>.jsonl` (scores from the Kaggle kernel). For each depth N the
top-N hybrid candidates are re-ordered by reranker score; the result is compared with the plain hybrid order on the same questions
with a paired bootstrap. Candidates beyond N keep their hybrid order. Also reports the ceiling: the share of questions whose
evidence is inside the top-N candidates at all (a reranker cannot fix a miss that is not in the list).

Usage:
    python -X utf8 scripts/eval_rerank.py --candidates data/index/rerank-candidates-bge-m3 --scores data/index/kaggle_rerank/rerank_scores_bge-reranker-v2-m3.jsonl \
        --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl --parents data/index/chunks-v11-t512
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import evaluate  # noqa: E402

KS = [1, 3, 5, 10]
KEYS = [f"{m}@{k}" for k in KS for m in ("recall", "hit", "mrr")]


def read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--parents", type=Path, required=True)
    ap.add_argument("--depths", type=int, nargs="+", default=[10, 20, 30])
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    units = {c["chunk_id"]: c for c in read(args.parents / "chunks.jsonl")}
    qs = {q["qid"]: q for q in read(args.questions) if q["answerable"] and q["status"] != "rejected" and q["split"] == "dev" and "??" not in q["question"]}
    cands = {r["qid"]: [c["chunk_id"] for c in r["candidates"]] for r in read(args.candidates / "candidates.jsonl")}
    scores: dict[tuple[str, str], float] = {(r["qid"], r["chunk_id"]): r["score"] for r in read(args.scores)}
    qids = [q for q in cands if q in qs]

    def score_all(order_fn) -> dict[str, dict]:
        return {q: evaluate.score_question([units[u] for u in order_fn(q)[:10]], qs[q]["evidence"], KS) for q in qids}

    base = score_all(lambda q: cands[q])
    lines = [f"# Reranker vs hybrid order ({len(qids)} answerable dev questions, silver pilot)\n",
             "| setting | R@1 | R@5 | R@10 | MRR@10 | R@5 diff vs hybrid (95% CI) | MRR@10 diff (95% CI) | better/worse/tie (R@5) |", "|---|---|---|---|---|---|---|---|"]
    b = evaluate.aggregate(base, KEYS)
    lines.append(f"| hybrid order | {b['recall@1']:.3f} | {b['recall@5']:.3f} | {b['recall@10']:.3f} | {b['mrr@10']:.3f} | | | |")
    for depth in args.depths:
        def order(q, depth=depth):
            top = sorted(cands[q][:depth], key=lambda u: -scores[(q, u)])
            return top + cands[q][depth:]
        res = score_all(order)
        o = evaluate.aggregate(res, KEYS)
        p5 = evaluate.paired_bootstrap({q: v["recall@5"] for q, v in base.items()}, {q: v["recall@5"] for q, v in res.items()})
        pm = evaluate.paired_bootstrap({q: v["mrr@10"] for q, v in base.items()}, {q: v["mrr@10"] for q, v in res.items()})
        lines.append(f"| rerank top-{depth} | {o['recall@1']:.3f} | {o['recall@5']:.3f} | {o['recall@10']:.3f} | {o['mrr@10']:.3f} | "
                     f"{p5['mean_diff']:+.3f} ({p5['ci95'][0]:+.3f}, {p5['ci95'][1]:+.3f}) | {pm['mean_diff']:+.3f} ({pm['ci95'][0]:+.3f}, {pm['ci95'][1]:+.3f}) | "
                     f"{p5['b_better']}/{p5['a_better']}/{p5['ties']} |")
    ceiling = {n: sum(any(evaluate.covers(units[u], e) for u in cands[q][:n] for e in qs[q]["evidence"]) for q in qids) / len(qids) for n in args.depths}
    lines.append("\nCeiling (share of questions with the evidence inside the top-N candidates): " + ", ".join(f"top-{n}: {v:.2f}" for n, v in ceiling.items()))
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
