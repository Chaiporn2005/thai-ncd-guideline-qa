"""Prototype for the hidden-white-text problem: which lines of a corpus page can a reader actually see? (Track B, proposal only)

For one document the script takes each page of the corpus text (`pages.jsonl`, never modified) and classes every line by comparing its
5-character pieces with the PDF's two text layers (pdfplumber, as in check_visible_text.py): the visible layer (fill colour not
white, inside the page box) and the white layer.
  visible      >= --min-visible of the line is in the visible layer
  hidden_only  not visible enough but >= --min-visible is in the white layer (the contaminated case)
  unclear      neither (PDF text differs from the pipeline text: encoding/OCR); kept in the prototype text and listed for a person
The prototype text keeps visible and unclear lines and drops hidden_only lines. It is written to a separate folder as a candidate
`pages.jsonl`; a person decides whether it replaces anything. Pages that are images with a white OCR layer show up as mostly
hidden_only: their lines are listed per page so they are not dropped blindly (`image_ocr_suspect` when a page has almost no visible
characters at all).

Usage:
    .venv-ingest/Scripts/python.exe -X utf8 scripts/prototype_visible_only.py --doc DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566 \
        --corpus data/processed/normalized-v11 --out data/agent_runs/20261011-visible-only-prototype
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


def layers(page) -> tuple[str, str]:
    width, height = page.width, page.height
    visible = collapse(page.filter(lambda o: o.get("object_type") != "char" or (
        str(o.get("non_stroking_color")) not in WHITE and 0 <= o["x0"] and o["x1"] <= width + 1
        and o["top"] >= -1 and o["bottom"] <= height + 1)).extract_text() or "")
    white = collapse(page.filter(lambda o: o.get("object_type") == "char" and str(o.get("non_stroking_color")) in WHITE).extract_text() or "")
    return visible, white


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-visible", type=float, default=0.7)
    ap.add_argument("--min-line", type=int, default=6, help="lines shorter than this many characters are kept (too short to judge)")
    args = ap.parse_args(argv)

    rows = [json.loads(x) for x in (args.corpus / args.doc / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    pdf = pdfplumber.open(ROOT / "data/raw" / args.doc / "source.pdf")
    report, out_rows = [], []
    for row in rows:
        page = pdf.pages[row["pdf_page"] - 1]
        visible, white = layers(page)
        pv, pw = pieces(visible), pieces(white)
        kept, counts, dropped = [], {"visible": 0, "hidden_only": 0, "unclear": 0, "short": 0}, []
        for line in row["text"].split("\n"):
            c = collapse(line)
            if len(c) < args.min_line:
                kept.append(line)
                counts["short"] += 1
                continue
            want = pieces(c)
            seen, hid = len(want & pv) / len(want), len(want & pw) / len(want)
            if seen >= args.min_visible:
                kept.append(line)
                counts["visible"] += 1
            elif hid >= args.min_visible:
                counts["hidden_only"] += 1
                dropped.append(line)
            else:
                kept.append(line)
                counts["unclear"] += 1
        report.append({"pdf_page": row["pdf_page"], "status": row["status"], "visible_chars": len(visible), "white_chars": len(white),
                       "lines": counts, "changed": counts["hidden_only"] > 0,
                       "image_ocr_suspect": len(visible) < 40 and len(white) > 200, "dropped_lines": dropped[:6]})
        out_rows.append({**row, "text": "\n".join(kept), "visible_only_prototype": True, "hidden_lines_dropped": counts["hidden_only"]})
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows), encoding="utf-8", newline="\n")
    summary = {"document": args.doc, "pages": len(rows), "pages_with_hidden_only_lines": sum(r["changed"] for r in report),
               "image_ocr_suspect_pages": [r["pdf_page"] for r in report if r["image_ocr_suspect"]],
               "lines_dropped": sum(r["lines"]["hidden_only"] for r in report), "lines_unclear": sum(r["lines"]["unclear"] for r in report),
               "lines_visible": sum(r["lines"]["visible"] for r in report),
               "chars_before": sum(len(r["text"]) for r in rows), "chars_after": sum(len(r["text"]) for r in out_rows)}
    (args.out / "report.json").write_text(json.dumps({"summary": summary, "pages": report}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
