"""Build the question-review pages (one HTML file per reviewer) from the silver questions.

Questions are grouped by document so a reviewer works through whole documents, and the groups are dealt out so each
part has about the same number of questions. Each page keeps the reviewer's choices in the browser; the reviewer
exports a JSON file and sends it back.

Two kinds of page:
* part 1 (`--local-part`, the owner's) embeds the full text of every evidence page. It also takes every question
  from documents under the rights conflict (Siriraj, Decision 0008: text stays local). Keep that file out of Git.
* the other parts carry only the question, the draft answer, the short evidence quote and the public source link, so
  they can be committed and opened by a teammate who does not have the corpus.

Usage:
    python -X utf8 scripts/build_question_review.py --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl \
        --corpus data/processed/normalized-v11 --parts 4 --shared-dir data/questions/review \
        --local-dir data/agent_runs/20261010-silver-questions/review
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = Path(__file__).with_name("question_review.html")


def deal(questions: list[dict], parts: int, pinned_docs: set[str]) -> list[list[dict]]:
    """Whole documents per part; pinned documents (text must stay local) all go to part 1."""
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        by_doc[q["evidence"][0]["document_id"]].append(q)
    out: list[list[dict]] = [[] for _ in range(parts)]
    for doc in sorted(pinned_docs & set(by_doc)):
        out[0].extend(by_doc.pop(doc))
    for _, group in sorted(by_doc.items(), key=lambda kv: -len(kv[1])):
        min(out, key=len).extend(group)  # the lightest part takes the next-largest document
    return [sorted(p, key=lambda q: q["qid"]) for p in out]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--parts", type=int, default=4)
    ap.add_argument("--shared-dir", type=Path, required=True, help="parts 2..N (no page text): safe to commit")
    ap.add_argument("--local-dir", type=Path, required=True, help="part 1 (full page text): keep local")
    args = ap.parse_args(argv)

    questions = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    docs = {json.loads(x)["document_id"]: json.loads(x) for x in
            (ROOT / "data/manifests/documents.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()}
    rights = json.loads((ROOT / "data/manifests/rights_review_20261005.json").read_text(encoding="utf-8"))["records"]
    pinned = {r["document_id"] for r in rights if "rights_conflict" in json.dumps(r)}

    pages: dict[str, str] = {}
    for doc in {e["document_id"] for q in questions for e in q["evidence"]}:
        for line in (args.corpus / doc / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                pages[f"{doc}:p{row['pdf_page']}"] = row["text"]

    def url_for(doc: str) -> str:
        meta = docs[doc]
        return meta.get("landing_url") or meta.get("download_url") or ""

    template = HTML.read_text(encoding="utf-8")
    summary = []
    for n, part in enumerate(deal(questions, args.parts, pinned), 1):
        local = n == 1
        shown = [{**q, "evidence": [{**e, "url": url_for(e["document_id"])} for e in q["evidence"]]} for q in part]
        data = {"part_id": f"part{n}of{args.parts}", "part_label": f"ส่วนที่ {n} จาก {args.parts}", "questions": shown,
                "pages": {f"{e['document_id']}:p{e['pdf_page']}": pages[f"{e['document_id']}:p{e['pdf_page']}"]
                          for q in part for e in q["evidence"]} if local else {}}
        blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # "</" inside a script block would end it
        folder = args.local_dir if local else args.shared_dir
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"review_part{n}.html").write_text(template.replace("/*DATA*/null", blob), encoding="utf-8")
        summary.append({"part": n, "where": "local (full page text)" if local else "shared (quotes only)",
                        "questions": len(part), "documents": len({q["evidence"][0]["document_id"] for q in part}),
                        "dev": sum(q["split"] == "dev" for q in part), "test": sum(q["split"] == "test" for q in part),
                        "rights_conflict_questions": sum(q["evidence"][0]["document_id"] in pinned for q in part)})
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
