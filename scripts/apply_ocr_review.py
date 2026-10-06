"""Apply a page-level OCR review file to a corpus version and write a new version.

Every ocr_unreviewed page in the source must have exactly one review entry. Outcomes:
  pass / pass_text_only / fix  -> text corrected as listed, status stays ocr_unreviewed and
                                  human_review records the review (indexable under the intake rule)
  reject                        -> status garbled (never indexed), review recorded
Corrections: "replacements" (every occurrence; each old string must exist), "replace_text",
"truncate_after", "remove_duplicate_block" and "append". Markdown image placeholders and
backslash escapes left by the OCR model are removed from reviewed pages. The original OCR output
stays in ocr_text and the pre-review text in reviewed_from_text.

Usage:
    python -X utf8 scripts/apply_ocr_review.py --source data/processed/normalized-v3 \
        --review data/manifests/ocr_review_20261007.json --out data/processed/normalized-v4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

IMAGE_PLACEHOLDER = re.compile(r"^[ \t]*!\[[^\]]*\]\([^)]*\)[ \t]*(?:\n|$)", re.M)
ESCAPE = re.compile(r"\\([.*_#\[\]()-])")
BLANK_LINES = re.compile(r"\n{3,}")
INDEXABLE = {"pass", "pass_text_only", "fix"}


class ReviewError(ValueError):
    pass


def apply_corrections(text: str, entry: dict) -> str:
    key = entry["key"]
    if "replace_text" in entry:
        text = entry["replace_text"]
    for old, new in entry.get("replacements", []):
        if old not in text:
            raise ReviewError(f"{key}: replacement text not found: {old!r}")
        text = text.replace(old, new)
    block = entry.get("remove_duplicate_block")
    if block:
        start = text.find(block["start"])
        end = text.find(block["end"], start + 1)
        if start < 0 or end < 0:
            raise ReviewError(f"{key}: duplicate block markers not found")
        text = text[:start] + block["keep"] + text[end:]
    marker = entry.get("truncate_after")
    if marker:
        position = text.find(marker)
        if position < 0:
            raise ReviewError(f"{key}: truncate marker not found: {marker!r}")
        text = text[:position + len(marker)]
    text += entry.get("append", "")
    text = ESCAPE.sub(r"\1", IMAGE_PLACEHOLDER.sub("", text))
    return BLANK_LINES.sub("\n\n", text).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists; corpus versions are never overwritten")

    review = json.loads(args.review.read_text(encoding="utf-8"))
    entries = {}
    for entry in review["pages"]:
        if entry["key"] in entries:
            parser.error(f"duplicate review entry {entry['key']}")
        if entry["outcome"] not in INDEXABLE | {"reject"}:
            parser.error(f"{entry['key']}: unknown outcome {entry['outcome']}")
        entries[entry["key"]] = entry
    review_date = datetime.now(timezone.utc).date().isoformat()

    documents = sorted(p for p in args.source.iterdir() if (p / "pages.jsonl").exists())
    plans, used = [], set()
    for folder in documents:
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        new_rows = []
        for row in rows:
            key = f"{row['document_id']}:p{row['pdf_page']}"
            if row["status"] == "ocr_unreviewed":
                if key not in entries:
                    parser.error(f"{key} is ocr_unreviewed but has no review entry")
                entry = entries[key]
                used.add(key)
                row = dict(row)
                row["reviewed_from_text"] = row["text"]
                if entry["outcome"] == "reject":
                    row["status"] = "garbled"
                else:
                    row["text"] = apply_corrections(row["text"], entry)
                row["human_review"] = {
                    "reviewed_by": review["reviewer"], "review_date": review_date, "outcome":
                    {"reject": "reject", "fix": "fix"}.get(entry["outcome"], "pass"),
                    "review_method": review["review_method"], "detail_outcome": entry["outcome"],
                    "notes": entry.get("notes", ""), "human_confirmation": review.get("human_confirmation")}
            new_rows.append(row)
        plans.append((folder, new_rows))
    unused = set(entries) - used
    if unused:
        parser.error(f"review entries for pages that are not ocr_unreviewed: {sorted(unused)}")

    totals = Counter()
    for folder, rows in plans:
        out_dir = args.out / folder.name
        out_dir.mkdir(parents=True)
        blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
        (out_dir / "pages.jsonl").write_bytes(blob)
        summary = json.loads((folder / "normalization.json").read_text(encoding="utf-8"))
        statuses = Counter(r["status"] for r in rows)
        totals.update(statuses)
        status_pages: dict[str, list[int]] = {}
        for r in rows:
            if r["status"] != "ok":
                status_pages.setdefault(r["status"], []).append(r["pdf_page"])
        summary.update(status_counts=dict(sorted(statuses.items())), status_pages=status_pages,
                       pages_jsonl_sha256=hashlib.sha256(blob).hexdigest(),
                       derived_from={"corpus_version": folder.parent.name,
                                     "pages_jsonl_sha256": summary["pages_jsonl_sha256"],
                                     "review_file": args.review.name},
                       created_at=datetime.now(timezone.utc).isoformat())
        (out_dir / "normalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")
    outcomes = Counter(e["outcome"] for e in entries.values())
    print(json.dumps({"documents": len(plans), "reviewed_pages": len(used), "outcomes": dict(outcomes),
                      "status_totals": dict(sorted(totals.items()))}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReviewError as exc:
        print(f"review error: {exc}", file=sys.stderr)
        sys.exit(1)
