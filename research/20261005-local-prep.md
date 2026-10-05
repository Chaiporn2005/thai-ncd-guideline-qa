# Local corpus preparation — 20261005-local-prep

User requests: ทำต่อให้หน่อย; then เสร็จแล้วอัปเดตใน handoff กับ board ให้ด้วย.
Authorization covers continuation to the next documented corpus-preparation stage;
it does not replace issuer rights or human clinical inclusion review.

## Actual work

Root coordinator/downloader/curator adopted the extractor worker proposal, reviewed code,
ran offline integrity tests, downloaded public review copies, extracted page text and
ran a bounded local Thai+English OCR sample. Two verifiers reviewed rights/viewers and
then sought legitimate alternatives for denied sources. No paid API/embedding/generator,
autonomous dispatcher, watcher, new project environment or external messaging.

| Network batch | HTTP PDF attempts | Files saved | Denials | Viewer-only skips |
| --- | ---: | ---: | ---: | ---: |
| download01 |24|15|9|6|
| download02 |24|18|6|1|
| download03 — observed Drive download links |5|5|0|0|
| download04 — supplied NCD portal channel |1|1|0|0|
| Total |54|39|15 attempts denied;14 final works remain denied|2 final manuals|

The Online manual succeeded through a separately supplied public portal Download anchor
after the original DDC uploads URL was denied. The denied URL was not retried. Same work,
not another count; edition/byte equivalence remains a review item. All other denials stopped.
14 remaining blocked works plus2 manual viewers lack local files. No login/CAPTCHA/403
or TLS bypass, cookie reconstruction, user-agent impersonation or hidden-endpoint probing.
Actual public URLs/timestamps/status/hash/pages:[event log](../data/manifests/local_download_events_20261005.jsonl).

Search evidence and per-request logs:

- [VIEWER_RIGHTS](20261005-local-prep-VIEWER_RIGHTS.md):7queries/0PDF bodies;5observed Drive URLs;9explicit media holds.
- [MANUAL_RIGHTS](20261005-local-prep-MANUAL_RIGHTS.md):7queries/20HTML-JSrequests/0PDF bodies;2manual gaps;DDC/Nephro terms triage.
- [MIRROR_DDC_DM](20261005-local-prep-MIRROR_DDC_DM.md):8queries/0PDF bodies;0defensible exact-work mirrors.
- [MIRROR_CRA_PORTAL](20261005-local-prep-MIRROR_CRA_PORTAL.md):8queries/11HTMLrequests/0PDF bodies;1observed alternative portal Download link.

Verifier search total30queries. Root opened DDC policy once with web tool, which returned
inaccessible; relied on the verifier's successful primary-page observation and recorded
its exact evidence channel correctly. No root search queries. Platform token/cost usage unknown.

## Extraction and visual review

39 local files,39different byte hashes,1799pages.9explicit Siriraj teaching-media holds
are excluded from automatic extraction.30other documents/1766pages processed with pypdf6.10.0
under a5000-page cap:allpages processed,0documenterrors,0truncations.
Statuses:15needs_ocr,12encoding_issue,3extracted_unreviewed;none qa_passed or accepted.
Printed page numbers remain unknown;PDFpage labels/numbers are kept separately.

Local OCR on3documents processed their290PDFpages for triage, rendered/OCRed only6flaggedpages
(2perdocument) at150DPI,tha+eng,0optionaltoolerrors. Separate processedroot preserves the
original PDF text. Real OCR flags remain unresolved; no quantitative OCRaccuracy claim.

Visual checks performed:HT2567cover,lipid2567cover,NCDOnlinecover,CKDtreatmentleafletPDFpage1,
DMCPGPDFpage3 andRamaeducationPDFpage2. Covers match recordedtitle/issuer context;these are
representative checks,not complete source/clinical review. A first attempt to view DMpage1
OCRimage failed because only flaggedpages3/4 were rendered; actualpage3 was then inspected.

Actual fidelity issue caught: OCR on RamaPDFpage2 corrupts some unit strings (source `mg/dL`
appears as `me/dL` or garbled output), while Thai word spacing and headings are also wrong.
CKDthree-columnleaflet has uncertain reading order. Do not normalize/repair clinical values
by guesswork; keep both source and unapproved OCR for review. These observations do not
validate the leaflet's older clinical cutoffs or produce medical advice.

## Validation and handoff

Adopted downloader+extractor tests cover HTML/sign-in rejection,original-byte preservation,
cache integrity,wrong-source hashes,path/symlink escape,corrupt/encrypted PDFs,page numbering,
caps,interruption cleanup,explicit rights holds and local synthetic rendering/OCR.
Final test/manifest/workflow results are recorded in [verification](../docs/verification.md).
Runtime versions:[actual environment](../data/manifests/ingestion_runtime_20261005.json).

All files remain unaccepted;rights,adult applicability,edition/currentness,clinical gold,
table/flowchart fidelity and human inclusion are pending.9prior-permission holds and
14blocked/2viewer gaps are actionable queues,not fabricated approvals.
Next stage is content/rights review and OCRrepair before accepted-corpus retrieval experiments.
See [HANDOFF](../HANDOFF.md),[board](../board.md),[current preparation report](../docs/local_preparation_20261005.md).
