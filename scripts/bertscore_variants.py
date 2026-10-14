"""BERTScore variants that are more sensitive than the whole-answer F1, chosen on DEV and reported on TEST (Track C, plan E-1).

    python -X utf8 scripts/bertscore_variants.py --dev-eval data/index/runs/eval/dev_p2_N7 --dev-answers A=data/index/runs/gen/dev-A/answers.jsonl ... \
        --test-answers A=data/index/runs/gen/test-A/answers.jsonl ... --chunks data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl --out data/index/runs/eval/bertscore_variants.json

Why: with the frozen BERTScore (whole answer, F1, bge-m3 layer 8) the three retrieval variants score the same on test although their correctness differs by ~0.09:
F1 moves only ~0.018 between a correct and a not-correct answer, and the answers are longer than the references (up to 3 claims), so Precision is low by construction.
Candidates, declared before looking at test (layer 8, idf from the dev gold answers, as frozen):
  answer_f1        the frozen metric: all claims joined, F1
  answer_recall    all claims joined, Recall
  bestclaim_f1     the claim closest to the reference (max F1 over claims)
  bestclaim_recall the claim closest to the reference (max Recall over claims)
Rule: the candidate with the highest AUC (judged-correct vs judged-not-correct answers, dev, labels from the luna judge) is reported on test next to the frozen
metric. Also given: each candidate rescaled with a baseline b, the mean score of the same answers against the reference of another random question,
(score - b) / (1 - b); rescaling does not change a ranking or an AUC, it only puts the scale back (course slide L14 p35).
The test answers were already generated and the frozen metric already reported; nothing here changes them.
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
sys.path.insert(0, str(ROOT / "scripts"))

import eval_generation as eg  # noqa: E402
from ncdqa.eval.bertscore import BertScorer  # noqa: E402

SC = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}


def auc(pos, neg):
    if not pos or not neg:
        return None
    return round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 4)


def candidates(scorer: BertScorer, claims: list[str], gold: str) -> dict[str, float]:
    whole = scorer.score(" ".join(claims), gold)
    each = [scorer.score(c, gold) for c in claims]
    return {"answer_f1": whole["f1"], "answer_recall": whole["recall"],
            "bestclaim_f1": max(s["f1"] for s in each), "bestclaim_recall": max(s["recall"] for s in each)}


def collect(answers: dict[str, Path], units: dict, scorer: BertScorer, profile: str = "N7") -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for name, path in answers.items():
        out[name] = {}
        for r in eg.read_jsonl(path):
            if not r["answerable"]:
                continue
            rv = eg.revalidate(r, units, profile)
            if rv["status"] != "answered" or not rv["claims"]:
                continue
            claims = [c["text"] for c in rv["claims"]]
            out[name][r["qid"]] = {"claims": claims, "gold": r["gold_answer"], **candidates(scorer, claims, r["gold_answer"])}
    return out


def baseline(scorer: BertScorer, items: dict[str, dict[str, dict]], seed: int = 20261011) -> dict[str, float]:
    rng = random.Random(seed)
    golds = sorted({v["gold"] for d in items.values() for v in d.values()})
    acc: dict[str, list[float]] = {}
    for d in items.values():
        for v in d.values():
            other = rng.choice([g for g in golds if g != v["gold"]])
            for k, x in candidates(scorer, v["claims"], other).items():
                acc.setdefault(k, []).append(x)
    return {k: sum(x) / len(x) for k, x in acc.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dev-eval", type=Path, required=True, help="eval folder of the dev run whose per_question.csv holds the judge labels")
    ap.add_argument("--dev-answers", nargs="+", required=True)
    ap.add_argument("--test-answers", nargs="+", required=True)
    ap.add_argument("--test-eval", type=Path, required=True, help="eval folder of the test run (judge labels, for the by-correctness table)")
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--questions", type=Path, default=ROOT / "data/handoff/track_c_20261012/questions_all_reviewed.jsonl")
    ap.add_argument("--layer", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    units = {c["chunk_id"]: c for c in eg.read_jsonl(args.chunks)}
    dev_gold = sorted({q["answer"] for q in eg.read_jsonl(args.questions) if q["split"] == "dev" and q["status"] == "gold" and q["answer"]})
    scorer = BertScorer("BAAI/bge-m3", args.layer, dev_gold)   # not changed: this script measures variants of the old (special tokens dropped) scoring
    parse = lambda xs: {n: Path(p) for n, _, p in (x.partition("=") for x in xs)}  # noqa: E731

    dev = collect(parse(args.dev_answers), units, scorer)
    labels = {(r["variant"], r["qid"]): r["correctness"] for r in csv.DictReader((args.dev_eval / "per_question.csv").open(encoding="utf-8-sig"))}
    table = {}
    for k in ("answer_f1", "answer_recall", "bestclaim_f1", "bestclaim_recall"):
        good = [v[k] for n, d in dev.items() for q, v in d.items() if labels.get((n, q)) == "correct"]
        notc = [v[k] for n, d in dev.items() for q, v in d.items() if labels.get((n, q)) in ("partial", "wrong")]
        wrong = [v[k] for n, d in dev.items() for q, v in d.items() if labels.get((n, q)) == "wrong"]
        table[k] = {"auc_vs_not_correct": auc(good, notc), "auc_vs_wrong": auc(good, wrong), "n_correct": len(good), "n_not_correct": len(notc), "n_wrong": len(wrong)}
    chosen = max(table, key=lambda k: table[k]["auc_vs_not_correct"] or 0)
    b = baseline(scorer, dev)

    test = collect(parse(args.test_answers), units, scorer)
    tlabels = {(r["variant"], r["qid"]): r["correctness"] for r in csv.DictReader((args.test_eval / "per_question.csv").open(encoding="utf-8-sig"))}
    report: dict = {}
    for k in ("answer_f1", chosen) if chosen != "answer_f1" else ("answer_f1",):
        report[k] = {}
        for n, d in test.items():
            xs = [v[k] for v in d.values()]
            report[k][n] = {"mean": eg.ci_mean(xs), "rescaled_mean": round((sum(xs) / len(xs) - b[k]) / (1 - b[k]), 4)}
        for a_, b_ in (("A", "B"), ("A", "C"), ("B", "C")):
            report[k][f"{b_} - {a_}"] = eg.paired_diff({q: v[k] for q, v in test[a_].items()}, {q: v[k] for q, v in test[b_].items()})
        by_c: dict = {}
        for n, d in test.items():
            for q, v in d.items():
                by_c.setdefault(tlabels.get((n, q), "?"), []).append(v[k])
        report[k]["by_correctness"] = {c: {"n": len(x), "mean": round(sum(x) / len(x), 4)} for c, x in by_c.items()}
    res = {"layer": args.layer, "profile": "N7", "dev_selection": table, "chosen_on_dev": chosen, "baseline_b_dev": {k: round(v, 4) for k, v in b.items()}, "test": report}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dev_selection": table, "chosen": chosen, "baseline": res["baseline_b_dev"]}, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
