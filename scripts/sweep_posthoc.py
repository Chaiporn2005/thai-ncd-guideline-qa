"""Post-hoc paired comparisons on a finished hybrid sweep (Track B): every candidate against the dense-only run.

The sweep compares candidates inside a stage; the question that matters is also "does adding BM25 beat dense alone?". This reads
`sweep_results.json`, pairs each entry with the dense-only entry on the same questions and prints the difference with a 95%
bootstrap interval (metric default recall@5 and mrr@10).

Usage:
    python -X utf8 scripts/sweep_posthoc.py --sweep data/index/sweeps/hybrid-v1-bge-m3 [--stage A_tokenizer_hybrid_rrf ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import evaluate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sweep", type=Path, required=True)
    ap.add_argument("--stage", nargs="*", help="stage names to include (default: all)")
    ap.add_argument("--metrics", nargs="+", default=["recall@5", "mrr@10"])
    args = ap.parse_args(argv)
    data = json.loads((args.sweep / "sweep_results.json").read_text(encoding="utf-8"))
    dense = next(r for r in data["results"] if r["name"] == "dense_parent_child_only")
    print(f"vs dense-only parent-child ({data['questions']} dev questions, silver): paired difference, 95% bootstrap interval\n")
    print("| stage | candidate | " + " | ".join(f"{m} (diff, CI)" for m in args.metrics) + " | better/worse/tie on recall@5 |")
    print("|---|---|" + "---|" * (len(args.metrics) + 1))
    for r in data["results"]:
        if r["name"] == "dense_parent_child_only" or (args.stage and r["stage"] not in args.stage):
            continue
        cells = []
        for m in args.metrics:
            p = evaluate.paired_bootstrap({q: v[m] for q, v in dense["per_question"].items()}, {q: v[m] for q, v in r["per_question"].items()})
            cells.append(f"{p['mean_diff']:+.3f} ({p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f})")
            if m == "recall@5":
                wins = f"{p['b_better']}/{p['a_better']}/{p['ties']}"
        print(f"| {r['stage']} | {r['name']} | " + " | ".join(cells) + f" | {wins} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
