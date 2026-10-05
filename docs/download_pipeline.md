# Local PDF download workflow

`scripts/fetch_documents.py` retrieves review copies from already verified public publisher
links. It does not search, change manifest status, approve rights, or publish documents.
PDF/text/image files stay under ignored local folders.

Use Python3.10+ and `pip install -r requirements-ingest.txt` in the team's environment.
This machine used the existing bundled Python3.12.14/pypdf6.10.0; no new packages or project
virtual environment were installed in this run.

```powershell
python scripts/fetch_documents.py --run-id YOUR_REGISTERED_RUN --start 0 --limit 30 --local-review
python scripts/extract_pages.py --cohort data/manifests/private_review_selection.csv
python scripts/validate_manifest.py
```

Register each run/claim in Orchestra before network work. A new run ID preserves the log;
an existing run ID is rejected. `--start`/`--limit` slice the ordered cohort; repeat
`--document-id ID` to limit a batch to particular selected works. Maximum30 attempted
downloads, request timeout30seconds,64MiB default source limit,10 starting requests/host/minute.
There are no automatic retries or alternative-source probes after a denial.

Downloadable PDF URLs come from canonical metadata. Viewer URLs are held until a verifier
observes an actual public download link. `--links PATH` accepts a curator-reviewed JSON map
of selected document IDs to those exact URLs. URL overrides are provenance decisions, not
permission or proof that two editions match. Never construct an endpoint to evade restrictions.
Keep source/edition comparison in the review queue.

The tool validates HTTP200, PDF signature/structure/page count, size and SHA-256 before saving
`data/raw/<document_id>/source.pdf`. Existing different bytes are preserved; HTML/login pages
and encrypted PDFs are held. Cached bytes must match a non-null manifest hash.
Per-document `retrieval.json` and ignored `data/agent_runs/<run_id>/download.jsonl` record
the attempted/resolved URL, actual time, outcome and byte metadata. The curator publishes
metadata-only copies in [download events](../data/manifests/local_download_events_20261005.jsonl).

Previously denied identical URLs are held on subsequent runs. A genuinely published
alternative channel requires source verification and a new recorded URL; it is not a retry
with different headers/cookies. Do not disable TLS validation, use credentials, impersonate
clients, reconstruct sessions or bypass owner restrictions.

`--local-review` identifies the purpose of a private review copy. It does not grant copyright
permission, authorize extraction of explicitly restricted media, or accept a clinical corpus.
Read [rights queue](../data/manifests/rights_review_20261005.json) and
[extraction workflow](extraction_pipeline.md) before preprocessing or RAG.

This machine's results:39 PDF files/39 different byte hashes/1799 pages;14 remaining access
restrictions and2 manuals without a working PDF. See [current preparation report](local_preparation_20261005.md).
