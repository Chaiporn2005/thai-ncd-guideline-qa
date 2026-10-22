"""Add a variant that was evaluated in its own run (here D = BM25 only) to the A/B/C table without re-judging A/B/C (Track C).

    python -X utf8 scripts/compare_extra_variant.py --base data/index/runs/eval/test_luna_N7 --extra data/index/runs/eval/test_D_luna_N7 --out data/index/runs/eval/test_ABCD.md

Why separate runs: the correctness judge takes 8 answers per call and the batch composition changes when a variant is added; that moves a verdict now and then (agreement 94.7%
over two reshufflings, scripts/judge_bias.py). Keeping the A/B/C verdicts untouched keeps their published numbers stable; D is judged in its own batches and compared pairwise
by question. Differences between D and the others therefore include that small batching noise, which is stated in the output.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

NL = chr(10)
SC = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "no_answer": 0.0}


def rows(p: Path) -> dict:
    return {(r["variant"], r["qid"]): r for r in csv.DictReader((p / "per_question.csv").open(encoding="utf-8-sig"))}


def paired(a: dict, b: dict, get, n: int = 3000, seed: int = 20261011) -> str:
    keys = [k for k in a if k in b and get(a[k]) is not None and get(b[k]) is not None]
    d = [get(b[k]) - get(a[k]) for k in keys]
    if not d:
        return "-"
    rng = random.Random(seed)
    m = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d) / len(d):+.3f} [{m[int(.025 * n)]:+.3f}, {m[int(.975 * n)]:+.3f}] (n={len(d)})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    mb = json.loads((args.base / "metrics.json").read_text(encoding="utf-8"))["variants"]
    me = json.loads((args.extra / "metrics.json").read_text(encoding="utf-8"))["variants"]
    allm = {**mb, **me}
    names = list(allm)
    lines = [f"# {args.base.name} + {args.extra.name}" + NL, "| metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    get = {"correctness (0-1)": lambda s: s["correctness_score"]["mean"], "faithfulness": lambda s: s["faithfulness"]["mean"],
           "BERTScore F1": lambda s: s["bert_f1"]["mean"], "BERTScore recall": lambda s: s["bert_recall"]["mean"],
           "retrieval hit@5": lambda s: s["retrieval_hit"]["k"] / s["retrieval_hit"]["n"],
           "citation correct | answered": lambda s: s["citation_correct_given_answered"]["k"] / s["citation_correct_given_answered"]["n"],
           "numbers of gold present": lambda s: s["numbers_covered"]["k"] / max(s["numbers_covered"]["n"], 1)}
    for label, f in get.items():
        lines.append(f"| {label} | " + " | ".join("-" if f(allm[n]) is None else f"{f(allm[n]):.3f}" for n in names) + " |")
    lines.append("| answerable refused | " + " | ".join(allm[n]["abstention"]["answerable_refused"] for n in names) + " |")
    lines.append("| unanswerable abstained | " + " | ".join(allm[n]["abstention"]["unanswerable_abstained"] for n in names) + " |")
    lines.append(NL + "Failure taxonomy:" + NL)
    cats = sorted({c for n in names for c in allm[n]["failure_taxonomy"]})
    lines += ["| category | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    lines += [f"| {c} | " + " | ".join(str(allm[n]["failure_taxonomy"].get(c, 0)) for n in names) + " |" for c in cats]
    rb, re_ = rows(args.base), rows(args.extra)
    ev = next(iter(me))
    lines += [NL + f"Paired difference of {ev} minus each other variant (mean [95% CI], by question):" + NL, "| vs | correctness | faithfulness | BERTScore recall |", "|---|---|---|---|"]
    for other in mb:
        a = {k[1]: v for k, v in rb.items() if k[0] == other}
        b = {k[1]: v for k, v in re_.items() if k[0] == ev}
        corr = lambda r: SC.get(r.get("correctness"))  # noqa: E731
        fl = lambda r: float(r["faithfulness"]) if r.get("faithfulness") else None  # noqa: E731
        br = lambda r: float(r["bert_recall"]) if r.get("bert_recall") else None  # noqa: E731
        lines.append(f"| {other} | {paired(a, b, corr)} | {paired(a, b, fl)} | {paired(a, b, br)} |")
    lines.append(NL + "The judge scored " + ev + " in its own 8-answer batches (see the docstring), so these differences include a small batching noise.")
    text = NL.join(lines) + NL
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
