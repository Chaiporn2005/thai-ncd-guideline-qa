"""Import PDFs that a team member downloaded by hand in a normal browser.

Some publishers deny scripted requests (HTTP 403) but serve the same public PDF to a browser. A person
downloads each link, saves it unchanged into an inbox folder, and this script matches each file to a
selected record by the URL's file name, validates it as a PDF, stores it as data/raw/<id>/source.pdf and
writes a retrieval.json with channel "team_member_browser_download". It makes no network requests.

Usage:
    python scripts/import_manual_downloads.py --inbox data/inbox --downloaded-by <name>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_documents as fetch  # noqa: E402  (shared PDF validation and safe storage)

ROOT = Path(__file__).resolve().parents[1]


def url_file_name(url: str) -> str:
    return unquote(Path(urlsplit(url).path).name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inbox", type=Path, required=True)
    parser.add_argument("--downloaded-by", required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifests/documents.jsonl")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/raw")
    args = parser.parse_args(argv)

    records = [json.loads(x) for x in args.manifest.read_text(encoding="utf-8").splitlines() if x.strip()]
    by_name: dict[str, dict] = {}
    for record in records:
        for url in [record.get("download_url")] + list(record.get("alternate_urls") or []):
            if url and url.lower().split("?")[0].endswith(".pdf"):
                by_name.setdefault(url_file_name(url), dict(record, matched_url=url))

    results = []
    for path in sorted(p for p in args.inbox.iterdir() if p.is_file()):
        record = by_name.get(path.name) or by_name.get(unquote(path.name))
        if record is None:
            results.append({"file": path.name, "outcome": "unmatched"})
            continue
        doc_id = record["document_id"]
        try:
            meta = fetch.store_pdf(fetch.safe_path(args.raw_dir, doc_id), path.read_bytes())
        except ValueError as exc:
            results.append({"file": path.name, "document_id": doc_id, "outcome": "rejected", "error": str(exc)})
            continue
        if record.get("sha256") and record["sha256"] != meta["sha256"]:
            outcome = "downloaded_hash_conflict"
        else:
            outcome = "downloaded"
        receipt = {"document_id": doc_id, "requested_url": record["matched_url"],
                   "retrieved_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                   "imported_at": datetime.now(timezone.utc).isoformat(),
                   "channel": "team_member_browser_download", "downloaded_by": args.downloaded_by,
                   "purpose": "local_review", "reuse_permission_inferred": False, "outcome": outcome,
                   "network_attempts": 0, **meta}
        (args.raw_dir / doc_id / "retrieval.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                                              encoding="utf-8", newline="\n")
        results.append({"file": path.name, "document_id": doc_id, "outcome": outcome,
                        "pdf_pages": meta["pdf_pages"], "sha256": meta["sha256"]})
    print(json.dumps({"imported": sum(r["outcome"] == "downloaded" for r in results), "results": results},
                     ensure_ascii=False, indent=2))
    return 0 if all(r["outcome"] == "downloaded" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
