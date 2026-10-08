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


## 2026-10-06T13:22:38+07:00 — 20261006-repo-cleanup

- Owner:root session;user asked to upload normalization work(commit f28eb5b) and remove unused git files,choosing to include superseded round files.
- Removed10tracked files:20261005-local-prep EXTRACT_TOOL proposal copy(3;adopted version is scripts/extract_pages.py+tests with rights hold),ocr_stderr.txt(empty),extraction_stderr.txt(pypdf warnings),curate_local.py,ncd-50 curate.py,collection_20261005.csv/json,docs/source_catalog_20261005.md.
- Superseded by corpus_50_candidates.csv/source_catalog_50.md(29/30 IDs;excluded covid record kept in data/by_disease/99_excluded).
- Current docs relinked to source_catalog_50;historical log entries link to commit f28eb5b where removed files remain;dated github_data_inventory_20261006.json unchanged.
- Checks:0 broken internal markdown links;manifest,orchestra,disease catalogue --check pass;tests normalize18/extract20(1skip)/fetch pass.


## 2026-10-06T13:43:00+07:00 — 20261006-processed-replacement

- Owner:root session;user asked to upload the new normalized output and remove badly processed old files.
- User chose:upload summaries only(no page text) and delete old outputs locally and in git.
- Published:data/processed/normalized-v1/<id>/normalization.json(30;no source text checked) via allowlist !normalization.json;pages.jsonl stays local/ignored.
- Removed:33tracked extraction.json(30docs+3OCR samples);local first-round pages.jsonl(30),ocr-review-v1(images/OCR text);old summaries remain in git history at commit 7c98d8e and extract_pages.py can regenerate.
- Disease catalogue builder now reads normalization.json(usable/review/empty pages);124catalogue files regenerated.
- Checks:catalogue --check,manifest,orchestra pass;tests normalize18/extract20(1skip)/fetch pass;0 broken internal links.


## 2026-10-06T13:53:57+07:00 — 20261006-permission-hold-removal

- Owner:root session;user asked to remove raw data that requires permission from GitHub.
- Verified first:no PDF/page text/image/OCR file was ever committed in git history;GitHub held only55metadata receipts(URL/hash/size/pages/outcome).
- User chose:remove receipts of the9explicit prior-permission records(Siriraj Diabetes Center) from GitHub and delete their local PDFs.
- Done:9retrieval.json untracked and ignored in data/raw/.gitignore(kept locally);9local source.pdf deleted;30local PDFs remain.
- Catalogue builder marks permission holds without receipt links or downloaded count;124files regenerated.
- Earlier commits still contain the9metadata receipts(no document content);history was not rewritten.
- Checks:catalogue --check,manifest,orchestra pass;tests pass(extract 1skip);0links unresolvable on GitHub.
- Next:re-download only after recorded permission;manifest notes still describe the earlier local copies(curator update pending).


## 2026-10-06 — 20261006-recheck-download01

- Owner:Calvin session (macOS);user asked to clone the repo, cross-check data/raw, and download documents following the download pipeline guidelines.
- Cross-check:46committed retrieval.json receipts match documents.jsonl on URL/sha256/pdf_pages;30normalization.json match source_sha256/pdf_pages;validate_manifest passes.
- Download:fetch_documents.py --local-review with verified_links.json, restricted to the30previously downloaded IDs;30network attempts,30downloaded,0hash conflicts.
- Result:30PDFs/1766pages/208.6MB;on-disk sha256, page count and byte size identical to manifest and earlier receipts, so no upstream edition changes were detected.
- Not attempted:14HTTP403 sources(no retry/bypass),2manual viewers,9Siriraj prior-permission holds.
- PDFs and run log are local-only(ignored);script-rewritten retrieval.json files were restored to the committed versions;rights/accepted status unchanged.
- Next:team member on a Thai network downloads the14blocked sources manually in a normal browser and records them as a new channel with hashes.


## 2026-10-07 — 20261007-fidelity-review

- Owner:Calvin session;user asked to check the documents the team assigned (review queue item:Thai glyphs/tables/units vs page images).
- Re-ran scripts/normalize_thai.py without OCR into local data/processed/normalized-recheck-20261006/;matches committed normalized-v1 except the11earlier OCR pages and4pages of lipid-inmu.
- Compared91sampled pages across30documents with rendered page images:11usable,14usable with fixes,5need OCR/rework.
- Critical findings:underlined ≥/≤ extracted as >/< (CKD 2565, hemodialysis manual);citation superscripts merged into values (lipid 2567, Siriraj OPD HT);NUL digits in3Siriraj lipid brochures;image-only flowcharts marked ok (DM CPG, lipid 2567).
- Report:docs/fidelity_review_20261007.md;per-page JSON stays local in data/agent_runs/20261007-fidelity-review/.
- Not human approval;rights/accepted unchanged;critical numbers need team confirmation.


## 2026-10-08T09:30:00+07:00 — 20261008-calvin-merge-normalization-v2

