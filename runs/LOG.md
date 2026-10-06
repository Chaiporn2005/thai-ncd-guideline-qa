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

## 2026-10-05 — 20261005-local-prep

- Owner:rootcoordinator/downloader/curator;VIEWER_RIGHTS/MANUAL_RIGHTS verifiers then2mirrorverifiers;EXTRACT_TOOLworker
- User:continuework;updateHANDOFF/boardwhenfinished
- Downloads:4registeredbatches54attempts;39localPDFs/39hashes/1799pages;15deniedattempts,14finalworksblocked/2viewers
- Sources:5observedDrivepublicdownloadlinks;1suppliedNCDportalchannel;existingverifiedBangkokHTmirror;no403/TLS/loginbypass
- Extraction:30private-review documents/1766pages,0docerrors/0truncation;15needs_ocr/12encoding_issue/3unreviewed
- Rights:9explicitteachingmediaholds;all55RAGusependingrights/clinical/humanreview;accepted0
- OCR:3docs,290pagetriage,6flaggedpagesrendered/OCRedat150DPItha+eng;0toolerrors;fidelityissuesremain
- Visualreview:HT/lipid/NCDcovers,DMpage3,CKDleafletpage1,Ramaeducationpage2;notall-pageclinicalQA
- Tools:existingPython3.12.14/pypdf6.10.0/Poppler/Tesseract;newforegroundCLI;nonewpackage/venv/paidAPI/embedding/generator
- Search:30verifierqueries;fullPDFbodiesdownloadedbyrootonly;tokens/platformcostunknown
- Evidence:[research](../research/20261005-local-prep.md),[report](../docs/local_preparation_20261005.md),[reviewCSV](../data/manifests/local_preparation_20261005.csv)
- Next:rights/edition/adultcurrentnessreview,OCR/readingorder/unitQA,legitimateaccessgaps,actualhumanacceptancebeforeSTCPUbaseline


## 2026-10-06T00:15:50+07:00 — 20261006-data-github

- Owner:rootcoordinator;no delegated agents or background processes.
- User requested upload of data;educational-purpose follow-up did not supply redistribution licence.
- Uploaded reviewed metadata:55retrieval records/33extraction summaries/39agent output files;folder READMEs/allowlists/inventory;149tracked data files total.
- Verified publication commit0182f05369c65ca769a691b8cf0be663b287b2c1;git push succeeded;remote main equals local HEAD.
- Excluded source bodies:39PDF/33pages JSONL/6OCR text/6images;2Python caches excluded.
- Checks:JSON/JSONL parse,index matches inventory,no staged source bodies;manifest and orchestra validators pass.
- Preserved one historical extra blank EOF;ordinary diff check warned;whitespace check with blank-at-EOF excluded passed.
- Source permission/human approval/accepted0 unchanged;no paid API,extra download,extraction,clinical evaluation or index creation.
- Next:document-specific rights evidence before any source-body publication.


## 2026-10-06T19:20:30+07:00 — 20261006-disease-folders

- Owner:rootcoordinator/curator;scope:document folder organization and GitHub publication.
- Output:data/by_disease,5primary groups+99_excluded;58document folders withREADME/document.json;124generated files.
- Metadata-derived catalogue includes document title/publisher/edition/type/population/source links and retrieval/extraction/OCR summary references.
- Added deterministic builder with read-only --check;canonical manifest and source processing paths unchanged.
- Checks:58unique records/55selected/3excluded,58metadata JSON match canonical,335internal links valid;builder/manifest/orchestra checks passed.
- No rawPDF/page text/OCR image uploads,no acceptance/rights changes,no network source collection,no new paid API or workers.
- Board/HANDOFF/CORPUS/overview updated;publication evidence follows verified push.


## 2026-10-06 — 20261006-rag-design

- User:ลอง design ระบบ RAG จากภาพตัวอย่างให้เห็นภาพในโครงการนี้.
- Created docs/rag_architecture.md with ingestion/indexing, query/answer safeguards and evaluation Mermaid diagrams.
- Adapted flow for Thai NCD: multi-agent collection; permissions/content/human gates; page-grounded chunk metadata; CPU dense baseline; Thai BM25/RRF comparison; source-linked citations; clarify/abstain.
- Explicitly labeled all architecture components as design only; corpus accepted0, no index/Q&A/provider/model/gold/metrics.
- Added root README/plan/board/HANDOFF and RAG workstream pointers; decision 0007 captures choices and limits.
- No corpus/source documents changed; no user draft files staged; no agents/paid API started.


## 2026-10-06T20:16:18+07:00 — 20261006-thai-normalization

- Owner:root session for user;no delegated agents,parallel workers or paid API.
- User asked for a review of retrieval data,then to redo the data and review again.
- Review found:DM CPG 4% Thai text(digits as glyph IDs),HT CPG broken ToUnicode,CKD booklet MacRoman TIS-620,dropped SARA AM/tone marks;original flags missed some.
- Added scripts/normalize_thai.py,configs/thai_normalization.json,tests/test_normalize_thai.py,docs/normalization_pipeline.md.
- Method:in-memory font ToUnicode repair(TH Sarabun glyph order,SARA AA/AM,NIKHAHIT-as-space,first-cluster labels),deterministic Thai text rules,edge-line removal,page quality gate,opt-in local OCR for empty pages only.
- Output local-only:data/processed/normalized-v1/<id>/pages.jsonl+normalization.json;30documents/1766pages;ok1542,ok_minor116,degraded18,garbled7,ocr_unreviewed11,empty72;0failures.
- Checks:18new tests pass;existing extractor tests20 pass(1 skipped:Poppler not on PATH);per-page regression vs original 0 worse/584 improved;rendered-page comparisons DM p40,HT p30/p77,lipid p26,CKD anemia p20,CKD booklet p20,geriatric p4,stroke leaflet p2.
- Independent dictionary check(PyThaiNLP in scratch only,not a repo dependency):Thai word hit rate92.5%->99.2%.
- Decision:Tesseract Thai OCR worse than garbled PDF text on NUL-tone pages,so OCR fills only empty pages with>=50 Thai letters.
- Not changed:manifest,rights,accepted0,human/clinical approval,original pages.jsonl;no network source collection;no index/chunking.
- Next:human fidelity review of degraded/garbled/OCR pages;adult section tagging(DM CPG90/282 pages mention children/pregnancy);table/citation handling;token-aware chunking on normalized-v1.
