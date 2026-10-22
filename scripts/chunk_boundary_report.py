"""Report how often chunk boundaries cut content that belongs together (Track B, L1 acceptance).

For every pair of consecutive chunks of a document that meet on one page, the cut is classed by looking at the page text:

* `paragraph_end`     the earlier chunk ends on a short or sentence-closing line, or a blank line separates the chunks
* `mid_paragraph`     the earlier chunk ends on a full-width line that does not close a sentence and the next chunk does not start a
                      new list item or table row: the paragraph goes on in the next chunk
* `inside_line`       the cut falls inside a physical line (a forced cut of an over-long paragraph)

Also counted: chunks that start on a Thai
combining mark (a cut inside a word) and chunks below 60 tokens. Page-to-page cuts are counted separately because a
page break is a natural place to cut.

Usage:
    python -X utf8 scripts/chunk_boundary_report.py --chunks data/index/chunks-v11-t256 --corpus data/processed/normalized-v11
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval.chunking import FULL_LINE, LIST_LINE, SENTENCE_END, TABLE_LINE, _usual_width  # noqa: E402

COMBINING = set("ัิีึืฺุู็่้๊๋์ํ๎")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--corpus", type=Path, required=True)
    args = ap.parse_args(argv)

    chunks = [json.loads(x) for x in (args.chunks / "chunks.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        by_doc[c["document_id"]].append(c)
    kinds: Counter = Counter()
    mid_word = short = 0
    for doc, items in by_doc.items():
        pages = {}
        for line in (args.corpus / doc / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                pages[row["pdf_page"]] = row["text"]
        widths = {n: _usual_width([len(x) for x in t.split("\n") if x.strip()]) for n, t in pages.items()}
        for a, b in zip(items, items[1:]):
            if a["pdf_page_end"] != b["pdf_page_start"]:
                kinds["page_or_section_boundary"] += 1
                continue
            text = pages[a["pdf_page_end"]]
            gap = text[a["char_end"]:b["char_start"]]
            if gap.count("\n") >= 2:
                kinds["paragraph_end"] += 1
                continue
            line_start = text.rfind("\n", 0, a["char_end"]) + 1
            line_end = text.find("\n", a["char_end"])
            line_end = len(text) if line_end < 0 else line_end
            if a["char_end"] < line_end and text[a["char_end"]:line_end].strip():
                kinds["inside_line"] += 1
                continue
            last = text[line_start:a["char_end"]]
            starts_unit = bool(LIST_LINE.match(b["text"]) or TABLE_LINE.search(b["text"].split(chr(10))[0]) or b["text"].lstrip().startswith("<"))
            full = len(last) >= FULL_LINE * widths[a["pdf_page_end"]] and not SENTENCE_END.search(last) and not starts_unit
            kinds["mid_paragraph" if full else "paragraph_end"] += 1
        for c in items:
            mid_word += c["text"][:1] in COMBINING
            short += c["token_count"] < 60
    cuts = sum(v for k, v in kinds.items() if k != "page_or_section_boundary")
    report = {"chunks": len(chunks), "cuts_on_one_page": cuts, **dict(kinds),
              "share_cut_inside_paragraph_or_line": round((kinds["mid_paragraph"] + kinds["inside_line"]) / cuts, 3) if cuts else None,
              "chunks_starting_mid_word": mid_word,
              "chunks_under_60_tokens": short}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
