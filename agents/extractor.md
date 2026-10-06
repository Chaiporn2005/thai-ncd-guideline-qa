# Document extractor

Take source-verified candidates and legitimate local files only.
Record source URL, actual byte hash, size, PDF pages, method and extraction status.
Extract by page and section; preserve printed/PDF page numbers and citation spans.
Check for scanned pages, corrupted font maps, columns and reading-order failures.
Keep table headers, units, merged cells and footnotes, and source images for flowcharts.
Do not repair clinical numbers or missing branches by inference.
Compare representative pages and all gold-evidence pages with original images;
log fidelity problems, OCR requirements and repair outcomes.
Store raw/processed content locally in ignored folders; publish only metadata/report summaries.
Follow `docs/data_engineering_rules.md` (per-page status, normalization, OCR measurement) and
address open findings in `docs/reviews/` before scaling beyond the pilot.
