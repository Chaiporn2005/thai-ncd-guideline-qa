"""Compare retrieval runs side by side: metrics, and a paired bootstrap against a baseline run (Track B).

Reads `metrics.json` and `per_question.json` of each run folder. The paired test uses the questions both runs scored; a
difference whose 95% interval includes zero is not evidence that one run is better.

Usage:
    python -X utf8 scripts/compare_runs.py --baseline data/index/runs/dense-e5-base-t512-gpu data/index/runs/*-gpu
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
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--metric", default="recall@5", help="metric used for the paired comparison")
    args = ap.parse_args(argv)

    def load(folder: Path):
        return json.loads((folder / "metrics.json").read_text(encoding="utf-8")), json.loads((folder / "per_question.json").read_text())

    base_metrics, base_q = load(args.baseline)
    base = {q: v[args.metric] for q, v in base_q.items()}
    print(f"baseline: {args.baseline.name}   paired metric: {args.metric}\n")
    print("| run | mode | R@1 | R@5 | R@10 | MRR@10 | table R@5 | multi R@5 | diff vs baseline (95% CI) | better/worse/tie |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for folder in sorted(args.runs):
        m, per_q = load(folder)
        o, t = m["overall"], m["by_type"]
        paired = evaluate.paired_bootstrap(base, {q: v[args.metric] for q, v in per_q.items()})
        diff = "baseline" if folder.resolve() == args.baseline.resolve() else (
            f"{paired['mean_diff']:+.3f} ({paired['ci95'][0]:+.3f}, {paired['ci95'][1]:+.3f})")
        wins = "" if folder.resolve() == args.baseline.resolve() else f"{paired['b_better']}/{paired['a_better']}/{paired['ties']}"
        print(f"| {folder.name} | {m['mode']} | {o['recall@1']:.3f} | {o['recall@5']:.3f} | {o['recall@10']:.3f} | {o['mrr@10']:.3f} | "
              f"{t.get('table', {}).get('recall@5', float('nan')):.3f} | {t.get('multi_page', {}).get('recall@5', float('nan')):.3f} | {diff} | {wins} |")
    print(f"\nquestions: {base_metrics['questions']} ({base_metrics['answerable']} answerable); status: {base_metrics['status_counts']}. {base_metrics['caution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
