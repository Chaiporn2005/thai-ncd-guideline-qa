# Local PDF extraction and triage

The coordinator adopted `scripts/extract_pages.py` after reviewing the worker proposal and synthetic tests. It performs bounded foreground processing of existing local PDFs. It does not download documents, modify the corpus manifest, approve inclusion, run retrieval, or call a paid API.

## Runtime and commands

Run from repository root in PowerShell. The current bundled runtime already has pypdf 6.10.0; reportlab 4.4.9 and Pillow are used only by synthetic tests. Poppler `pdftoppm` and Tesseract are optional local executables. The basic extraction command needs neither executable.
For a separate team environment, use `requirements-ingest.txt` for processing and
`requirements-dev.txt` for the synthetic tests; local OCR also needs Poppler/Tesseract
with Thai language data. None were installed in this run.

```powershell
$taskPython = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $taskPython 'scripts/extract_pages.py' --help
& $taskPython 'scripts/extract_pages.py' --cohort 'data/manifests/private_review_selection.csv' --manifest 'data/manifests/documents.jsonl' --raw-dir 'data/raw' --processed-dir 'data/processed' --max-documents 60 --max-pages-per-document 1000 --max-total-pages 5000
& $taskPython 'tests/test_extract_pages.py'
```

The tool reads `data/raw/<document_id>/source.pdf` and writes `data/processed/<document_id>/pages.jsonl` plus `extraction.json`. It skips records without a local PDF. A CSV supplied with `--cohort` must have a `document_id` column; it can contain extra columns and a UTF-8 BOM. Repeat `--document-id ID` to select individual records. When both selectors are supplied, their intersection is used. An explicitly empty cohort selects nothing. Unknown IDs, unsafe IDs and case-colliding manifest IDs are errors.

Optional local rendering/OCR, shown for a document ID that exists in the current manifest:

```powershell
& $taskPython 'scripts/extract_pages.py' --document-id 'dm-cpg-2566-revised-2567' --processed-dir 'data/processed/ocr-review-v1' --ocr --ocr-languages 'tha+eng' --max-render-pages-per-document 20 --max-total-render-pages 50 --dpi 150
```

This example still requires its local `source.pdf`. `--ocr` implies rendering; `--render` requests images without OCR. Only pages with triage flags are rendered/OCRed. The tool never runs either optional executable unless explicitly requested, invokes commands without a shell, and does not follow source URLs. Local executable names can be configured with `--renderer` and `--tesseract`. Each child process has a 60-second timeout. No watcher, background runner, or external OCR service is created.

## Output contract

Each JSONL row preserves its one-based **PDF page number**, including blank pages. Declared PDF page labels are separate, and printed page numbers remain `null`. Text is the unchanged string returned by `pypdf.extract_text`; OCR text is stored separately. The tool does not repair characters, normalize clinical values, join pages, infer missing numbers, or claim that reading order/tables were preserved.

Page rows record source SHA-256, text method, text/whitespace counts, image XObject references, errors, and flags for empty text, replacement characters, control characters, private-use characters, or repeated identical combining marks. Image references include nested Form XObjects to a bounded depth; inline image detection and visual layout fidelity are not established by this count. Glyph flags are heuristics and do not prove faithful Thai extraction. Empty text with no detected image can mean a blank or vector page.

`extraction.json` preserves the source record's title as UTF-8 and records the SHA-256 and byte size of the exact PDF snapshot processed, actual total PDF page count, processed page count, page-cap/truncation markers, text/empty/image/glyph totals, local render attempts/successes, OCR page count, tool configuration, creation time, and the page-JSONL hash. A non-null manifest `sha256` must match the local bytes before extraction or cache reuse; otherwise `manifest_hash_mismatch` is reported and no output is written. A null manifest hash remains unknown; the actual processed hash is still recorded. `human_approval` is `null` and `clinical_or_layout_qa_performed` is `false`.
The summary's `source_url` is the manifest URL at extraction time. For the actual HTTP
retrieval channel/resolved URL and date, use the raw `retrieval.json` and published event log.

The only extraction statuses are:

- `needs_ocr`: at least one extracted page has no non-whitespace text. Genuine blank pages still enter this conservative visual/OCR review queue.
- `encoding_issue`: no empty pages, but glyph indicators or extraction/optional-tool errors require review.
- `extracted_unreviewed`: no detected issues; faithful clinical text and layout have **not** been established.

