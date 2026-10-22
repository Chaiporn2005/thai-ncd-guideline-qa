"""Score generated answers: BERTScore, Faithfulness, Answer correctness, citation, abstention, retrieval hit, failure taxonomy (Track C).

    python -X utf8 scripts/eval_generation.py --answers A=data/index/runs/gen/dev-A/answers.jsonl B=data/index/runs/gen/dev-B/answers.jsonl \
        --chunks data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl --bert-model FacebookAI/xlm-roberta-base --bert-layer 9 \
        --validator N5 --out data/index/runs/eval/dev1

Input is one or more `run_generation.py` outputs (name=path). The validator profile is recomputed offline from the saved raw model output, so the
same generation can be scored under N2 (citations only), N5 (+numbers in the cited evidence) or N7 (+Latin words) without new LLM calls.
Judges (Faithfulness, Correctness) run through `agy` (gemini-3.8-flash-high), cached in data/index/llm_cache/judge.jsonl; a failed judge call leaves the
metric empty for that question and is counted, never guessed. No human has checked the judge (owner's decision E5): results are "as judged by the model".
Output folder: metrics.json (per variant + paired comparisons), per_question.csv, manifest.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.eval import agy_client, correctness, correctness_batch, faithfulness  # noqa: E402
from ncdqa.rag import prompt as prompt_mod  # noqa: E402
from ncdqa.rag.guardrail_eval import wilson  # noqa: E402
from ncdqa.rag.validate import validate  # noqa: E402

PROFILES = {"N2": dict(check_claims=False, check_tokens=False), "N5": dict(check_claims=True, check_tokens=False), "N7": dict(check_claims=True, check_tokens=True),
            "N8": dict(check_claims=True, check_tokens=True, own_numbers=True),
            "V2": dict(check_claims=True, check_tokens=True, own_numbers=True, reattribute=True, drop_denials=True, population=True),      # V2 = N8 + re-point citation, drop denials, group check; N8 = N7 + numbers the user wrote in the question are allowed in a claim
            "V3": dict(check_claims=True, check_tokens=True, own_numbers=True, reattribute=True, drop_denials=True, population=True, header=True)}      # V3 = V2 + the evidence block shows header_text
SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "no_answer": 0.0}
ABSTAIN = ("abstained_model", "abstained_validator", "abstained_no_evidence")


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def shown_unit(u: dict, header: bool) -> dict:
    """A chunk as the model saw it: with the V3 profile its header_text is part of the evidence text (src/ncdqa/rag/prompt.py shown_text)."""
    return {**u, "text": prompt_mod.shown_text(u, {"evidence_header": header})}


def revalidate(row: dict, units: dict, profile: str) -> dict:
    """Kept claims and status of a saved answer under a validator profile (same rules as the live pipeline, applied to the saved raw output)."""
    t = row["trace"]
    if "raw_output" not in t or "evidence" not in t:
        return {"status": row["status"], "claims": [], "dropped": []}
    header = bool(PROFILES[profile].get("header"))
    evidence = {sid: shown_unit(units[cid], header) for sid, cid in t["evidence"].items()}
    prof = dict(PROFILES[profile])
    own = prof.pop("own_numbers", False)
    prof.pop("header", None)
    v = validate(t["raw_output"], evidence, question=row.get("question") if (own or prof.get("population")) else None, own_numbers=own, **prof)
    if not v.parsed:
        return {"status": "parse_error", "claims": [], "dropped": []}
    status = "abstained_model" if v.abstain else ("answered" if v.kept else "abstained_validator")
    return {"status": status, "claims": v.kept, "dropped": v.dropped}


def fit_prompt(claims: list[str], ctx_by_sid: dict, cited: set, limit: int = 26000, question: str | None = None) -> tuple[str, bool]:
    """Faithfulness prompt that fits the judge's command-line limit. An agent can see many chunks; the cited ones are kept first, the others are dropped from the end
    until the prompt fits. Returns (prompt, trimmed). A fixed-pipeline answer (5 chunks) never needs trimming."""
    order = [k for k in ctx_by_sid if k in cited] + [k for k in ctx_by_sid if k not in cited]
    keep = list(order)
    while True:
        prompt = faithfulness.build_prompt(claims, [ctx_by_sid[k] for k in keep], question)
        if len(prompt) <= limit or len(keep) <= 1:
            return prompt, len(keep) < len(order)
        keep.pop()


def gold_hit(chunk_ids: list[str], units: dict, gold: list[dict]) -> bool:
    for cid in chunk_ids:
        u = units[cid]
        if any(u["document_id"] == g["document_id"] and u["pdf_page_start"] <= g["pdf_page"] <= u["pdf_page_end"] for g in gold):
            return True
    return False


def cite_ok(claims: list[dict], evidence_ids: dict, units: dict, gold: list[dict]) -> bool:
    used = {s for c in claims for s in c["cite"]}
    return gold_hit([evidence_ids[s] for s in used if s in evidence_ids], units, gold)


def ci_mean(xs: list[float], n_boot: int = 2000, seed: int = 20261011) -> dict:
    if not xs:
        return {"mean": None, "n": 0}
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n_boot))
    return {"mean": round(sum(xs) / len(xs), 4), "ci95": [round(means[int(.025 * n_boot)], 4), round(means[int(.975 * n_boot)], 4)], "n": len(xs)}


def paired_diff(a: dict[str, float], b: dict[str, float], n_boot: int = 2000, seed: int = 20261011) -> dict:
    keys = sorted(set(a) & set(b))
    if not keys:
        return {"n": 0}
    d = [b[k] - a[k] for k in keys]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n_boot))
    return {"n": len(d), "mean_diff_b_minus_a": round(sum(d) / len(d), 4), "ci95": [round(means[int(.025 * n_boot)], 4), round(means[int(.975 * n_boot)], 4)]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--answers", nargs="+", required=True, metavar="NAME=answers.jsonl")
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--validator", choices=list(PROFILES), default="N5")
    ap.add_argument("--bert-model", default=None, help="encoder for BERTScore (skipped when omitted)")
    ap.add_argument("--bert-layer", type=int, default=None)
    ap.add_argument("--no-idf", action="store_true")
    ap.add_argument("--bert-compat", action="store_true", help="reference-compatible BERTScore (matches the official bert_score package exactly; the default drops the special tokens and is about 0.02 lower per answer)")
    ap.add_argument("--idf-questions", type=Path, help="questions file whose DEV gold answers give the idf weights (so a test run does not use test references for idf)")
    ap.add_argument("--no-judge", action="store_true", help="skip Faithfulness and Correctness (no agy calls)")
    ap.add_argument("--judge", choices=["agy-claude", "codex-luna", "agy", "api"], default="agy-claude",
                    help="agy-claude: claude-sonnet-4-6 through the Antigravity CLI; codex-luna: gpt-5.6-luna, reasoning high, through the Codex CLI "
                         "(the owner's two judges, 2026-10-11); agy: gemini-3.8-flash-high through agy; api: gemini-3.8-flash through the Gemini API "
                         "(the Gemini routes ran out of quota on 2026-10-11)")
    ap.add_argument("--faith-question", action="store_true", help="faithfulness judge also sees the question (statements that lean on the question's own conditions are not marked unsupported); a different metric, report both")
    ap.add_argument("--no-faithfulness", action="store_true", help="correctness (and the rest) only; faithfulness needs one call per answer")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--corr-batch", type=int, default=8, help="answers per correctness judge call")
    ap.add_argument("--judge-cache", type=Path, default=None, help="default: data/index/llm_cache/judge_<route>.jsonl (judge.jsonl for the Gemini routes)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: runs are immutable, choose a new --out")

    units = {c["chunk_id"]: c for c in read_jsonl(args.chunks)}
    runs = {n: read_jsonl(Path(p)) for n, _, p in (a.partition("=") for a in args.answers)}
    started, t0 = datetime.now(timezone.utc), time.perf_counter()

    scorer = None
    if args.bert_model:
        from ncdqa.eval.bertscore import BertScorer
        if args.idf_questions:
            golds = sorted({q["answer"] for q in read_jsonl(args.idf_questions) if q["split"] == "dev" and q["status"] == "gold" and q["answer"]})
        else:
            golds = sorted({r["gold_answer"] for rows in runs.values() for r in rows if r["gold_answer"]})
        scorer = BertScorer(args.bert_model, args.bert_layer, None if args.no_idf else golds, reference_compat=args.bert_compat)

    judge = None
    if not args.no_judge:
        from ncdqa.llm.env import load_env
        load_env()
        cache = args.judge_cache or ROOT / "data/index/llm_cache" / ("judge.jsonl" if args.judge in ("agy", "api") else f"judge_{args.judge}.jsonl")
        if args.judge == "api":
            from ncdqa.eval import api_judge
            judge = api_judge.ApiJudge(cache)
        elif args.judge == "codex-luna":
            from ncdqa.eval import codex_client
            judge = codex_client.CodexJudge(cache)
        elif args.judge == "agy-claude":
            judge = agy_client.AgyJudge(cache, model="claude-sonnet-4-6")
        else:
            judge = agy_client.AgyJudge(cache)
    per_q: dict[str, dict[str, dict]] = {}          # variant -> qid -> fields
    jobs, owners = [], []                           # faithfulness: one judge call per answer
    corr_items: list[tuple[dict, str, str, str]] = []   # correctness: (row fields, question, reference, answer), batched below
    for name, rows in runs.items():
        out = per_q[name] = {}
        for r in rows:
            rv = revalidate(r, units, args.validator)
            ev_ids = r["trace"].get("evidence", {})
            answer = " ".join(c["text"] for c in rv["claims"])
            f = {"qid": r["qid"], "type": r["type"], "answerable": r["answerable"], "status": rv["status"], "n_claims": len(rv["claims"]),
                 "n_dropped": len(rv["dropped"]), "answer": answer, "gold_answer": r["gold_answer"], "retrieval_hit": gold_hit(
                     [h["chunk_id"] for h in r["trace"].get("hits", [])], units, r["gold_evidence"]) if r["answerable"] else None,
                 "latency_s": round((r["trace"].get("llm_s") or 0) + (r["trace"].get("retrieval_s") or 0), 3),
                 "total_tokens": (r["trace"].get("usage") or {}).get("total_tokens"), "question": r["question"]}
            f["abstained"] = rv["status"] in ABSTAIN
            f["citation_ok"] = cite_ok(rv["claims"], ev_ids, units, r["gold_evidence"]) if (r["answerable"] and rv["claims"]) else None
            if r["answerable"] and rv["status"] == "answered":
                if scorer:
                    f.update({f"bert_{k}": v for k, v in scorer.score(answer, r["gold_answer"]).items()})
                f["numbers_covered"] = correctness.numbers_covered(r["gold_answer"], answer)
                if judge:
                    fp, trimmed = fit_prompt([c["text"] for c in rv["claims"]], {sid: shown_unit(units[cid], bool(PROFILES[args.validator].get("header")))["text"] for sid, cid in ev_ids.items()}, {x for c in rv["claims"] for x in c["cite"]},
                                             question=r["question"] if args.faith_question else None)
                    f["contexts_trimmed"] = trimmed
                    jobs.append((fp, faithfulness.SCHEMA)); owners.append(f)
                    corr_items.append((f, r["question"], r["gold_answer"], answer))
            elif r["answerable"]:
                f["correctness"] = "no_answer"
            else:
                f["correctness"] = "correct_abstain" if f["abstained"] else "false_answer"
            out[r["qid"]] = f
    if judge and corr_items:        # correctness first: short prompts, 8 per call, so the metric is complete even if the faithfulness calls are cut short
        slots = correctness_batch.batches(list(range(len(corr_items))), args.corr_batch)
        results = judge.map_calls([(correctness_batch.build_prompt([corr_items[i][1:] for i in b]), correctness_batch.SCHEMA) for b in slots], args.workers)
        for b, res in zip(slots, results):
            try:
                if isinstance(res, Exception):
                    raise ValueError(str(res))
                verdicts = correctness_batch.parse(res.text, len(b))
            except (ValueError, KeyError, json.JSONDecodeError) as err:
                for i in b:
                    corr_items[i][0]["corr_error"] = str(err)[:120]
                continue
            for pos, i in enumerate(b, 1):
                if verdicts[pos] is None:
                    corr_items[i][0]["corr_error"] = "verdict missing in the batch reply"
                else:
                    corr_items[i][0]["correctness"] = verdicts[pos]
    if judge and jobs and not args.no_faithfulness:
        for f, res in zip(owners, judge.map_calls(jobs, args.workers)):
            try:
                if isinstance(res, Exception):
                    raise ValueError(str(res))
                v = faithfulness.parse(res.text, f["n_claims"])
                f["faithfulness"], f["claims_supported"] = faithfulness.score(v), sum(v)
            except (ValueError, KeyError, json.JSONDecodeError) as err:
                f["faith_error"] = str(err)[:120]

    summary: dict = {}
    for name, rows in per_q.items():
        ans = [f for f in rows.values() if f["answerable"]]
        una = [f for f in rows.values() if not f["answerable"]]
        answered = [f for f in ans if f["status"] == "answered"]
        s = {"questions": len(rows), "answerable": len(ans), "unanswerable": len(una), "answered": len(answered)}
        for m in ("bert_f1", "bert_recall", "bert_precision"):
            s[m] = ci_mean([f[m] for f in answered if m in f])
        s["faithfulness"] = ci_mean([f["faithfulness"] for f in answered if f.get("faithfulness") is not None])
        s["correctness_score"] = ci_mean([SCORE[f["correctness"]] for f in ans if f.get("correctness") in SCORE])
        s["correctness_counts"] = dict(Counter(f.get("correctness", "judge_failed") for f in ans))
        nc = [f["numbers_covered"] for f in answered if f.get("numbers_covered") is not None]
        s["numbers_covered"] = {"k": sum(nc), "n": len(nc), "ci95": wilson(sum(nc), len(nc))}
        cc = [f["citation_ok"] for f in answered if f.get("citation_ok") is not None]
        s["citation_correct_given_answered"] = {"k": sum(cc), "n": len(cc), "ci95": wilson(sum(cc), len(cc))}
        s["retrieval_hit"] = {"k": sum(bool(f["retrieval_hit"]) for f in ans), "n": len(ans), "ci95": wilson(sum(bool(f["retrieval_hit"]) for f in ans), len(ans))}
        s["abstention"] = {"unanswerable_abstained": f'{sum(f["abstained"] for f in una)}/{len(una)}', "answerable_refused": f'{sum(f["abstained"] for f in ans)}/{len(ans)}'}
        s["judge_failures"] = sum(1 for f in rows.values() if "faith_error" in f or "corr_error" in f)
        s["latency_s_mean"] = round(sum(f["latency_s"] for f in rows.values()) / len(rows), 3)
        s["tokens_mean"] = round(sum(f["total_tokens"] or 0 for f in rows.values()) / len(rows))
        tax: Counter = Counter()
        for f in rows.values():
            if not f["answerable"]:
                tax["false_answer" if not f["abstained"] else "ok_abstain"] += 1
            elif f["abstained"]:
                tax["false_refusal"] += 1
            elif "correctness" not in f:
                tax["not_judged"] += 1
            elif f["correctness"] == "correct":
                tax["ok"] += 1
            elif not f["retrieval_hit"]:
                tax["retrieval_miss"] += 1
            elif f.get("faithfulness") is not None and f["faithfulness"] < 1:
                tax["unsupported"] += 1
            else:
                tax["faithful_but_wrong_or_partial"] += 1
        s["failure_taxonomy"] = dict(tax)
        summary[name] = s
    comparisons = {}
    names = list(per_q)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for m, key in (("correctness_score", None), ("bert_f1", "bert_f1"), ("faithfulness", "faithfulness")):
                def val(f, m=m, key=key):
                    return SCORE.get(f.get("correctness")) if m == "correctness_score" else f.get(key)
                pa = {q: val(f) for q, f in per_q[a].items() if f["answerable"]}
                pb = {q: val(f) for q, f in per_q[b].items() if f["answerable"]}
                pa = {q: v for q, v in pa.items() if v is not None and pb.get(q) is not None}
                comparisons[f"{b} - {a}: {m}"] = paired_diff(pa, {q: pb[q] for q in pa})
    args.out.mkdir(parents=True)
    (args.out / "metrics.json").write_text(json.dumps({"validator_profile": args.validator, "variants": summary, "paired": comparisons}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cols = ["variant", "qid", "type", "answerable", "status", "n_claims", "n_dropped", "retrieval_hit", "citation_ok", "bert_f1", "bert_precision", "bert_recall",
            "faithfulness", "claims_supported", "correctness", "numbers_covered", "faith_error", "corr_error", "latency_s", "total_tokens", "question", "gold_answer", "answer"]
    with (args.out / "per_question.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, cols, extrasaction="ignore")
        w.writeheader()
        for name, rows in per_q.items():
            for f in rows.values():
                w.writerow({"variant": name, **f})
    manifest = {"run": args.out.name, "inputs": args.answers, "validator_profile": args.validator, "bert_model": args.bert_model, "bert_layer": args.bert_layer,
                "bert_idf": bool(args.bert_model and not args.no_idf), "bert_idf_source": "dev gold answers" if args.idf_questions else "gold answers of the scored runs", "judge": None if args.no_judge else {"model": judge.model, "route": args.judge, "reasoning": "high", "human_checked": False},
                "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
                "started_utc": started.isoformat(timespec="seconds"), "seconds": round(time.perf_counter() - t0, 1)}
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({n: {k: s[k] for k in ("answered", "correctness_score", "faithfulness", "bert_f1")} for n, s in summary.items()}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
