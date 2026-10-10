"""List other corpus pages that may state the same fact as a question's evidence page (candidates for extra gold pages).

A question has one evidence page, but guidelines repeat facts across documents; a retriever that returns another correct
page is scored as a miss. For every answerable question this lists pages in OTHER places that (a) share most of the
evidence quote's character shingles, or (b) contain every number of the answer and share much of the question's wording.
It only proposes: a person must read each candidate and decide whether it truly answers the question.

Usage:
    python -X utf8 scripts/find_alt_evidence.py --corpus data/processed/normalized-v11 \
        --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl --out alt_evidence.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHINGLE = 6
NUM = re.compile(r"\d+(?:[.,]\d+)?")


def norm(text: str) -> str:
    return re.sub(r"[\s\u200b]+", "", text)


def shingles(text: str, n: int = SHINGLE) -> set[str]:
    t = norm(text)
    return {t[i:i + n] for i in range(max(0, len(t) - n + 1))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--questions", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-quote", type=float, default=0.8)
    ap.add_argument("--min-num", type=float, default=0.45)
    args = ap.parse_args(argv)

    pages: dict[tuple[str, int], tuple[str, set[str]]] = {}
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        for line in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                if row.get("status") in ("ok", "ok_minor_issues", "ocr_unreviewed", "degraded") and not row.get("index_exclusion"):
                    pages[(folder.name, row["pdf_page"])] = (norm(row["text"]), shingles(row["text"]))

    questions = [json.loads(x) for f in args.questions for x in f.read_text(encoding="utf-8").split("\n") if x.strip()]
    out = []
    for q in questions:
        if not q.get("answerable", True) or not q.get("evidence"):
            continue
        own = {(e["document_id"], e["pdf_page"]) for e in q["evidence"]}
        quote_sh = set().union(*(shingles(e["quote"]) for e in q["evidence"]))
        nums = {n for n in NUM.findall(q.get("answer") or "")}
        q_sh = shingles(q["question"], 4)
        cands = []
        for key, (text, sh) in pages.items():
            if key in own:
                continue
            by_quote = len(quote_sh & sh) / max(1, len(quote_sh))
            by_num = 0.0
            if nums and all(n in text for n in nums):
                by_num = len(q_sh & shingles(text, 4)) / max(1, len(q_sh))
            if by_quote >= args.min_quote or by_num >= args.min_num:
                cands.append({"document_id": key[0], "pdf_page": key[1], "quote_overlap": round(by_quote, 2),
                              "answer_numbers_and_question_overlap": round(by_num, 2)})
        cands.sort(key=lambda c: -max(c["quote_overlap"], c["answer_numbers_and_question_overlap"]))
        if cands:
            out.append({"qid": q.get("qid") or q.get("frame_id"), "split": q.get("split"), "evidence": sorted(own),
                        "candidates": cands[:5]})
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8", newline="\n")
    print(f"{len(out)} of {len(questions)} questions have candidate pages elsewhere -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
