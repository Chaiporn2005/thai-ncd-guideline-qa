"""Probe: does showing the judge the QUESTION change Faithfulness verdicts? (error analysis 2026-10-12)

    python -X utf8 scripts/faithfulness_probe.py --answers data/index/runs/gen/test-B/answers.jsonl --chunks data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl \
        --qids q031 q072 q147 q152 q169 q175 --out data/index/runs/eval/faith_probe_test_B.json

Why: some answers are correct, cite the right page and repeat the evidence's number, yet get faithfulness 0 under the strict definition, because the claim is a fragment that leans on the
question ("at least 14 readings" without saying "for a 4-6 hour HBPM"). Each answer is judged twice with the same judge (gpt-5.6-luna high through codex): the current prompt (no question) and
the same prompt with the question and a note that the question's own conditions are understood. Judgements are cached separately from the main judge cache. A control set (answers that were
judged unsupported AND are wrong) shows whether the question note makes the judge generous: it must not flip those.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.eval import codex_client, faithfulness  # noqa: E402
from ncdqa.rag import prompt as prompt_mod  # noqa: E402,F401


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--answers", type=Path, required=True)
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--qids", nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    units = {c["chunk_id"]: c for c in read_jsonl(args.chunks)}
    rows = {r["qid"]: r for r in read_jsonl(args.answers)}
    judge = codex_client.CodexJudge(ROOT / "data/index/llm_cache/judge_codex-luna_probe.jsonl")
    jobs, meta = [], []
    for q in args.qids:
        r = rows[q]
        claims = r.get("claims") or []
        if not claims:
            continue
        ctx_by_sid = {sid: units[cid]["text"] for sid, cid in r["trace"]["evidence"].items()}
        cited = {s for c in claims for s in c["cite"]}
        ctxs = [ctx_by_sid[k] for k in ctx_by_sid if k in cited] + [ctx_by_sid[k] for k in ctx_by_sid if k not in cited]
        texts = [c["text"] for c in claims]
        for variant, question in (("no_question", None), ("with_question", r["question"])):
            jobs.append((faithfulness.build_prompt(texts, ctxs, question), faithfulness.SCHEMA))
            meta.append((q, variant, len(texts)))
    out: dict = {}
    for (q, variant, n), res in zip(meta, judge.map_calls(jobs, args.workers)):
        try:
            v = faithfulness.parse(res.text, n)
            out.setdefault(q, {})[variant] = {"supported": sum(v), "n": n, "score": faithfulness.score(v)}
        except Exception as err:  # noqa: BLE001
            out.setdefault(q, {})[variant] = {"error": type(err).__name__}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for q, v in out.items():
        print(q, {k: (x.get("score") if "score" in x else x) for k, x in v.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
