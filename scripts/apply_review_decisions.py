"""Apply a person's exported review decisions (from review.html) to a corpus version, writing a new version.

For each decided page:
  accept -> apply only the edits the reviewer ticked (each `old` must occur exactly once), record the review;
            OCR pages stay `ocr_unreviewed` and PDF-text pages keep their status, both indexable through
            human_review.outcome = pass/fix
  reject -> status `garbled` (never indexed), review recorded
  later / undecided -> human_review.outcome = `pending`, which keeps the page out of the index until decided
Pages not in the decisions file are copied unchanged.

Usage:
    python -X utf8 scripts/apply_review_decisions.py --source data/processed/normalized-v6 \
        --decisions ocr_review_decisions_round2.json --reviewer "<name>" --proposer "<agent/model>" \
        --out data/processed/normalized-v7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class DecisionError(ValueError):
    pass


def apply_page(row: dict, decision: dict, reviewer: str, proposer: str, date: str) -> dict:
    key = decision["key"]
    row = dict(row)
    page = decision["page"]
    review = {"reviewed_by": reviewer, "review_date": date, "review_method": "human_verified_ai_proposed",
              "proposed_by": proposer, "notes": decision.get("note", ""), "previous_review": row.get("human_review")}
    if page == "accept":
        original = row["text"]
        spans = []
        for edit in decision.get("accepted_edits", []):
            count = original.count(edit["old"])
            if count != 1:
                raise DecisionError(f"{key}: edit old text occurs {count} times: {edit['old']!r}")
            start = original.index(edit["old"])
            old, new = edit["old"], edit["new"]
            if edit.get("kind") != "remove":
                # Trim the context shared by old and new so edits that only share context do not collide.
                prefix = 0
                while prefix < min(len(old), len(new)) and old[prefix] == new[prefix]:
                    prefix += 1
                suffix = 0
                while (suffix < min(len(old), len(new)) - prefix
                       and old[len(old) - 1 - suffix] == new[len(new) - 1 - suffix]):
                    suffix += 1
                old, new, start = old[prefix:len(old) - suffix], new[prefix:len(new) - suffix], start + prefix
            spans.append((start, start + len(old), dict(edit, old=old, new=new)))
        # Locate every edit in the original text; a removal that covers smaller edits supersedes them.
        spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
        kept = []
        for span in spans:
            if kept and span[0] < kept[-1][1]:
                outer = kept[-1]
                if outer[2].get("kind") == "remove" and span[1] <= outer[1]:
                    continue
                raise DecisionError(f"{key}: overlapping edits {outer[2]['old'][:30]!r} / {span[2]['old'][:30]!r}")
            kept.append(span)
        text = original
        for start, end, edit in reversed(kept):
            text = text[:start] + edit["new"] + text[end:]
        if decision.get("accepted_edits"):
            row["text_before_review_edits"] = row["text"]
        row["text"] = text
        review.update(outcome="fix" if decision.get("accepted_edits") else "pass",
                      edits_applied=len(decision.get("accepted_edits", [])))
        if row["status"] == "garbled":
            row["status"] = "ocr_unreviewed" if row.get("text_source") == "ocr" else "degraded"
    elif page == "reject":
        row["status"] = "garbled"
        review["outcome"] = "reject"
    elif page in ("later", "undecided"):
        review["outcome"] = "pending"
    else:
        raise DecisionError(f"{key}: unknown page decision {page!r}")
    row["human_review"] = review
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--proposer", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists; corpus versions are never overwritten")
    data = json.loads(args.decisions.read_text(encoding="utf-8"))
    decisions = {d["key"]: d for d in data["decisions"]}
    date = datetime.now(timezone.utc).date().isoformat()

    seen, outcomes, plans = set(), Counter(), []
    for folder in sorted(p for p in args.source.iterdir() if (p / "pages.jsonl").exists()):
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        new_rows = []
        for row in rows:
            key = f"{row['document_id']}:p{row['pdf_page']}"
            if key in decisions:
                row = apply_page(row, decisions[key], args.reviewer, args.proposer, date)
                seen.add(key)
                outcomes[row["human_review"]["outcome"]] += 1
            new_rows.append(row)
        plans.append((folder, new_rows))
    unknown = set(decisions) - seen
    if unknown:
        raise DecisionError(f"decisions for pages not in the source: {sorted(unknown)[:5]}")

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
                                     "review_decisions": args.decisions.name},
                       created_at=datetime.now(timezone.utc).isoformat())
        (out_dir / "normalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")
    print(json.dumps({"documents": len(plans), "decided_pages": len(seen), "outcomes": dict(outcomes),
                      "status_totals": dict(sorted(totals.items()))}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DecisionError as exc:
        print(f"decision error: {exc}", file=sys.stderr)
        sys.exit(1)
