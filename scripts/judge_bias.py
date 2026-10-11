"""How stable and how biased is the judge? Re-judge the test answers under changed conditions (Track C, plan E-3, judge gpt-5.6-luna high).

    python -X utf8 scripts/judge_bias.py --eval data/index/runs/eval/test_luna_N7 --answers B=data/index/runs/gen/test-B/answers.jsonl --out data/index/runs/eval/judge_bias.json

Checks (course slides L14 p39-41: length bias, positional bias, repeated runs, mitigation):
  batch composition   correctness re-judged with two other shufflings of the 8-per-call batches: do the verdicts stay? (position / neighbour effects)
  batch vs single     48 answers re-judged one per call: does batching change the verdict?
  repeat              faithfulness of 30 answers asked again with the identical prompt (fresh cache): how much does the score move on its own?
  order swap          the same 30 with claims and contexts in reverse order
  length              Spearman correlation of answer length with the correctness score and with faithfulness
Uses its own cache file so the repeat really goes back to the model. Nothing here changes the reported test results; it measures how far they can be trusted.
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

import compare_judges as cj  # noqa: E402
import eval_generation as eg  # noqa: E402
from ncdqa.eval import codex_client, correctness_batch, faithfulness  # noqa: E402
from ncdqa.eval.correctness import build_prompt as single_prompt, parse as parse_single, SCHEMA as SINGLE_SCHEMA  # noqa: E402
from ncdqa.llm.env import load_env  # noqa: E402

SC = cj.SCORE


def rejudge_batches(judge, items, seed, workers):
    slots = correctness_batch.batches(list(range(len(items))), 8, seed)
    res = judge.map_calls([(correctness_batch.build_prompt([items[i] for i in b]), correctness_batch.SCHEMA) for b in slots], workers)
    out = {}
    for b, r in zip(slots, res):
        try:
            if isinstance(r, Exception):
                raise ValueError(str(r))
            v = correctness_batch.parse(r.text, len(b))
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
        for pos, i in enumerate(b, 1):
            if v[pos]:
                out[i] = v[pos]
    return out


def agreement(orig, new):
    ks = [k for k in orig if k in new]
    a, b = [orig[k] for k in ks], [new[k] for k in ks]
    return {"n": len(ks), "raw_agreement": round(sum(x == y for x, y in zip(a, b)) / max(len(ks), 1), 3), "kappa_4_labels": cj.kappa(a, b),
            "kappa_correct_vs_not": cj.kappa(["c" if x == "correct" else "n" for x in a], ["c" if x == "correct" else "n" for x in b])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--eval", type=Path, required=True)
    ap.add_argument("--answers", nargs="+", required=True, help="NAME=answers.jsonl of the runs behind --eval (for the faithfulness re-judging)")
    ap.add_argument("--chunks", type=Path, default=ROOT / "data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl")
    ap.add_argument("--validator", default="N7")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    load_env()
    judge = codex_client.CodexJudge(ROOT / "data/index/llm_cache/judge_codex-luna_bias.jsonl")
    rows = [r for r in csv.DictReader((args.eval / "per_question.csv").open(encoding="utf-8-sig")) if r["answerable"] == "True" and r["correctness"] in SC and r["answer"]]
    items = [(r["question"], r["gold_answer"], r["answer"]) for r in rows]
    orig = {i: r["correctness"] for i, r in enumerate(rows)}
    res: dict = {"judge": judge.model, "answers_judged": len(rows)}

    res["batch_composition"] = {f"seed_{s}": agreement(orig, rejudge_batches(judge, items, s, args.workers)) for s in (101, 102)}
    rng = random.Random(20261011)
    sample = sorted(rng.sample(range(len(rows)), min(48, len(rows))))
    single_res = judge.map_calls([(single_prompt(*items[i]), SINGLE_SCHEMA) for i in sample], args.workers)
    single = {}
    for i, r in zip(sample, single_res):
        try:
            single[i] = parse_single(r.text)
        except Exception:
            pass
    res["batch_vs_single"] = agreement({i: orig[i] for i in sample}, single)

    # faithfulness: repeat and order swap on 30 answers of the first run in --answers
    name, _, path = args.answers[0].partition("=")
    units = {c["chunk_id"]: c for c in eg.read_jsonl(args.chunks)}
    orig_f = {(r["variant"], r["qid"]): float(r["faithfulness"]) for r in csv.DictReader((args.eval / "per_question.csv").open(encoding="utf-8-sig")) if r["faithfulness"]}
    cand = []
    for r in eg.read_jsonl(Path(path)):
        rv = eg.revalidate(r, units, args.validator)
        if r["answerable"] and rv["status"] == "answered" and (name, r["qid"]) in orig_f:
            cand.append((r, rv))
    cand = rng.sample(cand, min(30, len(cand)))

    def ask(reverse: bool):
        jobs = []
        for r, rv in cand:
            claims, ctx = [c["text"] for c in rv["claims"]], [units[c]["text"] for c in r["trace"]["evidence"].values()]
            jobs.append((faithfulness.build_prompt(claims[::-1] if reverse else claims, ctx[::-1] if reverse else ctx), faithfulness.SCHEMA))
        out = []
        for (r, rv), x in zip(cand, judge.map_calls(jobs, args.workers)):
            try:
                v = faithfulness.parse(x.text, len(rv["claims"]))
                out.append(faithfulness.score(v[::-1] if reverse else v))   # claims were reversed: reverse the verdicts back (the score is order-free anyway)
            except Exception:
                out.append(None)
        return out
    base = [orig_f[(name, r["qid"])] for r, _ in cand]
    for label, new in (("repeat_identical_prompt", ask(False)), ("order_swap", ask(True))):
        pairs = [(a, b) for a, b in zip(base, new) if b is not None]
        res[f"faithfulness_{label}"] = {"n": len(pairs), "mean_abs_diff": round(sum(abs(a - b) for a, b in pairs) / max(len(pairs), 1), 3),
                                        "same_score": round(sum(abs(a - b) < 1e-9 for a, b in pairs) / max(len(pairs), 1), 3),
                                        "same_fully_faithful_flag": round(sum((a == 1) == (b == 1) for a, b in pairs) / max(len(pairs), 1), 3)}

    # length bias (no judge call)
    allrows = list(csv.DictReader((args.eval / "per_question.csv").open(encoding="utf-8-sig")))
    lc = [(len(r["answer"]), SC[r["correctness"]]) for r in allrows if r["answerable"] == "True" and r["correctness"] in SC and r["answer"]]
    lf = [(len(r["answer"]), float(r["faithfulness"])) for r in allrows if r["faithfulness"]]
    res["length_bias"] = {"spearman_length_vs_correctness": cj.spearman([a for a, _ in lc], [b for _, b in lc]), "n_correctness": len(lc),
                          "spearman_length_vs_faithfulness": cj.spearman([a for a, _ in lf], [b for _, b in lf]), "n_faithfulness": len(lf)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
