"""Choose the BERTScore encoder and layer by a test on dev, not by guessing (Track C, owner's decision E4).

    python -X utf8 scripts/select_bertscore_model.py --per-question data/index/runs/eval/dev_judged/per_question.csv --out data/index/runs/eval/bert_selection_dev.json

Input: per_question.csv of a judged dev run (scripts/eval_generation.py, without --bert-model): each answered question has the answer, the gold answer and
the judge's correctness verdict. For every candidate encoder and layer, two AUCs say how well BERTScore (F1 and Recall, idf on) separates
  * judged-correct answers from judged-wrong answers   (the hard test: same topic, wrong content; partial answers are left out), and
  * an answer with its own gold from the same answer with the gold of another question (the easy floor: right topic or not).
The hard AUC against not-correct answers (wrong + partial, F1) decides: wrong answers alone are too few on dev (7 of 291). Only DEV answers are used, so the test set stays untouched. The judge is an LLM, so the labels are "as judged".
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.eval.bertscore import BertScorer  # noqa: E402

CANDIDATES = {
    "BAAI/bge-m3": [8, 12, 16, 20, 24],
    "intfloat/multilingual-e5-base": [6, 8, 9, 10, 12],
    "FacebookAI/xlm-roberta-base": [6, 8, 9, 10, 12],
    "FacebookAI/xlm-roberta-large": [12, 16, 18, 20, 24],
    "airesearch/wangchanberta-base-att-spm-uncased": [6, 8, 9, 10, 12],
    "google-bert/bert-base-multilingual-cased": [6, 8, 9, 10, 12],
}


def auc(pos: list[float], neg: list[float]) -> float | None:
    """P(random positive scores above random negative), ties count half."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 4)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-question", type=Path, required=True)
    ap.add_argument("--models", nargs="*", default=list(CANDIDATES))
    ap.add_argument("--compat", action="store_true", help="reference-compatible BERTScore (special tokens stay in the matching pool with weight 0, as in the official bert_score package)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    rows = [r for r in csv.DictReader(args.per_question.open(encoding="utf-8-sig")) if r["answer"] and r["gold_answer"] and r["answerable"] == "True"]
    labelled = [r for r in rows if r["correctness"] in ("correct", "partial", "wrong")]
    golds = sorted({r["gold_answer"] for r in rows})
    rng = random.Random(20261011)
    mism = [(r["answer"], rng.choice([g for g in golds if g != r["gold_answer"]])) for r in rows]
    counts = {k: sum(r["correctness"] == k for r in labelled) for k in ("correct", "partial", "wrong")}
    print(f"{len(labelled)} labelled answers {counts}, {len(rows)} answers for the floor test", flush=True)
    if counts["wrong"] < 5:
        print("WARNING: fewer than 5 wrong answers: hard_auc (correct vs wrong) is not meaningful; use hard_auc_notcorrect", flush=True)

    results = []
    for name in args.models:
        try:
            scorer = BertScorer(name, idf_texts=golds, layers=CANDIDATES[name], reference_compat=args.compat)
        except Exception as err:  # not downloaded, or no weights
            print(f"skip {name}: {type(err).__name__}", flush=True)
            continue
        for layer in CANDIDATES[name]:
            def sc(a, g, key):
                return scorer.score(a, g, layer)[key]
            row = {"model": name, "layer": layer}
            for key in ("f1", "recall"):
                good = [sc(r["answer"], r["gold_answer"], key) for r in labelled if r["correctness"] == "correct"]
                row[f"hard_auc_{key}"] = auc(good, [sc(r["answer"], r["gold_answer"], key) for r in labelled if r["correctness"] == "wrong"])
                row[f"hard_auc_notcorrect_{key}"] = auc(good, [sc(r["answer"], r["gold_answer"], key) for r in labelled if r["correctness"] != "correct"])
                row[f"floor_auc_{key}"] = auc([sc(r["answer"], r["gold_answer"], key) for r in rows], [sc(a, g, key) for a, g in mism])
            results.append(row)
            print(row, flush=True)
        del scorer
    best = max((r for r in results if r["hard_auc_notcorrect_f1"] is not None), key=lambda r: r["hard_auc_notcorrect_f1"], default=None)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"input": str(args.per_question), "labelled": len(labelled), "results": results, "best_by_hard_auc_notcorrect_f1": best}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("best:", best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
