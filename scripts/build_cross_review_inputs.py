"""Build the inputs for model-to-model review of drafted questions (each model reviews the other's questions).

For every question: the question, draft answer, evidence quote(s) and the full text of the evidence page(s). For an
unanswerable question also the pages of the same document that share the most wording with it (the reviewer must
check the document really does not answer it).

Usage:
    python -X utf8 scripts/build_cross_review_inputs.py --corpus data/processed/normalized-v11 --run-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LABEL = {"codex": "astra", "agy": "gemini"}


def norm(t: str) -> str:
    return re.sub(r"[\s\u200b]+", "", t)


def grams(t: str, n: int = 4) -> set[str]:
    t = norm(t)
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--related", type=int, default=6)
    args = ap.parse_args(argv)

    questions = [json.loads(x) for x in (args.run_dir / "questions_silver.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    pages: dict[str, dict[int, str]] = {}
    out: dict[str, list[dict]] = {"astra": [], "gemini": []}
    for q in questions:
        author = LABEL[q["generated_by"].split()[0]]
        reviewer = "gemini" if author == "astra" else "astra"
        item = {"qid": q["qid"], "question": q["question"], "draft_answer": q["answer"], "type": q["type"],
                "answerable": q["answerable"], "evidence": q["evidence"], "evidence_pages": []}
        for e in q["evidence"]:
            doc = pages.setdefault(e["document_id"], {
                json.loads(x)["pdf_page"]: json.loads(x)["text"]
                for x in (args.corpus / e["document_id"] / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()})
            item["evidence_pages"].append({"document_id": e["document_id"], "pdf_page": e["pdf_page"], "text": doc[e["pdf_page"]]})
        if not q["answerable"]:
            doc = pages[q["evidence"][0]["document_id"]]
            qg = grams(q["question"])
            ranked = sorted(doc, key=lambda p: -len(qg & grams(doc[p])) / max(1, len(qg)))[:args.related]
            item["same_document_pages_most_like_the_question"] = [{"pdf_page": p, "text": doc[p]} for p in sorted(ranked)]
        out[reviewer].append(item)
    for reviewer, items in out.items():
        path = args.run_dir / f"review_input_{reviewer}.jsonl"
        path.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8", newline="\n")
        print(reviewer, "reviews", len(items), "questions ->", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
