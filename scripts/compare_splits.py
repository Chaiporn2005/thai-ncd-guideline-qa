"""Dev vs test side by side for the answer-quality metrics, and whether the ranking of the variants holds (Track C, plan E-9). No judge call.

    python -X utf8 scripts/compare_splits.py --dev data/index/runs/eval/dev_p2_N7 --test data/index/runs/eval/test_luna_N7 --out data/index/runs/eval/dev_vs_test.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROWS = [("correctness score (0-1)", lambda s: s["correctness_score"]["mean"]), ("faithfulness", lambda s: s["faithfulness"]["mean"]),
        ("BERTScore F1", lambda s: (s.get("bert_f1") or {}).get("mean")), ("BERTScore Recall", lambda s: (s.get("bert_recall") or {}).get("mean")),
        ("retrieval hit@5", lambda s: s["retrieval_hit"]["k"] / s["retrieval_hit"]["n"]),
        ("citation correct | answered", lambda s: s["citation_correct_given_answered"]["k"] / s["citation_correct_given_answered"]["n"]),
        ("answerable refused (share)", lambda s: int(s["abstention"]["answerable_refused"].split("/")[0]) / int(s["abstention"]["answerable_refused"].split("/")[1])),
        ("unanswerable abstained (share)", lambda s: int(s["abstention"]["unanswerable_abstained"].split("/")[0]) / int(s["abstention"]["unanswerable_abstained"].split("/")[1]))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev", type=Path, required=True)
    ap.add_argument("--test", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    dev = json.loads((args.dev / "metrics.json").read_text(encoding="utf-8"))
    test = json.loads((args.test / "metrics.json").read_text(encoding="utf-8"))
    names = list(test["variants"])
    lines = ["# Dev vs test (answer quality)\n", f"dev: {args.dev.name} (answerable {dev['variants'][names[0]]['answerable']}), test: {args.test.name} "
             f"(answerable {test['variants'][names[0]]['answerable']}); validator {dev['validator_profile']} / {test['validator_profile']}\n",
             "| metric | " + " | ".join(f"{n} dev | {n} test" for n in names) + " | order dev | order test |", "|---|" + "---|" * (2 * len(names) + 2)]
    for label, get in ROWS:
        cells, vals = [], {"dev": {}, "test": {}}
        for n in names:
            for split, m in (("dev", dev), ("test", test)):
                try:
                    v = get(m["variants"][n])
                except (KeyError, TypeError, ZeroDivisionError):
                    v = None
                vals[split][n] = v
                cells.append("-" if v is None else f"{v:.3f}")
        order = lambda d: " > ".join(sorted((n for n in names if d[n] is not None), key=lambda n: -d[n])) if all(d[n] is not None for n in names) else "-"  # noqa: E731
        lines.append(f"| {label} | " + " | ".join(cells) + f" | {order(vals['dev'])} | {order(vals['test'])} |")
    lines.append("\nPaired differences (mean [95% CI]):\n\n| comparison | dev | test |\n|---|---|---|")
    for key in dev["paired"]:
        if key in test["paired"] and "mean_diff_b_minus_a" in dev["paired"][key] and "mean_diff_b_minus_a" in test["paired"][key]:
            f = lambda p: f"{p['mean_diff_b_minus_a']:+.3f} [{p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}] (n={p['n']})"  # noqa: E731
            lines.append(f"| {key} | {f(dev['paired'][key])} | {f(test['paired'][key])} |")
    lines.append("\nRead with care: the dev and test questions differ, test has only 52 answerable questions, and the judge is one model. An interval that contains 0 means the "
                 "difference cannot be told from noise, not that there is none.")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
