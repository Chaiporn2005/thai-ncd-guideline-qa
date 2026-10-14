"""Re-score BERTScore with the reference-compatible implementation for runs that were already judged (Track C, 2026-10-14).

    python -X utf8 scripts/rescore_bertscore_compat.py --evals test=data/index/runs/eval/test_luna_N7 test=data/index/runs/eval/test_D_luna_N7 test=data/index/runs/eval/test_react-py_luna_N7 \
        dev=data/index/runs/eval/dev_p2_N7 --idf-questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl --out runs/frozen_gen_v1/eval/bertscore_compat.json

Why: the first BERTScore numbers dropped the special tokens (<s>, </s>) from the matching pool; the official bert_score package keeps them with weight 0. scripts/check_bertscore_vs_reference.py shows
the compat mode equals the package to five decimals. Nothing else changes: same encoder (bge-m3), layer 8, idf from the DEV gold answers, same answers (the `answer` column of per_question.csv, i.e.
the claims that passed the validator profile of that eval run), the answered answerable questions only. Reports per system: mean P, R, F1 with a bootstrap interval, the old F1 for comparison, and the
AUC of F1 for judged-correct against not-correct answers (does BERTScore tell right from wrong?).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.eval.bertscore import BertScorer  # noqa: E402


def auc(pos, neg):
    if not pos or not neg:
        return None
    return round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 4)


def ci(xs, n=2000, seed=20261014):
    rng = random.Random(seed)
    means = sorted(st.mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n)], 4)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evals", nargs="+", required=True, help="split=eval_folder (folder with per_question.csv)")
    ap.add_argument("--idf-questions", type=Path, required=True)
    ap.add_argument("--layer", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose another --out")
    qs = [json.loads(x) for x in args.idf_questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    golds = sorted({q["answer"] for q in qs if q["split"] == "dev" and q["status"] == "gold" and q["answer"]})
    scorer = BertScorer("BAAI/bge-m3", args.layer, golds, reference_compat=True)
    out: dict = {"encoder": "BAAI/bge-m3", "layer": args.layer, "mode": "reference_compat (special tokens kept in the pool, weight 0)", "idf": "dev gold answers", "systems": {}}
    for spec in args.evals:
        split, _, folder = spec.partition("=")
        by: dict[str, list[dict]] = {}
        for r in csv.DictReader(open(Path(folder) / "per_question.csv", encoding="utf-8-sig")):
            if r["answerable"] == "True" and r["answer"].strip() and r["gold_answer"].strip():
                by.setdefault(r["variant"], []).append(r)
        for variant, rows in by.items():
            sc = [scorer.score(r["answer"], r["gold_answer"]) for r in rows]
            f = [x["f1"] for x in sc]
            old = [float(r["bert_f1"]) for r in rows if r["bert_f1"] not in ("", "None")]
            cls = {k: [x for x, r in zip(f, rows) if r["correctness"] == k] for k in ("correct", "partial", "wrong")}
            notc = cls["partial"] + cls["wrong"]
            out["systems"][f"{split}:{variant}"] = {
                "n": len(rows), "f1": round(st.mean(f), 4), "f1_ci95": ci(f), "precision": round(st.mean(x["precision"] for x in sc), 4), "recall": round(st.mean(x["recall"] for x in sc), 4),
                "f1_old_special_tokens_dropped": round(st.mean(old), 4) if old else None, "mean_f1_by_judged_class": {k: (round(st.mean(v), 4), len(v)) for k, v in cls.items() if v},
                "auc_correct_vs_notcorrect": auc(cls["correct"], notc)}
            print(split, variant, out["systems"][f"{split}:{variant}"]["f1"], "old", out["systems"][f"{split}:{variant}"]["f1_old_special_tokens_dropped"], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
