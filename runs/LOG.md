# Run log

ใช้ [RUN template](../NCD%20-%200Protocol/templates/RUN.md) สำหรับรอบถัดไป
ไม่สร้าง detailed query log ย้อนหลังสำหรับงานค้นที่มีเพียงสรุปผล

## 2026-10-05 — research-seed-summary

- Owner: coordinator สรุปผล 3 agents จากรอบก่อน
- Work: diabetes_sources, cardiometabolic_sources และ agent_design_review
- Evidence: [research notes](../docs/research_notes.md), [manifest](../data/manifests/documents.jsonl)
- Result: seed 13 source_verified; accepted 0
- Detailed queries/tokens/cost/start-end times: ไม่บันทึกครบใน repo; unknown
- Clinical/extraction approval: ยังไม่ได้ทำ
- Next: ตรวจ identity/access/rights และ full content ตาม gates

## 2026-10-05 — workflow-setup

- Owner/workstream: coordinator / coordination
- Purpose: จัดระบบตามโฟลเดอร์ kaggle-team ที่ผู้ใช้อ้าง
- Inputs: local reference Protocol, Orchestra, governance, status, handoff และ run log
- Output: NCD Protocol/Orchestra, registry, HANDOFF, PROGRESS, templates และ orchestra CLI
- Tools: local file inspection/editing, Python standard library และ Git
- Agent dispatch / paid API runner: ไม่ใช้ในรอบจัดโครง
- Cost/tokens: unknown; ไม่มี provider meter สำหรับรอบนี้
- Verification results: ดู [verification](../docs/verification.md)
- Check clock sampled: 2026-10-05T20:13:50+07:00 ก่อนรัน registry negative checks
- Checks passed: workflow/local links, live status, manifest 13/accepted 0,
  registry negative cases 8 และ unstaged diff whitespace check
- Resource claim/release: none (local scaffold editing; no parallel worker reservation)
- Next: dispatch source/content verification ตาม Orchestra PLAN เมื่อเริ่มรอบค้นใหม่

## 2026-10-05 — 20261005-ncd-plus10 + curation verification

- Owner:coordinatorwithDM/HT/LIPIDscouts,thenrootcurator/verifier
- Purpose:userrequested10additionaldocumentsperdisease,clarifiedPDF/manualonly
- Tools:websearch/open/click,ordinaryurllib,pypdf/metadatahashinmemory,Git; no newpaidAPI
- Inputs:13seedrecords,officialThaiissuers,roleprompts/schema/Orchestradependencies
- Output:30newsource_verifiedcandidateIDs;canonicalmanifest43,accepted0
- Formats:27directPDFURLs,1DrivePDFviewer,2manuale-bookviewers;20patienteducation8servicemanuals2reports
- Bodyretrieved:19retainednewPDFs;8link-only3viewer-only;no rawPDFsaved/humanapproval
- Search:50actualqueries;per-rolePDFaccounting/failures in [researchrun](../research/20261005-ncd-plus10.md)
- Curation:DOHformgate replaced;Tratpotentialmirror excluded;menuofficiale-bookfoundbutdirectPDFstillunverified
- Checks:metadata43valid,cohort/CSV30IDs10pergroupconsistent,old13recordspreserved,workflowlinksvalid
- Resources:allclaimsreleased;tokens/costunknown;budgetaccountingdefinitionchangedmidrun,notuniformruntimeenforcement
- Next:rights/accessreview,legitimatePDFdownload/hash,extraction/OCR/visualQA,humaninclusionreview

## 2026-10-05 — 20261005-ncd-50

- Owner: coordinator with CKD/NCD_SERVICE/CORE scouts, then root curator
- Purpose: user requested at least50 PDF/manual sources, core diseases plus optional CKD and NCD Clinic Plus
- Inputs: 43 original records; official Thai issuers; decision0003; schema and isolated scout outputs
- Output: 15 new records (CKD6/NCD_SERVICE3/CORE6); manifest58, selected55, accepted0
- Exclusions: JPG, unresolved CKD excerpt and historical COVID vaccination-specific guide; originals preserved
- Tools: web search/open/click, ordinary public HTTP fallback for timeout, pypdf/hash in memory, Git
- Usage: 18 actual queries,26 PDF attempts (17 successes/9 failures);4 reserve attempts unused
- Interruption: account usage limit; user explicitly resumed; existing allocations continued
- New retained bodies retrieved:13;2 new official PDF links await body retrieval; no local raw PDF persistence
- Evidence: [research run](../research/20261005-ncd-50.md), [selected catalogue](../docs/source_catalog_50.md)
- Resources: collection claims released after handoff; tokens/cost unmetered; no new paid API or autonomous runner
- Next: permissions/currency/content/hash dedup, adult-section extraction/OCR, clinical and human inclusion review
