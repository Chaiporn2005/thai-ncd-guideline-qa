"""Cuts of a judged evaluation that need no judge call: by question type, number rule x judge verdict, and error examples per category (Track C, plan E-5/E-6/E-7).

    python -X utf8 scripts/analyze_results.py --eval data/index/runs/eval/test_luna_N7 --out data/index/runs/eval/test_analysis.md
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

SC = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "no_answer": 0.0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--eval", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--examples", type=int, default=5)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    rows = list(csv.DictReader((args.eval / "per_question.csv").open(encoding="utf-8-sig")))
    variants = sorted({r["variant"] for r in rows})
    out = [f"# Analysis of {args.eval.name}\n"]

    out.append("## By question type: mean correctness score (n answerable) per variant\n")
    types = sorted({r["type"] for r in rows if r["answerable"] == "True"})
    out.append("| type | " + " | ".join(variants) + " |\n|---|" + "---|" * len(variants))
    for t in types:
        cells = []
        for v in variants:
            xs = [SC[r["correctness"]] for r in rows if r["variant"] == v and r["type"] == t and r["answerable"] == "True" and r["correctness"] in SC]
            cells.append(f"{sum(xs) / len(xs):.2f} (n={len(xs)})" if xs else "-")
        out.append(f"| {t} | " + " | ".join(cells) + " |")

    out.append("\n## Retrieval hit@5 by type (answerable)\n")
    out.append("| type | " + " | ".join(variants) + " |\n|---|" + "---|" * len(variants))
    for t in types:
        cells = []
        for v in variants:
            xs = [r["retrieval_hit"] == "True" for r in rows if r["variant"] == v and r["type"] == t and r["answerable"] == "True"]
            cells.append(f"{sum(xs)}/{len(xs)}")
        out.append(f"| {t} | " + " | ".join(cells) + " |")

    out.append("\n## Number rule x judge verdict (answers whose gold contains a number)\n")
    out.append("| variant | numbers all present | judge correct | numbers missing | judge correct |\n|---|---|---|---|---|")
    odd = []
    for v in variants:
        yes = [r for r in rows if r["variant"] == v and r["numbers_covered"] == "True"]
        no = [r for r in rows if r["variant"] == v and r["numbers_covered"] == "False"]
        out.append(f"| {v} | {len(yes)} | {sum(r['correctness'] == 'correct' for r in yes)} | {len(no)} | {sum(r['correctness'] == 'correct' for r in no)} |")
        odd += [r for r in no if r["correctness"] == "correct"]
    out.append(f"\nJudge says *correct* although a gold number is missing from the answer: {len(odd)} answers. Read them: the judge may be lenient, or the number may be written differently.\n")
    for r in odd[: args.examples * 2]:
        out.append(f"- {r['variant']} {r['qid']} gold: {r['gold_answer'][:110]} | answer: {r['answer'][:150]}")

    out.append("\n## Error examples per category\n")
    def cat(r):
        if r["answerable"] == "False":
            return "false_answer" if r["status"] == "answered" else None
        if r["status"].startswith("abstained"):
            return "false_refusal"
        if r["correctness"] == "correct":
            return None
        if r["retrieval_hit"] != "True":
            return "retrieval_miss"
        if r["faithfulness"] and float(r["faithfulness"]) < 1:
            return "unsupported"
        return "faithful_but_wrong_or_partial"
    groups = defaultdict(list)
    for r in rows:
        c = cat(r)
        if c:
            groups[c].append(r)
    for c, rs in sorted(groups.items()):
        out.append(f"### {c} ({len(rs)} answers; by variant {dict(Counter(r['variant'] for r in rs))})\n")
        seen = set()
        for r in rs:
            if r["qid"] in seen:
                continue
            seen.add(r["qid"])
            if len(seen) > args.examples:
                break
            out.append(f"- **{r['qid']}** [{r['type']}] {r['variant']} corr={r['correctness']} faith={r['faithfulness'] or '-'} hit={r['retrieval_hit'] or '-'}\n"
                       f"  - Q: {r['question'][:140]}\n  - gold: {r['gold_answer'][:140]}\n  - answer: {r['answer'][:220]}")
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out)[:6500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
