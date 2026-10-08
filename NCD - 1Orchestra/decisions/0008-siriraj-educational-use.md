# Decision 0008 — Siriraj Diabetes Center media: educational use only

- Decision maker / actual timestamp: user (project owner), 2026-10-08; recorded by coordinator (root session)
- Proposal link: education-use part of proposal 0006 on branch `review/data-engineering-20261006`
  (the data-engineering rules in that proposal remain open)
- Outcome: accept_with_changes
- Authorization basis: user instruction on 2026-10-08: "ตัวของ 9 เล่มศิริราชใช้เพื่อการศึกษาเท่านั้น"
  (the 9 Siriraj documents are used for educational purposes only)
- Evidence / rationale: the issuer catalogue states "สื่อการสอนเป็นลิขสิทธิ์ของศูนย์เบาหวานศิริราช
  ห้ามนำไปใช้หรือดัดแปลงก่อนได้รับอนุญาต" (see `data/manifests/rights_review_20261005.json`).
  This decision is the team's own use decision and risk acceptance. It is **not** permission from the
  issuer and does not change `redistribution_approved` (false).

## Scope

Records: `dm-siriraj-know-diabetes-undated`, `dm-siriraj-hypoglycemia-leaflet-undated`,
`dm-siriraj-patient-foot-manual-undated`, `dm-siriraj-microvascular-leaflet-undated`,
`dm-siriraj-macrovascular-leaflet-undated`, `dm-siriraj-retinopathy-leaflet-undated`,
`dm-siriraj-needle-disposal-leaflet-undated`, `dm-siriraj-self-monitoring-leaflet-undated`,
`lipid-siriraj-diabetes-fat-7`.

## Conditions

- Course study within the team only; no public deployment of answers built on these documents.
- PDFs, page text, download receipts and normalization summaries stay local and ignored by git
  (consistent with the user's 2026-10-06 instruction to keep these records off GitHub).
- No redistribution of the PDF or full text; demos and reports cite the issuer each time.
- Keep copyright notices; do not present the documents as permitted for reuse.
- Automatic extraction is allowed for this local educational use; RAG ingestion still follows the normal
  gates (`rag_ingestion_hold` stays true until human inclusion review, as for every other record).
- Sending a permission request to the Siriraj Diabetes Center is recommended; if the issuer refuses, remove
  the documents and their derived files.

## Affected files / owners

- `data/manifests/rights_review_20261005.json` (9 records: extraction hold lifted with the conditions above)
- local `data/raw/<id>/`, `data/processed/normalized-v2/<id>/` (ignored)
- `scripts/build_disease_catalogue.py` and `data/by_disease/` (catalogue notes local-only educational use)

## Follow-up

Re-download the 9 PDFs (hash must match the manifest), normalize them locally, and record the run.
Team to decide whether to send the permission request and who owns it.
