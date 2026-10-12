"""G4 option A (owner's choice, 2026-10-12): calibrate a score threshold for "evidence not enough -> say not found" on DEV only.

    python -X utf8 scripts/calibrate_abstain.py --questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl \
        --results data/handoff/track_c_20261012/results/dev-B/results.jsonl --out data/index/runs/eval/abstain_calibration_dev_B.json

Uses the top-1 retrieval score of each dev question (the same number pipeline.py compares with `abstain.min_top_score`). Reports AUC of "top score separates answerable from
unanswerable" and, for a grid of thresholds, how many unanswerable questions would be refused and how many answerable ones (false refusals). The rule for choosing is stated here
before looking at the numbers: the highest threshold whose false-refusal count on answerable questions is at most `--max-false-refusal` (default 2 of 97, about 2 percent).
Nothing is written to a config: switching the threshold on changes the delivered system and needs a new freeze and one test run (owner's decision).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def auc(pos: list[float], neg: list[float]) -> float:
    """P(score of a random positive > score of a random negative); ties count half."""
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--max-false-refusal", type=int, default=2)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    gold = {q["qid"]: q for q in read_jsonl(args.questions) if q["split"] == "dev" and q["status"] == "gold"}
    top = {r["qid"]: r["hits"][0]["score"] for r in read_jsonl(args.results) if r["qid"] in gold and r["hits"]}
    ans = sorted(top[q] for q in top if gold[q]["answerable"])
    unans = sorted(top[q] for q in top if not gold[q]["answerable"])
    grid = sorted(set(round(s, 3) for s in ans + unans))
    rows = [{"threshold": t, "unanswerable_refused": sum(s < t for s in unans), "answerable_refused": sum(s < t for s in ans)} for t in grid]
    ok = [r for r in rows if r["answerable_refused"] <= args.max_false_refusal]
    chosen = max(ok, key=lambda r: r["threshold"]) if ok else None
    out = {"n_answerable": len(ans), "n_unanswerable": len(unans), "auc_top_score_answerable_vs_unanswerable": round(auc(ans, unans), 3),
           "answerable_top_score": {"min": ans[0], "median": ans[len(ans) // 2], "max": ans[-1]}, "unanswerable_top_score": {"min": unans[0], "median": unans[len(unans) // 2], "max": unans[-1]},
           "rule": f"highest threshold with at most {args.max_false_refusal} answerable questions refused", "chosen": chosen,
           "grid_near_chosen": [r for r in rows if chosen and abs(r["threshold"] - chosen["threshold"]) <= 0.06]}
    text = json.dumps(out, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
