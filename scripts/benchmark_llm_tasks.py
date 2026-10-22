"""Can this API play the answer-generation role? Answer from a page, and refuse when the page is irrelevant (Track B / D pipeline check).

Two small tests per provider on dev questions (cached, temperature 0, deterministic settings of the providers file):
* answer   : question + the parent chunk that holds the gold evidence -> the model must answer in Thai from that text only.
             Score = key-term recall: the share of the gold answer's numbers/Latin terms/Thai words (length >= 2) that appear in the
             model's answer. An automatic proxy, not a judgement of correctness.
* abstain  : the same question with a chunk from a different document -> the model must say the information is not in the text.
             Refusal rate here should be high. The refusal rate in the `answer` test (given the right page) should be low.
Refusal = the answer contains "ไม่พบ" / "ไม่มีข้อมูล" / "ไม่ระบุ" / "ไม่สามารถ" (our proxy). Samples are small: use them to exclude a provider
that clearly fails, not to rank close ones.

Usage:
    python -X utf8 scripts/benchmark_llm_tasks.py --provider typhoon_api --questions <questions.jsonl> --parents data/index/chunks-v11-t512 \
        --n 20 --workers 4 --out data/index/llm_api/tasks_typhoon_api.json
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.llm.client import LLMClient, load_providers  # noqa: E402
from ncdqa.llm.env import load_env  # noqa: E402
from ncdqa.retrieval import evaluate  # noqa: E402
from ncdqa.retrieval.thai_tokens import tokenize  # noqa: E402

SYSTEM = ("คุณเป็นผู้ช่วยตอบคำถามจากข้อความแนวทางเวชปฏิบัติที่ให้มาเท่านั้น ตอบเป็นภาษาไทยสั้นกระชับไม่เกินสองประโยค "
          "ถ้าข้อความที่ให้ไม่มีคำตอบ ให้ตอบเพียงว่า \"ไม่พบข้อมูลในข้อความที่ให้\" ห้ามใช้ความรู้นอกข้อความและห้ามเดา")
REFUSAL = re.compile(r"ไม่พบ|ไม่มีข้อมูล|ไม่ระบุ|ไม่สามารถ|ไม่ได้กล่าว")


def messages(question: str, context: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"ข้อความ:\n{context[:2500]}\n\nคำถาม: {question}"}]


def terms(text: str) -> set[str]:
    return {t for t in tokenize(text, "newmm_latin") if len(t) >= 2 or t.isdigit()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--provider", required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--parents", type=Path, required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    load_env()
    cfg = load_providers(ROOT / "configs/llm/providers.yaml")[args.provider]
    client = LLMClient(cfg, ROOT / "data/index/llm_cache" / f"{args.provider}.jsonl")
    parents = [json.loads(x) for x in (args.parents / "chunks.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    qs = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    qs = [q for q in qs if q["split"] == "dev" and q["answerable"] and len(q["evidence"]) == 1 and q["status"] != "rejected" and "??" not in q["question"]]
    rng = random.Random(20261010)
    rng.shuffle(qs)
    items = []
    for q in qs:
        ev = q["evidence"][0]
        right = next((p for p in parents if evaluate.covers(p, ev)), None)
        wrong = rng.choice([p for p in parents if p["document_id"] != ev["document_id"]])
        if right:
            items.append((q, right, wrong))
        if len(items) >= args.n:
            break

    def ask(job):
        kind, q, ctx = job
        start = time.perf_counter()
        try:
            r = client.complete(messages(q["question"], ctx["text"]), max_tokens=200)
            return {"kind": kind, "qid": q["qid"], "text": r.text.strip(), "finish": r.finish_reason, "latency": time.perf_counter() - start, "error": None}
        except Exception as err:
            return {"kind": kind, "qid": q["qid"], "text": "", "finish": None, "latency": time.perf_counter() - start, "error": type(err).__name__}

    jobs = [("answer", q, right) for q, right, _ in items] + [("abstain", q, wrong) for q, _, wrong in items]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(ask, jobs))
    by = {q["qid"]: q for q, _, _ in items}
    ans = [r for r in results if r["kind"] == "answer"]
    ab = [r for r in results if r["kind"] == "abstain"]
    recalls = []
    for r in ans:
        gold = terms(by[r["qid"]]["answer"] or "")
        if gold and not r["error"]:
            recalls.append(len(gold & terms(r["text"])) / len(gold))
    summary = {"provider": args.provider, "model": cfg.model, "n": len(items),
               "answer_key_term_recall_mean": round(sum(recalls) / len(recalls), 3) if recalls else None,
               "false_refusal_with_right_page": round(sum(bool(REFUSAL.search(r["text"])) for r in ans) / max(len(ans), 1), 3),
               "refusal_with_irrelevant_page": round(sum(bool(REFUSAL.search(r["text"])) for r in ab) / max(len(ab), 1), 3),
               "empty_or_cut": sum(1 for r in results if not r["text"] or r["finish"] == "length"),
               "errors": sum(1 for r in results if r["error"]),
               "latency_median_s": round(sorted(r["latency"] for r in results)[len(results) // 2], 2)}
    args.out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
