"""Write a metadata-only inventory of a normalized corpus version (no page text), safe to track in Git.

A page is searchable when its status is ok/ok_minor_issues, or ocr_unreviewed/degraded with a human review of pass or
fix, and it has no `index_exclusion`. The inventory records, per document, the hashes, status and population counts,
and why pages were excluded, so a version can be compared with its parent without opening the page files.

Usage:
    python -X utf8 scripts/write_corpus_inventory.py --corpus data/processed/normalized-v8 \
        --created-by "Track B (Up2mEz): normalized-v7 + page tags ..." --out data/manifests/corpus_normalized-v8_inventory.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def searchable(row: dict) -> bool:
    review = row.get("human_review") or {}
    return not row.get("index_exclusion") and (row["status"] in ("ok", "ok_minor_issues") or (
        row["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--created-by", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    records, totals, population, exclusions = [], Counter(), Counter(), Counter()
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        summary = json.loads((folder / "normalization.json").read_text(encoding="utf-8"))
        statuses = Counter(r["status"] for r in rows)
        totals.update(statuses)
        population.update(r.get("population", "general") for r in rows if searchable(r))
        reasons = Counter((r.get("index_exclusion") or {}).get("reason") for r in rows if r.get("index_exclusion"))
        exclusions.update(reasons)
        records.append({"document_id": folder.name, "source_sha256": rows[0]["source_sha256"], "pdf_pages": len(rows),
                        "pages_jsonl_sha256": summary["pages_jsonl_sha256"], "status_counts": dict(sorted(statuses.items())),
                        "indexable_pages": sum(searchable(r) for r in rows),
                        "population_counts": dict(sorted(Counter(r.get("population", "general") for r in rows).items())),
                        "index_exclusions": dict(sorted(reasons.items()))})
    inventory = {"corpus_version": args.corpus.name, "created_by": args.created_by, "documents": len(records),
                 "pdf_pages": sum(r["pdf_pages"] for r in records), "status_totals": dict(sorted(totals.items())),
                 "documents_with_indexable_pages": sum(r["indexable_pages"] > 0 for r in records),
                 "indexable_pages": sum(r["indexable_pages"] for r in records),
                 "indexable_population_counts": dict(sorted(population.items())),
                 "index_exclusion_totals": dict(sorted(exclusions.items())), "records": records}
    args.out.write_text(json.dumps(inventory, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in inventory.items() if k != "records"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
