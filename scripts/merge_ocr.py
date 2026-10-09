"""Merge Typhoon OCR results into a new corpus version without touching the source version.

For each OCR'd page the merged row gets text_source "ocr" and status "ocr_unreviewed"; the PDF text
is kept in pre_normalization_text and the raw OCR output in ocr_text. Cleaning only removes what the
OCR model added rather than read from the page: <figure> descriptions (kept separately in
ocr_figures because they are model-written), <page_number> tags and HTML entities. Digits, units,
signs and words are never changed. Pages without an OCR result are copied unchanged.

Usage:
    python -X utf8 scripts/merge_ocr.py --source data/processed/normalized-v2 \
        --ocr-dir data/processed/ocr-typhoon-v1 --out data/processed/normalized-v3
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

FIGURE = re.compile(r"<figure>(.*?)</figure>", re.S)
PAGE_NUMBER = re.compile(r"<page_number>(.*?)</page_number>", re.S)
BLANK_LINES = re.compile(r"\n{3,}")


def clean_ocr(text: str) -> tuple[str, list[str], str | None]:
    """Return (retrieval text, model-written figure descriptions, printed page number)."""
    figures = [f.strip() for f in FIGURE.findall(text)]
    text = FIGURE.sub("", text)
    page_numbers = [p.strip() for p in PAGE_NUMBER.findall(text)]
    text = PAGE_NUMBER.sub("", text)
    text = unicodedata.normalize("NFC", html.unescape(text))
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = BLANK_LINES.sub("\n\n", text).strip()
    return text, figures, (page_numbers[0] if page_numbers else None)


def load_ocr(ocr_dir: Path) -> dict[tuple[str, int], dict]:
    results = {}
    for shard in sorted(ocr_dir.glob("shard-*.jsonl")):
        for line in shard.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                if row.get("outcome") == "ocr_done":
                    results[(row["document_id"], row["pdf_page"])] = row
    return results


def merge_document(source_dir: Path, out_dir: Path, ocr: dict) -> dict:
    rows = [json.loads(x) for x in (source_dir / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    doc_id = source_dir.name
    merged, used = [], 0
    for row in rows:
        hit = ocr.get((doc_id, row["pdf_page"]))
        if hit is not None:
            if hit["source_sha256"] != row["source_sha256"]:
                raise ValueError(f"{doc_id} p{row['pdf_page']}: OCR was run on different PDF bytes")
            text, figures, printed = clean_ocr(hit["ocr_markdown"])
            row = dict(row)
            row.update(
                pre_normalization_text=row.get("text"), pdf_text_status=row["status"], text=text,
                text_source="ocr", status="ocr_unreviewed" if text else "empty",
                ocr_text=hit["ocr_markdown"], ocr_figures=figures,
                ocr_method=f"{hit['model']} task {hit['task_type']} (typhoon-ocr {hit['typhoon_ocr_version']})",
                ocr_printed_page_hint=printed, human_review=None)
            if row.pop("needs_ocr", False):  # a reviewer sent this page for a new OCR pass; it is not excluded any more,
                row["reocr"] = {"previous_status": hit.get("normalized_status"), "previous_pdf_text_status": row["pdf_text_status"]}
                if (row.get("index_exclusion") or {}).get("reason") == "awaiting_reocr":
                    del row["index_exclusion"]  # but stays out of search until a person reviews the OCR text
            used += 1
        merged.append(row)
    out_dir.mkdir(parents=True)
    blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in merged).encode("utf-8")
    (out_dir / "pages.jsonl").write_bytes(blob)
    source_summary = json.loads((source_dir / "normalization.json").read_text(encoding="utf-8"))
    statuses = Counter(r["status"] for r in merged)
    status_pages: dict[str, list[int]] = {}
    for r in merged:
        if r["status"] != "ok":
            status_pages.setdefault(r["status"], []).append(r["pdf_page"])
    summary = dict(source_summary)
    summary.update(
        status_counts=dict(sorted(statuses.items())), status_pages=status_pages, ocr_pages=used,
        pages_jsonl_sha256=hashlib.sha256(blob).hexdigest(),
        derived_from={"corpus_version": source_dir.parent.name,
                      "pages_jsonl_sha256": source_summary["pages_jsonl_sha256"]},
        created_at=datetime.now(timezone.utc).isoformat(), human_approval=None)
    (out_dir / "normalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8", newline="\n")
    return {"document_id": doc_id, "ocr_pages_merged": used, "status_counts": summary["status_counts"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ocr-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists; corpus versions are never overwritten")
    ocr = load_ocr(args.ocr_dir)
    docs = sorted(p for p in args.source.iterdir() if (p / "pages.jsonl").exists())
    unknown = {d for d, _ in ocr} - {p.name for p in docs}
    if unknown:
        parser.error(f"OCR results for documents not in source: {sorted(unknown)}")
    results = [merge_document(d, args.out / d.name, ocr) for d in docs]
    totals = Counter()
    for r in results:
        totals.update(r["status_counts"])
    merged = sum(r["ocr_pages_merged"] for r in results)
    print(json.dumps({"documents": len(results), "ocr_pages_available": len(ocr), "ocr_pages_merged": merged,
                      "status_totals": dict(sorted(totals.items()))}, indent=2))
    return 0 if merged == len(ocr) else 1


if __name__ == "__main__":
    sys.exit(main())
