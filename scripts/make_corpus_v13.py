"""Write corpus v13: v11 with one document's pages replaced by their visible-only text (Track B, owner's decision 2026-10-11).

DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566 has a white text layer that disagrees with the visible page (docs/finding_hidden_text_layer.md).
`scripts/prototype_visible_only.py` keeps, line by line, the lines of the v11 text that the visible layer of the PDF supports and
drops those found only in the white layer. This script copies v11 and swaps that document's `pages.jsonl` for the prototype's
output, recording per page how many lines were dropped and the SHA-256 of the v11 text it came from; `normalization.json` gets the
new `pages_jsonl_sha256` and a `visible_only` block. Nothing else changes: every other document is byte-identical to v11. v12 (the
whole manual excluded) is left as it is. Corpus versions are immutable, so the output folder must not exist.

Usage:
    python -X utf8 scripts/make_corpus_v13.py --src data/processed/normalized-v11 --out data/processed/normalized-v13 \
        --document-id DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566 --pages data/agent_runs/20261011-visible-only-prototype/pages.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--document-id", required=True)
    ap.add_argument("--pages", type=Path, required=True, help="visible-only pages.jsonl from prototype_visible_only.py")
    ap.add_argument("--decided-by", default="owner of Track B, 2026-10-11")
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: corpus versions are immutable, choose a new --out")
    shutil.copytree(args.src, args.out)

    folder = args.out / args.document_id
    old_rows = [json.loads(x) for x in (args.src / args.document_id / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    new_rows = [json.loads(x) for x in args.pages.read_text(encoding="utf-8").split("\n") if x.strip()]
    if [r["pdf_page"] for r in old_rows] != [r["pdf_page"] for r in new_rows]:
        sys.exit("page lists differ")
    out_rows, dropped = [], 0
    for old, new in zip(old_rows, new_rows):
        row = dict(old)
        row["text"] = new["text"]
        row["visible_only"] = {"v11_text_sha256": hashlib.sha256(old["text"].encode("utf-8")).hexdigest(),
                               "hidden_lines_dropped": new.get("hidden_lines_dropped", 0),
                               "method": "scripts/prototype_visible_only.py (line kept when its 5-char pieces are >= 0.7 in the visible layer)",
                               "decided_by": args.decided_by}
        dropped += row["visible_only"]["hidden_lines_dropped"]
        if not row["text"].strip():
            row["index_exclusion"] = {"reason": "empty_after_visible_only", "decided_by": args.decided_by}
        out_rows.append(row)
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows)
    (folder / "pages.jsonl").write_text(body, encoding="utf-8", newline="\n")
    norm = json.loads((folder / "normalization.json").read_text(encoding="utf-8"))
    norm["pages_jsonl_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    norm["visible_only"] = {"source_version": args.src.name, "hidden_lines_dropped": dropped,
                            "pages_changed": sum(1 for r in out_rows if r["visible_only"]["hidden_lines_dropped"]),
                            "decided_by": args.decided_by, "pages_source": "pdfplumber visible layer vs v11 text"}
    (folder / "normalization.json").write_text(json.dumps(norm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(norm["visible_only"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
