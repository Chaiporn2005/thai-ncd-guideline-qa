"""Check the silver-question drafts an agent wrote and convert the valid ones to `questions.jsonl` (silver).

Every check is mechanical; whether a question is good and its answer right is for the human reviewer. A draft is
rejected here when: the evidence quote is not an exact substring of the page (or is not 25-200 characters), the
question shares a run of 25 or more characters with the evidence page (lexical leak that flatters keyword search),
it names a page/figure/document, it contains an e-mail or phone-like number, its type or answerable flag is
inconsistent, or the frame id is unknown. Rejected drafts are listed with the reason and never dropped silently.

Usage:
    python -X utf8 scripts/validate_silver_questions.py --corpus data/processed/normalized-v11 \
        --run-dir data/agent_runs/20261010-silver-questions
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = {"fact", "number_unit", "condition", "table", "multi_page", "cross_document", "unanswerable"}
LEAK_CHARS = 25
PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}\b")
REFERENCE = re.compile(r"หน้า(?:ที่)?\s*\d|(?<![฀-๿])ภาพที่|(?<![฀-๿])รูปที่|ตารางที่|ตามตาราง(?:นี้|ข้างต้น)|ในเอกสาร(?:นี้|ฉบับนี้)|\.pdf", re.I)


def longest_shared_run(a: str, b: str) -> int:
    return SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size


def check(draft: dict, frame: dict, texts: dict[tuple[str, int], str]) -> list[str]:
    problems: list[str] = []
    if frame is None:
        return ["unknown frame_id"]
    if draft.get("type") not in TYPES:
        problems.append(f"unknown type {draft.get('type')!r}")
    answerable = draft.get("answerable")
    if (draft.get("type") == "unanswerable") == bool(answerable):
        problems.append("type and answerable disagree")
    if (draft.get("answer") is None) == bool(answerable):
        problems.append("answer must be null exactly when unanswerable")
    question = draft.get("question") or ""
    if not question.strip():
        problems.append("empty question")
    if "??" in question or "??" in (draft.get("answer") or ""):
        problems.append("garbled text (Thai lost when the file was written)")
    if REFERENCE.search(question):
        problems.append("question refers to a page, figure, table or document")
    if PERSONAL.search(question) or PERSONAL.search(draft.get("answer") or ""):
        problems.append("question or answer contains a phone number or e-mail")
    evidence = draft.get("evidence") or []
    if not evidence:
        problems.append("no evidence")
    wanted = 2 if draft.get("type") == "multi_page" else 1
    if draft.get("type") != "unanswerable" and len(evidence) < wanted:
        problems.append(f"{draft.get('type')} needs {wanted} evidence page(s)")
    for item in evidence:
        text = texts.get((item.get("document_id"), item.get("pdf_page")))
        quote = item.get("quote", "")
        if text is None:
            problems.append(f"evidence page {item.get('document_id')} p{item.get('pdf_page')} not in corpus")
            continue
        if not 25 <= len(quote) <= 200:
            problems.append(f"quote length {len(quote)} outside 25-200")
        if quote not in text:
            problems.append(f"quote is not an exact substring of p{item.get('pdf_page')}")
        if longest_shared_run(question, text) >= LEAK_CHARS:
            problems.append(f"question shares {longest_shared_run(question, text)} characters with p{item.get('pdf_page')}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--generated-by", default="codex gpt-6-astra (reasoning medium), run 20261010-silver-questions")
    ap.add_argument("--qid-start", type=int, default=1, help="first question number (a supplement continues after the main set)")
    ap.add_argument("--agent-labels", type=json.loads, default={},
                    help='JSON map frame page "agent" -> generated_by text, for runs drafted by several models')
    args = ap.parse_args(argv)

    frame = {p["frame_id"]: p for f in sorted(args.run_dir.glob("frame*.json"))
             for p in json.loads(f.read_text(encoding="utf-8"))["pages"]}
    drafts = [json.loads(x) for f in sorted(args.run_dir.glob("drafts*.jsonl"))
              for x in f.read_text(encoding="utf-8").split("\n") if x.strip()]
    docs = {json.loads(x)["document_id"]: json.loads(x) for x in
            (ROOT / "data/manifests/documents.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()}
    texts: dict[tuple[str, int], str] = {}
    for doc in {p["document_id"] for p in frame.values()}:
        for line in (args.corpus / doc / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                texts[(doc, row["pdf_page"])] = row["text"]

    accepted, rejected, skipped = [], [], []
    for draft in drafts:
        if "skipped" in draft:
            skipped.append({"frame_id": draft.get("frame_id"), "reason": draft["skipped"]})
            continue
        base = (draft.get("frame_id") or "").split("-")[0]
        problems = check(draft, frame.get(base), texts)
        (rejected if problems else accepted).append({"draft": draft, "problems": problems} if problems else draft)

    rows = []
    for n, draft in enumerate(accepted, args.qid_start):
        page = frame[draft["frame_id"].split("-")[0]]
        rows.append({"qid": f"q{n:03d}", "split": page["split"], "status": "silver", "question": draft["question"],
                     "answer": draft["answer"], "type": draft["type"], "answerable": bool(draft["answerable"]),
                     "evidence": [{"document_id": e["document_id"], "edition_id": docs[e["document_id"]]["edition_id"],
                                   "pdf_page": e["pdf_page"], "quote": e["quote"]} for e in draft["evidence"]],
                     "generated_by": args.agent_labels.get(page.get("agent"), args.generated_by), "reviewed_by": None, "review_date": None, "changes": None})
    (args.run_dir / "questions_silver.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
    report = {"drafts": len(drafts), "accepted": len(rows), "rejected": len(rejected), "skipped": len(skipped),
              "by_type": dict(Counter(r["type"] for r in rows)), "by_split": dict(Counter(r["split"] for r in rows)),
              "rejected_detail": rejected, "skipped_detail": skipped,
              "scope": "Mechanical checks only (exact quote, no lexical leak, no references/PII). Not a review of correctness."}
    (args.run_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("_detail")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