- Owner:root session;user asked to merge calvin-check and fix the problems its fidelity review found.
- Merged origin/calvin-check(re-download cross-check,docs/fidelity_review_20261007.md) into main;no conflicts.
- Uncommitted plus5 work from another session was stashed before the merge and restored afterwards;it stays uncommitted per that session's instruction.
- normalize_thai.py v2:underlined ≥/≤ from pdfplumber geometry(26 signs/11 pages),citation superscripts(720 runs,attached-or-group rule,raise 0.15-0.8x),image-only figure pages(45 figure_review),review_hold_pages config(13 pages from the review),dedupe_layered_text(DDC),watermark lines,run-level legacy decoding+NFC,FFFD+space SARA AM,italic SARA AA font rule,mojibake metric.
- Errors caught during this run:superscript rule first turned body numbers into superscripts(geriatric อายุ 35,80 มก./ดล.);fixed with attachment and raise bounds;mojibake metric first flagged × ÷ Ø;fixed.
- Output data/processed/normalized-v2:ok1528,ok_minor73,degraded16,garbled7,figure_review45,review_hold13,ocr_unreviewed9,empty75;0failures;v1 removed(git history 624edb7).
- Checks:every v1→v2 number change attributed;1 page more defects(real CKD booklet residue);dictionary hit99.2%→99.3%;images CKD2565 p29,anemia p57;27 tests;catalogue/manifest/orchestra pass;0 broken links.
- Not changed:manifest,rights,accepted0;NUL digits in3Siriraj leaflets remain garbled;review/data-engineering branch not merged(proposal0006 pending team decision).


## 2026-10-08T10:31:36+07:00 — 20261008-siriraj-educational-use

- Owner:root session;user decided "ตัวของ 9 เล่มศิริราชใช้เพื่อการศึกษาเท่านั้น" (9 Siriraj documents for educational use only).
- Recorded decision 0008 (conditions from proposal 0006:team-private,no redistribution,cite issuer,keep notices;not issuer permission);rights queue:9 extraction holds lifted with team_use_decision,rag_ingestion_hold unchanged.
- Re-downloaded 9 PDFs(run 20261008-siriraj-edu,9 network attempts);sha256 identical to manifest.PDFs,receipts and normalization summaries stay local(gitignore).
- Error caught:the SARA AM font rule misread the foot-care manual(PSL-Bundit-Bold leaves า unmapped;rule turned real ำ into า).Added sibling-font fill with a layout-agreement guard and a glyph-order rule;first sibling version broke INMU(ทำ→ท์า) and was guarded before the final run.
- Rebuilt normalized-v2 for 39 documents/1799 pages:ok1566,ok_minor60,degraded8,garbled5,figure_review54,review_hold13,ocr_unreviewed16,empty77;0 failures;30 earlier documents changed on 91 pages,none with more defects.
- Catalogue shows the 9 as local-only educational use without links;checks and tests pass;0 broken links.
- Next:team decides whether to send the permission request to the Siriraj Diabetes Center;human review of the 7 OCR leaflet pages.


## 2026-10-09 — 20261009-trackb-corpus-v2-to-v11

- Owner:Track B (Up2mEz) with Claude and Codex CLI as workers;branch data/corpus-normalized-v2, PR to main.
- Built corpus versions normalized-v2..v11 (68 documents/4009 pages;3749 searchable in v11): 29 documents added, 19 downloaded by hand where the issuer returned 403, Typhoon OCR of 524 flagged pages (two keys in parallel), human review of every AI-proposed OCR correction (283 + 90 pages), page tags (population, personal data, low content), booklet furniture/category cleanup. Details: docs/corpus_process_record.md, data/processed/README.md.
- Errors caught:pass_auto OCR pages had 11% wrong numbers/signs (e.g. ">126" for "≥126");raw text copies kept personal data after redaction;a looping OCR call stalled a shard (now 180 s timeout);Track A's normalization v2 changes 511/1799 pages incl. 11 pages of >=/<= signs that Track B versions do not contain (docs/corpus_process_record.md 4.16).
- Decisions needing the team:(1) Siriraj Diabetes Center rights:Track B's team_decision says permission was reported obtained (no written evidence), Track A's decision 0008 says not obtained,rag hold true — both kept in rights_review, see rights_conflict_to_resolve;(2) rag_ingestion_hold false for the 68 team-approved documents (Track B team decision);(3) integrate Track A normalize v2 into Track B versions (overlay plan in 4.16);(4) guardrail/harness choices (docs/decisions_guardrail_harness.md, all unfilled);(5) population tags as weight or filter (docs/population_tag_experiment.md).
- Not in Git:PDFs, page text, OCR output, page images, .env, reviewer exports with personal values. Secret scan of files and history:clean. accepted stays 0 (no clinical approval).
- Tests:python -m unittest discover -s tests (117+ tests, ingest env). Next:integrate Track A v2, then Track B L1 (chunker, embeddings, dense search).
