"""Check that a question's evidence quote is visible text on its PDF page, not only in a hidden (white) text layer.

The extracted page text (`pages.jsonl`) is the whole text layer of the PDF. Some PDFs also carry invisible text: a white
copy of the page (the usual OCR layer of an image page: harmless, the image shows the same words) or, worse, white text
that is NOT on the visible page. DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566 p30 is the second kind: the dates
"1 มิถุนายน - 20 สิงหาคม" exist only as white text, so a person reading the PDF cannot find them, while the extracted text
(and so the retriever) has them.

For each question the script reports the share of the quote's 5-character pieces found in the visible text (fill colour not
white, inside the page box) and in the white text. Low visible coverage means: open the page image and look. It does not
decide (an image page has all its words in the white OCR layer; a page whose PDF text is garbled or OCR-only matches
neither layer); a person confirms. Verdict HIDDEN ONLY is the one to chase.

Usage:
    .venv-ingest/Scripts/python.exe -X utf8 scripts/check_visible_text.py \
        --questions data/agent_runs/20261011-supplement-questions/questions_supplement.jsonl --doc DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
WHITE = ("(1.0,)", "(1, 1, 1)", "(1.0, 1.0, 1.0)", "(0.0, 0.0, 0.0, 0.0)", "1", "1.0")


def collapse(text: str) -> str:
    return re.sub(r"[\s​]+", "", text)


def pieces(text: str) -> set[str]:
    return {text[i:i + 5] for i in range(max(0, len(text) - 4))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, nargs="+", required=True)
    ap.add_argument("--doc", nargs="*", help="document ids to check (default: all that the questions cite)")
    ap.add_argument("--min-visible", type=float, default=0.7)
    args = ap.parse_args(argv)

    questions = [json.loads(x) for f in args.questions for x in f.read_text(encoding="utf-8").split("\n") if x.strip()]
    pdfs: dict[str, pdfplumber.PDF] = {}
    flagged = 0
    for q in questions:
        for e in q["evidence"]:
            doc = e["document_id"]
            if args.doc and doc not in args.doc:
                continue
            pdf = pdfs.setdefault(doc, pdfplumber.open(ROOT / "data/raw" / doc / "source.pdf"))
            page = pdf.pages[e["pdf_page"] - 1]
            width, height = page.width, page.height
            visible = collapse(page.filter(lambda o: o.get("object_type") != "char" or (
                str(o.get("non_stroking_color")) not in WHITE and 0 <= o["x0"] and o["x1"] <= width + 1
                and o["top"] >= -1 and o["bottom"] <= height + 1)).extract_text() or "")
            white = collapse(page.filter(lambda o: o.get("object_type") == "char"
                                         and str(o.get("non_stroking_color")) in WHITE).extract_text() or "")
            want = pieces(collapse(e["quote"]))
            seen, hidden = (len(want & pieces(t)) / max(len(want), 1) for t in (visible, white))
            if seen >= args.min_visible:
                verdict = "ok"
            elif hidden >= args.min_visible:
                verdict = "HIDDEN ONLY: the quote is in white text, not on the visible page (or the page is an image with an OCR layer: look)"
            else:
                verdict = "unclear: PDF text differs from the pipeline text (encoding or OCR); look at the page if in doubt"
            flagged += verdict.startswith("HIDDEN")
            print(f"{q['qid']:5s} {q['split']:5s} {doc[:34]:34s} p{e['pdf_page']:<4d} visible {seen:.2f} white {hidden:.2f}  {verdict}")
    print(f"{flagged} evidence items have the quote only in the hidden layer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
