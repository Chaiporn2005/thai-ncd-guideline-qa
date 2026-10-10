"""Write corpus v12: v11 with the pages of one document excluded from search where its hidden text layer disagrees with the page.

DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566 has a white (invisible) text layer that is a near copy of the visible page
with different details (dates such as "1 มิถุนายน – 20 สิงหาคม" that the visible page does not show). The visible glyphs
of that PDF decode to garbage in extraction, so the white layer is what v11 searches (docs/finding_hidden_text_layer.md).
Cutting the hidden lines out was tried and does not work: the two layers are near duplicates line by line, and the visible
layer alone is unreadable text. So v12 does not edit text. It copies v11 and sets `index_exclusion` (the field the
corpus already uses for pages that must not be searched) on the pages whose text contains a date or schedule that cannot
be confirmed on the visible page: every page of the document that mentions June, July or August or a year 2565/2566.
The decision is reversible and recorded per page; the rest of the document stays searchable.

Usage:
    python -X utf8 scripts/make_visible_only_corpus.py --src data/processed/normalized-v11 \
        --out data/processed/normalized-v12 --document-id DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SCHEDULE = re.compile(r"มิถุนายน|กรกฎาคม|สิงหาคม|256[56]")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--document-id", action="append", required=True)
    ap.add_argument("--decided-by", default="claude, on the instruction of the Track B owner")
    ap.add_argument("--decided-at", default="2026-10-11")
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: corpus versions are immutable, choose a new --out")
    shutil.copytree(args.src, args.out)

    for doc in args.document_id:
        pages_file = args.out / doc / "pages.jsonl"
        rows = [json.loads(x) for x in pages_file.read_text(encoding="utf-8").split("\n") if x.strip()]
        excluded = []
        for row in rows:
            text = re.sub(r"\s+", "", row["text"])
            if SCHEDULE.search(text) and not row.get("index_exclusion"):
                row["index_exclusion"] = {"reason": "hidden_text_layer_differs_from_visible_page",
                                          "decided_by": args.decided_by, "decided_at": args.decided_at}
                excluded.append(row["pdf_page"])
        pages_file.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
        (args.out / doc / "v12_changes.json").write_text(json.dumps(
            {"source": str(args.src), "document_id": doc, "rule": SCHEDULE.pattern, "pages_excluded": excluded,
             "pages_total": len(rows)}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{doc}: excluded {len(excluded)} of {len(rows)} pages: {excluded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
