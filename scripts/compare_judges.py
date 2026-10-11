"""Agreement between two judges' scores of the same answers (Track C). Stands in for the human check the owner chose not to do (decision E5).

    python -X utf8 scripts/compare_judges.py --a data/index/runs/eval/dev_agy-claude/per_question.csv --b data/index/runs/eval/dev_codex-luna/per_question.csv \
        --names claude-sonnet-4-6 gpt-5.6-luna --out data/index/runs/eval/dev_judge_agreement.json

Reports, over the answers both judges scored:
  * correctness: raw agreement, Cohen's kappa on the four labels and on correct-vs-not, the confusion matrix;
  * faithfulness: mean absolute difference, Spearman correlation, agreement on "fully faithful" (score = 1);
  * per variant (A/B/C) the mean score under each judge and under the consensus (the mean of the two), and whether the two judges rank the variants alike.
Agreement between two LLM judges shows consistency, not truth: they can share a bias. Kappa near 0.4-0.6 is moderate, above 0.8 strong (Landis & Koch).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "no_answer": 0.0}
LABELS = ("correct", "partial", "wrong", "no_answer")


def kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out, i = [0.0] * len(xs), 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return None if den == 0 else round(num / den, 3)


def load(path: Path) -> dict[tuple[str, str], dict]:
    return {(r["variant"], r["qid"]): r for r in csv.DictReader(path.open(encoding="utf-8-sig"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--names", nargs=2, default=["judge_a", "judge_b"])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    A, B = load(args.a), load(args.b)
    keys = sorted(set(A) & set(B))
    res: dict = {"judges": args.names, "answers_in_common": len(keys)}

    ck = [k for k in keys if A[k]["correctness"] in SCORE and B[k]["correctness"] in SCORE]
    ca, cb = [A[k]["correctness"] for k in ck], [B[k]["correctness"] for k in ck]
    res["correctness"] = {"n": len(ck), "raw_agreement": round(sum(x == y for x, y in zip(ca, cb)) / max(len(ck), 1), 3), "kappa_4_labels": kappa(ca, cb),
                          "kappa_correct_vs_not": kappa([x == "correct" for x in ca] and ["c" if x == "correct" else "n" for x in ca],
                                                        ["c" if x == "correct" else "n" for x in cb]),
                          "confusion_rows_a_cols_b": {x: {y: sum(1 for p, q in zip(ca, cb) if p == x and q == y) for y in LABELS} for x in LABELS}}
    fk = [k for k in keys if A[k]["faithfulness"] not in ("", None) and B[k]["faithfulness"] not in ("", None)]
    fa, fb = [float(A[k]["faithfulness"]) for k in fk], [float(B[k]["faithfulness"]) for k in fk]
    res["faithfulness"] = {"n": len(fk), "mean_abs_diff": round(sum(abs(x - y) for x, y in zip(fa, fb)) / max(len(fk), 1), 3), "spearman": spearman(fa, fb),
                           "kappa_fully_faithful": kappa(["1" if x == 1 else "0" for x in fa], ["1" if y == 1 else "0" for y in fb])}
    per_variant: dict = {}
    for v in sorted({k[0] for k in keys}):
        row: dict = {}
        vc = [k for k in ck if k[0] == v]
        vf = [k for k in fk if k[0] == v]
        row["correctness_score"] = {args.names[0]: round(sum(SCORE[A[k]["correctness"]] for k in vc) / max(len(vc), 1), 3),
                                    args.names[1]: round(sum(SCORE[B[k]["correctness"]] for k in vc) / max(len(vc), 1), 3), "n": len(vc)}
        row["correctness_score"]["consensus_mean"] = round((row["correctness_score"][args.names[0]] + row["correctness_score"][args.names[1]]) / 2, 3)
        row["faithfulness"] = {args.names[0]: round(sum(float(A[k]["faithfulness"]) for k in vf) / max(len(vf), 1), 3),
                               args.names[1]: round(sum(float(B[k]["faithfulness"]) for k in vf) / max(len(vf), 1), 3), "n": len(vf)}
        row["faithfulness"]["consensus_mean"] = round((row["faithfulness"][args.names[0]] + row["faithfulness"][args.names[1]]) / 2, 3)
        per_variant[v] = row
    res["per_variant"] = per_variant
    for metric in ("correctness_score", "faithfulness"):
        res[f"variant_ranking_{metric}"] = {n: sorted(per_variant, key=lambda v: -per_variant[v][metric][n]) for n in args.names}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("answers_in_common", "correctness", "faithfulness")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
