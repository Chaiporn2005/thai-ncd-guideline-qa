"""Check the judge without a human: does it accept what must be accepted and reject what must be rejected? (Track C, plan E-2; the owner chose no human check, E5.)

    python -X utf8 scripts/validate_judge.py --judge codex-luna --n 48 --out data/index/runs/eval/judge_sanity.json

Uses DEV questions only. Two known-answer tests:
  correctness  positives: the answer IS the gold answer of the same question (must be "correct"); negatives: the answer is the gold answer of a different question
               (must not be "correct").
  faithfulness positives: a statement copied from the gold evidence quote of the question, judged against the chunks retrieved for it (variant B), only for
               questions whose retrieval hit the gold page (must be supported); negatives: a statement copied from another question's quote against the same chunks
               (must not be supported). Each call carries the positive and the negative statement for one context.
These are easy cases by design. They show the judge is not broken or lenient on the extremes; they say nothing about its accuracy on the hard middle
(partial answers), which is what the judge-agreement analysis (compare_judges.py, a second model) is for.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import eval_generation as eg  # noqa: E402
from ncdqa.eval import agy_client, codex_client, correctness_batch, faithfulness  # noqa: E402
from ncdqa.llm.env import load_env  # noqa: E402


def wilson_ci(k: int, n: int):
    from ncdqa.rag.guardrail_eval import wilson
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None, "ci95": wilson(k, n)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--judge", choices=["codex-luna", "agy-claude"], default="codex-luna")
    ap.add_argument("--n", type=int, default=48, help="positives (and negatives) per test")
    ap.add_argument("--questions", type=Path, default=ROOT / "data/handoff/track_c_20261012/questions_all_reviewed.jsonl")
    ap.add_argument("--chunks", type=Path, default=ROOT / "data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl")
    ap.add_argument("--dev-answers", type=Path, default=ROOT / "data/index/runs/gen/dev-B/answers.jsonl", help="dev run (variant B) whose trace gives each question's retrieved chunks")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    load_env()
    cache = args.cache or ROOT / "data/index/llm_cache" / f"judge_{args.judge}_sanity.jsonl"
    judge = codex_client.CodexJudge(cache) if args.judge == "codex-luna" else agy_client.AgyJudge(cache, model="claude-sonnet-4-6")
    rng = random.Random(20261011)
    qs = [q for q in eg.read_jsonl(args.questions) if q["split"] == "dev" and q["status"] == "gold" and q["answerable"]]
    units = {c["chunk_id"]: c for c in eg.read_jsonl(args.chunks)}

    # correctness: 2n items = n positives + n negatives, batches of 8 (same batching as the real runs)
    chosen = rng.sample(qs, min(args.n, len(qs)))
    items, truth = [], []
    for q in chosen:
        other = rng.choice([x for x in qs if x["qid"] != q["qid"]])
        items.append((q["question"], q["answer"], q["answer"])); truth.append(True)
        items.append((q["question"], q["answer"], other["answer"])); truth.append(False)
    slots = correctness_batch.batches(list(range(len(items))), 8)
    res = judge.map_calls([(correctness_batch.build_prompt([items[i] for i in b]), correctness_batch.SCHEMA) for b in slots], args.workers)
    pos_ok = neg_ok = pos_n = neg_n = failed = 0
    for b, r in zip(slots, res):
        try:
            if isinstance(r, Exception):
                raise ValueError(str(r))
            v = correctness_batch.parse(r.text, len(b))
        except (ValueError, KeyError, json.JSONDecodeError):
            failed += len(b); continue
        for pos, i in enumerate(b, 1):
            if v[pos] is None:
                failed += 1; continue
            if truth[i]:
                pos_n += 1; pos_ok += v[pos] == "correct"
            else:
                neg_n += 1; neg_ok += v[pos] != "correct"
    correctness_res = {"positives_judged_correct": wilson_ci(pos_ok, pos_n), "negatives_not_judged_correct": wilson_ci(neg_ok, neg_n), "failed_items": failed}

    # faithfulness: statement = quote, context = the chunks B retrieved for the question
    by_q = {q["qid"]: q for q in qs}
    ctx_rows = []
    for r in eg.read_jsonl(args.dev_answers):
        q = by_q.get(r["qid"])
        if not q or "evidence" not in r["trace"] or not q["evidence"]:
            continue
        ids = list(r["trace"]["evidence"].values())
        if eg.gold_hit(ids, units, r["gold_evidence"]) and q["evidence"][0].get("quote"):
            ctx_rows.append((q, [units[c]["text"] for c in ids]))
    ctx_rows = rng.sample(ctx_rows, min(args.n, len(ctx_rows)))
    jobs = []
    for q, ctx in ctx_rows:
        other = rng.choice([x for x in qs if x["qid"] != q["qid"] and x["evidence"] and x["evidence"][0].get("quote")])
        jobs.append((faithfulness.build_prompt([q["evidence"][0]["quote"], other["evidence"][0]["quote"]], ctx), faithfulness.SCHEMA))
    res = judge.map_calls(jobs, args.workers)
    fp_ok = fn_ok = fn = ff = 0
    for r in res:
        try:
            if isinstance(r, Exception):
                raise ValueError(str(r))
            v = faithfulness.parse(r.text, 2)
        except (ValueError, KeyError, json.JSONDecodeError):
            ff += 1; continue
        fn += 1; fp_ok += v[0]; fn_ok += (not v[1])
    faith_res = {"positive_quotes_supported": wilson_ci(fp_ok, fn), "foreign_quotes_not_supported": wilson_ci(fn_ok, fn), "failed_calls": ff}

    out = {"judge": judge.model, "n_requested": args.n, "correctness": correctness_res, "faithfulness": faith_res}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