OCR does not clear flags or raise a document to `qa_passed`. The coordinator/curator remains responsible for rights review, clinical/content review, manifest changes, and any later acceptance decision. Extracted text and images inherit the source's rights restrictions and should remain in ignored local output directories until review.

The adopted CLI also reads `data/manifests/rights_review_20261005.json` by default
(override its path with `--rights-review`). A missing/malformed queue is an input error.
It skips explicit `automated_extraction_hold` records before parsing PDF pages, even when
selected individually or present in a cache. Nine Siriraj Diabetes Center media records
currently have this hold. All other extraction in this run is private fidelity review;
it does not establish a reuse licence or RAG approval. Prefer the checked
`data/manifests/private_review_selection.csv` cohort rather than the full manifest.

Current run:30 private-review documents/1766 pages; no page truncation or document errors.
Triage:15 `needs_ocr`,12 `encoding_issue`,3 `extracted_unreviewed`.
Separate local OCR root `data/processed/ocr-review-v1` contains6 OCR samples across3 documents.
Visual checks found spacing/column-order and word/unit errors; OCR output stays separate
and unapproved. See [local preparation report](local_preparation_20261005.md).

## Bounds, caching, and errors

Defaults are 60 present-document attempts, 1000 extracted pages per document, 5000 extracted-page attempts per run, and 150 MiB per source. Optional rendering is capped at 20 page attempts per document and 50 per run with DPI 72–300. Missing files consume no document/page budget; failed present documents consume a document attempt, and work performed before failures consumes page/render budgets. Cached outputs perform no page/render work but consume a present-document slot. pypdf still reads the PDF structure to determine total page count; these page caps bound text extraction, not all structural parsing. Large/hostile PDFs may require separate resource isolation.

Each document is staged under the processed root and committed by directory rename after JSON outputs are complete. Interruptions clean up staging. Existing outputs are reused only if source hash, extraction configuration, and page-JSONL hash match. Changed hashes/settings, missing summaries, or altered JSONL are reported and preserved; the tool has no overwrite/force flag. Use a separately named processed root for a new revision or changed extraction settings. The chosen roots should have a single writer. Existing image/OCR artifact files are not independently hash-checked during cache reuse, so inspect those before relying on them.

Cache configuration includes the effective page/render caps passed to each document. If a previous run reached a global cap midway, raising that cap on a later run can produce `configuration_changed`; use a new output root for the expanded extraction. A truncated document never gets its missing pages silently appended. Check `all_pdf_pages_processed` and `page_cap_applied` in every summary.

The final stdout report is UTF-8 JSON containing per-document outcomes, actual work counts, and `network_requests: 0`, `paid_api_calls: 0`, `manifest_modified: false`. pypdf diagnostics can appear separately on stderr. Exit codes:

- `0`: selection and attempted processing completed without document errors. Missing files, triage flags, and cap truncation still need attention in the report.
- `1`: at least one document or optional processing failed. Other selected documents continue within the limits.
- `2`: invalid selection/input before processing; argparse also uses this code for invalid CLI arguments.

Representative error codes are `unsafe_document_id`, `path_escape`, `invalid_pdf`, `invalid_pdf_page`, `encrypted_pdf`, `source_size_limit`, `incomplete_existing_output`, `source_hash_changed`, `configuration_changed`, `cached_output_corrupt`, `renderer_unavailable`, `ocr_unavailable`, and `optional_tool_failed`. Passwords are never guessed, and encrypted PDFs are rejected. Raw and processed document paths are resolved and checked against their configured roots to reject traversal and symlink escape.

## Verification performed by this worker

On 2026-10-05 the synthetic test suite passed **19 tests**, with no skips, in the bundled Windows runtime. It checked blank-page numbering and unchanged clinical digits, UTF-8 Thai title preservation, image-only scans, corrupt/encrypted PDFs, unchanged cache reuse, changed-source preservation, wrong-source manifest hash detection, cache tamper detection, changed settings, path traversal/reserved IDs, symlink escape, page/byte/global budgets, empty and malformed cohorts, missing-file handling, failed render budget accounting, and cleanup on interruption. One integration test ran the installed Poppler renderer and Tesseract with English OCR on a synthetic scan, confirming OCR remains separate and unreviewed. Thai OCR accuracy and real Thai clinical PDF layout/content were not validated. No source document was retrieved or processed by this worker; network requests and paid API calls were zero.
