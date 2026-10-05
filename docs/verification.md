# Verification record

Date: 2026-10-05

## Checks completed

- Seed manifest parses and satisfies the repository schema subset checked by the validator.
- 13 candidate records; core 3, supporting 5, requires scope expansion 5.
- Human-approved / accepted records: **0**.
- All local Markdown link targets exist.
- Git staged whitespace check passed; initial research scaffold committed and pushed to `main`.
- Validator rejects the following synthetic negative cases, without modifying real source records:
  1. Accepted status without actual human approval and content QA.
  2. Invalid calendar date.
  3. Non-HTTP(S) source URL.
  4. Malformed URL.
  5. Invalid SHA-256 format.
  6. Empty human reviewer identity.
  7. QA-passed status while only a viewer was accessed.
  8. Duplicate document/edition IDs.

Command:

```powershell
python scripts/validate_manifest.py
```

The targeted negative scenarios were exercised in memory through the validator's `inspect`
function. They are validation probes, not claims of actual corpus approval or clinical testing.

## Not verified

- Complete source-content/clinical accuracy, all-page extraction fidelity or download permissions.
- Source completeness and ambiguous revision/derivative identities noted in research notes.
- 50-document/equivalent course acceptance.
- Autonomous agents, RAG demo, retrieval quality, clinical gold answers or evaluation scores.

This is a research/planning scaffold; no application benchmark results are fabricated.
# Workflow organization — 2026-10-05

ปรับรูปแบบจาก local kaggle-team โดยเพิ่ม Protocol/Orchestra, ownership,
6 workstreams, proposals/decisions, HANDOFF/PROGRESS/run log และ read-only CLI
คง canonical manifest และข้อกำหนด Thai guidance/course เดิม

ตรวจบน bundled Python ใน workspace:

- `python scripts/orchestra.py check`: ผ่าน registry, required files และ local inline Markdown links
- `python scripts/orchestra.py status`: อ่าน manifest จริง 13 source_verified; accepted 0;
  core 3, supporting 5, requires_scope_expansion 5; ไม่ dispatch agents
- Registry negative checks แบบ in-memory ผ่าน 8 กรณี: duplicate IDs, dependency cycle,
  unknown dependency, path escape, missing prompt, role/prompt mismatch, shared status และ non-object registry
- `python scripts/validate_manifest.py`: ผ่าน 13 records; ไม่มี accepted record
- `git diff --check` และ `git diff --cached --check`: ผ่านทั้งก่อนและหลัง stage
- `git diff --exit-code HEAD -- data/manifests/documents.jsonl`: ผ่าน; seed manifest ไม่เปลี่ยน

ตรวจเฉพาะ file-based workflow/config/link destinations ไม่ตรวจ Markdown anchors,
remote source content, clinical accuracy, actual resource telemetry หรือ runtime enforcement
ไม่มี retrieval/evaluation experiment, paid API runner, watcher หรือ worker ใหม่ถูกรันในรอบนี้
# PDF/manual collection — 2026-10-05

- Canonicalmanifest:43source_verifiedrecords,accepted0;old13preserved plus30newcandidateIDs
- Cohort/CSV:10selectedIDsperDM/HT/LIPID,30uniqueIDs matchingnewmanifestrows
- Newformats:27directPDFURLs,1DrivePDFviewer,2manuale-bookviewers
- Newaccess:19fullPDFbodiesretrieved,8link-only,3viewer-only; noclinicalQA/humanapproval
- `scripts/validate_manifest.py`: passed43records
- `scripts/orchestra.py check`: passedregistry/requiredfiles/localinlinelinks
- In-memorycohort/CSVconsistencyand13originalrecordequalitychecks:passed
- Local`data/raw/`empty;raw/processed/indexes/agent_runsignored; no rawPDFcommit
- Scope/core/supportingcounts:core3/supporting35/requires_scope_expansion5

Actualqueries,PDFaccessfailures,form-gatereplacementandbudget-accountingcaveats:
[researchreport](../research/20261005-ncd-plus10.md)
This does not verifyallPDFbodies,rights,clinicalaccuracy,instructorcorpus-equivalence or RAGperformance.

# At-least-50 collection — 2026-10-05

- Manifest:58 source_verified records/58 provisional work IDs;accepted0.
- Selected cohort/CSV:55 unique IDs;DM17/HT10/LIPID13/CKD9/NCD_SERVICE6.
- Three excluded records plus selected55 account for all58; no multiplied cross-disease counts.
- Added15 newworks:CKD6/NCD_SERVICE3/CORE6, no duplicate IDs/titles/recorded URLs.
- Original43 records preserved semantically except5 explicit CKD optional-supporting scope/note amendments per decision0003.
- CSV values and cohort IDs match canonicalmanifest; CSV sorted in catalogue group order.
- `scripts/validate_manifest.py`:passed58 records; `scripts/orchestra.py check`:passed8-stream registry/files/local links.
- `git diff --check`:passed; no rawPDFs in local data/raw/ or staged publication.
- Access state selected55:38 full-document,11 link-only,6 viewer-only; no complete clinical/OCR/rights review.
- PDF attempts26 within amended cap30; tokens/cost unmetered; no new paid API invoked.

Evidence:[research](../research/20261005-ncd-50.md),[catalogue](source_catalog_50.md).
Metadata checks do not certify final byte/content dedup, adult applicability, clinical currency,
human acceptance, source redistribution rights or the course's accepted corpus minimum.
