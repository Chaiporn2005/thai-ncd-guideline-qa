"""Check an agent's page-by-page OCR correction proposals before a person sees them (schema and exact matches only).

For every page in the page list there must be exactly one result, in order, with a known verdict. Every proposed edit
must quote text that occurs exactly once in the page's current text, `new` must differ from `old`, a `remove` edit must
have an empty `new`, and `fixed`/`content_missing` results must carry what the verdict promises. This does not judge
whether an edit is right: that is for the reviewer, who sees the page image beside the text.

Usage:
    python -X utf8 scripts/validate_ocr_proposals.py --audit-dir data/agent_runs/20261008-codex-reocr \
        --pages pages.json --findings findings.jsonl --corpus data/processed/normalized-v9
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

VERDICTS = {"text_ok", "fixed", "content_missing", "text_invented", "unreadable", "blank_ok"}
KINDS = {"number", "sign", "unit", "drug", "word", "remove"}
RESULT_KEYS = {"key", "group", "verdict", "edits", "missing", "notes", "zoom_used"}
EDIT_KEYS = {"old", "new", "kind", "confidence", "evidence", "occurrences"}


def check(pages: list[dict], results: list[dict], texts: dict[str, str], image_root: Path) -> list[str]:
    errors = []
    if [r.get("key") for r in results] != [p["key"] for p in pages]:
        missing = sorted({p["key"] for p in pages} - {r.get("key") for r in results})
        errors.append(f"results do not match the page list in order (missing {len(missing)}: {missing[:5]})")
        return errors
    for page, row in zip(pages, results):
        key = row["key"]
        if set(row) != RESULT_KEYS:
            errors.append(f"{key}: result keys {sorted(set(row) ^ RESULT_KEYS)} differ from the contract")
            continue
        if row["verdict"] not in VERDICTS:
            errors.append(f"{key}: unknown verdict {row['verdict']!r}")
        if row["group"] != page["group"]:
            errors.append(f"{key}: group changed")
        if not (image_root / page["image"]).is_file():
            errors.append(f"{key}: image {page['image']} missing")
        text = texts[key]
        for edit in row["edits"]:
            if set(edit) != EDIT_KEYS:
                errors.append(f"{key}: edit keys differ from the contract")
                continue
            if not edit["old"] or edit["old"] == edit["new"]:
                errors.append(f"{key}: empty or unchanged edit")
            if text.count(edit["old"]) != 1 or edit["occurrences"] != 1:
                errors.append(f"{key}: old text occurs {text.count(edit['old'])} times: {edit['old'][:40]!r}")
            if edit["kind"] not in KINDS:
                errors.append(f"{key}: unknown kind {edit['kind']!r}")
            if edit["confidence"] not in {"high", "medium"} or not edit["evidence"]:
                errors.append(f"{key}: confidence/evidence missing")
            if (edit["new"] == "") != (edit["kind"] == "remove"):
                errors.append(f"{key}: remove edits must have an empty new text, and only they")
        if row["verdict"] == "content_missing" and not row["missing"]:
            errors.append(f"{key}: content_missing without a description")
        if row["verdict"] == "fixed" and (not row["edits"] or row["missing"]):
            errors.append(f"{key}: fixed must have edits and no missing content")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--findings", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", default="validation.json")
    args = parser.parse_args(argv)

    pages = json.loads((args.audit_dir / args.pages).read_text(encoding="utf-8"))
    results = [json.loads(x) for x in (args.audit_dir / args.findings).read_text(encoding="utf-8").split("\n") if x.strip()]
    texts: dict[str, str] = {}
    for doc in {p["document_id"] for p in pages}:
        for line in (args.corpus / doc / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                texts[f"{doc}:p{row['pdf_page']}"] = row["text"]
    errors = check(pages, results, texts, args.audit_dir)
    report = {"pages_expected": len(pages), "pages_with_results": len(results), "errors": errors[:50], "error_count": len(errors),
              "verdicts": dict(Counter(r.get("verdict") for r in results)),
              "edit_kinds": dict(Counter(e.get("kind") for r in results for e in r.get("edits", []))),
              "scope": "Proposal schema, page coverage and exact unique old-text matches only; not clinical or human approval."}
    (args.audit_dir / args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
