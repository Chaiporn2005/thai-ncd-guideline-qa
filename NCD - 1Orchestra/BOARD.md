# Agent message board — append only

ใช้ข้อความใหม่ด้านล่าง ห้าม rewrite ประวัติ; root [board.md](../board.md) ใช้ดู checklist

## 2026-10-05 — workflow-setup

- From: coordinator (current setup session)
- To: all future assigned workers
- Type: handoff
- Workstream/run: coordination / workflow-setup
- Message: ผู้ใช้ขอจัดระบบตาม kaggle-team จึงเพิ่ม protocol, orchestra, ownership,
  status และ templates รอบงาน ยังคง Thai guidance for Thai people และ instruction เดิม
- Evidence: [decision](decisions/0001-workflow-adoption.md), [HANDOFF](../HANDOFF.md)
- Runtime: ไม่มี background watcher หรือ autonomous runner ถูกเริ่มโดยการตั้งโครงนี้
- Timestamp precision: บันทึกวันที่จริง; ไม่อ้างเวลาเริ่มของงานวิจัยรอบก่อนที่ไม่มี log

<!-- Append new messages with an actual ISO timestamp including timezone. -->

## 2026-10-05T20:41:16+07:00 — 20261005-ncd-plus10 assignment

- From: coordinator
- To: DM / HT / LIPID scouts
- Type: assignment
- Scope: ผู้ใช้ขอหาเพิ่มโรคละ 10 เอกสาร; ตั้งเป้า 10 new distinct works ต่อโรคหลัก Thai adult guidance/education ไม่รวม 13 seeds เดิม
- Outputs: data/agent_runs/20261005-ncd-plus10/<stream>.jsonl และ <stream>_research.md
- Limits: 8 queries/scout/round, 10 candidates/scout; full PDF fetch budget DM 3, HT 3, LIPID 4 (รวมไม่เกิน 10)
- Done when: verified title/publisher/source URL/type/Thai applicability, dedup กับ seeds, schema-valid output และ actual query log; ไม่ accepted แทนคน
- Curator: coordinator รับ role curator ในช่วง merge หลัง scouts เสร็จ; canonical manifest single writer
- Claims: plus10-DM, plus10-HT, plus10-LIPID; existing session tools, no new paid API allocation

## 2026-10-05T20:41:16+07:00 — assigned sessions

- From: coordinator
- To: all
- Type: update
- Run: 20261005-ncd-plus10
- Session mapping: DM = /root/plus10_dm; HT = /root/plus10_ht; LIPID = /root/diabetes_sources (reassigned to LIPID)
- Curator: /root after isolated outputs return
- No fourth worker or new paid API runner started

## 2026-10-05 — PDF-only clarification and wave 2

- From: user clarification via coordinator
- To: DM / HT / LIPID scouts
- Type: assignment update
- Run: 20261005-ncd-plus10
- Requirement: ผู้ใช้เลือก “เฉพาะ PDF/คู่มือ”; ไม่รับบทความ HTML เป็นเอกสารในชุดโรคละ 10
- Change: อนุญาต wave 2 เพิ่มไม่เกิน 8 queries/scout เพื่อปรับการค้นตามข้อกำหนดใหม่; final candidates ยังไม่เกิน 10/scout
- Full PDF retrieval budgets remain DM 3 / HT 3 / LIPID 4 across both waves; verified issuer landing/link records allowed without claiming full body read
- Earlier HTML leads retained only as exclusions; no paid API runner or clinical approval

## 2026-10-05 — document verification allocation

- From: coordinator
- To: assigned scouts
- Type: decision
- Run: 20261005-ncd-plus10
- Decision: fullPDFfetch cap30, DM8/HT14/LIPID8 acrosswaves; configupdated. NoadditionalpaidAPI budget
- Evidence: [0002](decisions/0002-pdf-source-verification.md)

## 2026-10-05 — large-file verification reallocation

- From: coordinator
- To: HT / LIPID scouts
- Type: decision
- Run: 20261005-ncd-plus10
- Same total30 PDFretrieval cap; allocations adjusted DM8/HT12/LIPID10 includingfailedattempts
- Normalin-memoryPDFfetch mayverifylargefiles blockedonlybywebtoolsizecap; noaccessrestrictionbypass

## 2026-10-05 — collection curation complete

- From: coordinator/curator
- To: all / nextsession
- Type: handoff
- Run: 20261005-ncd-plus10
- Result:30newcandidateIDs DM10/HT10/LIPID10 merged;manifest43,accepted0
- Formats:27directPDFlinks,1DrivePDFviewer,2manuale-bookviewers;19retainednewPDFbodiesretrieved
- Corrections:replacedDOHformgatewithverifiedSirirajcholesterolleaflet;77provincemenusnowworkinggovernmentmanualviewer,noPDFdownloadclaim
- Claims:allreleased;noactiveworkers,allrawPDFsunsaved
- Userfollowups:PDFstorage convention data/raw/<document_id>/source.pdf;RAGsoftware usesPythonlibraries,notinstalledasprojectenvironmentyet
- Evidence:[catalogue](../docs/source_catalog_20261005.md),[researchrun](../research/20261005-ncd-plus10.md)

## 2026-10-05T21:19:57+07:00 — Git publication and RAG tool status

- From: coordinator
- To: all / next session
- Type: update
- Request: ผู้ใช้ขออัปขึ้น Git และแจ้งใน board
- Verified publication: ผลค้นและ metadata ขึ้น origin/main แล้วใน commit 19652cf
- Result: เพิ่ม DM10/HT10/LIPID10; manifest รวม 43 candidates, accepted 0
- Storage: metadata/URLs อยู่ใน Git; raw PDFs ยังไม่บันทึกใน data/raw/ และไม่ถูกอัปโหลด
- Tool check: Python 3.12.14/pypdf มีแล้ว; SentenceTransformers/PyTorch ยังไม่มีใน runtime ที่ตรวจ
- Implementation: ยังไม่มี project environment หรือ Q&A demo; ไม่ได้ติดตั้ง packages ในรอบนี้
- Evidence: [root board](../board.md), [RAG tools](../docs/rag_tools.md), [data layout](../data/README.md)

## 2026-10-05T21:36:59+07:00 — at-least-50 collection assignment

- From: coordinator
- To: CKD / NCD_SERVICE / core disease scouts
- Type: assignment
- Run: 20261005-ncd-50
- Target: >=50 eligible PDF/manual candidate works across DM/HT/LIPID/optional CKD/NCD Clinic Plus
- Strategy: seek6CKD +3NCDservice +3core newworks, allowing exclusion of JPG/uncertain derivatives/historical specialcontext records from targetcount
- Outputs: isolatedJSONL/researchlog perclaim, curator-only canonicalmanifest writer
- Claims: ncd50-CKD, ncd50-NCD, ncd50-CORE; each<=8queries/8PDFattempts/10candidates, coordinatorreserve6PDFattempts,total30
- No clinicalapproval/paidAPI/backgroundrunner
- Evidence:[decision0003](decisions/0003-collection-at-least-50.md)

## 2026-10-05T22:52:01+07:00 — curator assignment

- From: coordinator
- To: curator (root session)
- Type: assignment
- Run: 20261005-ncd-50
- Root assumes canonical manifest writer after scouts handoff; merge isolated CKD/NCD_SERVICE/CORE outputs, no additional search or PDF retrieval.
- Validate schema/IDs/URLs, target-count exclusions, CSV/cohort consistency and published evidence links; retain original records/history.
- Only approved collection-scope change: old CKD candidates become optional supporting per decision0003, not human-approved/core.

## 2026-10-05T22:55:33+07:00 — collection handoff

- From: curator / coordinator
- To: all / next session
- Type: handoff
- Run: 20261005-ncd-50
- Result:15 new works;manifest58 source_verified;selected55 PDF/manual candidate works;accepted0
- Primary buckets:DM17/HT10/LIPID13/CKD9/NCD_SERVICE6; cross-disease works counted once
- Excluded from target:JPG, unresolved CKD primary-care excerpt, historical COVID vaccination context; oldrecords preserved
- Contentaccess:selected38 full-document/11 link-only/6 viewer-only; no rawPDF persistence or humanapproval
- Usage:18queries/26PDFattempts inclfailures/repeats;allscouts/reserve released;no paidAPI
- Next:rights/currentness/contentdedup/OCR/clinical and human review beforeaccepted/RAG
- Evidence:[catalogue](../docs/source_catalog_50.md),[research](../research/20261005-ncd-50.md),[root board](../board.md)

## 2026-10-05T22:59:12+07:00 — Git publication verified

- From: coordinator
- To: user / next session
- Type: update
- Run:20261005-ncd-50
- Published source collection and metadata to origin/main:7c4f1cbc3e4a511dc4bee6c82685e48396e44ac7
- Verified git ls-remote main matches local HEAD after successful push.
- Metadata58/selected55/accepted0; no source PDFs uploaded; no active collection workers.
- Root board and handoff updated with publication evidence in follow-up documentation commit.

## 2026-10-05T23:11:45+07:00 — local preparation assignment

- From: coordinator
- To: root curator/downloader, VIEWER_RIGHTS, MANUAL_RIGHTS, EXTRACT_TOOL workers
- Type: assignment
- Run:20261005-local-prep
- User requested continuation; prepare legitimate local review copies, hashes/pages, page extraction and review queue.
- Root alone edits canonicalmanifest and downloader; verifier workers isolated JSON/logs, extractor worker isolated code proposal/tests.
- VIEWER_RIGHTS: DM/RCPT Drive identities and publisher reuse terms;8queries/0PDFbody attempts.
- MANUAL_RIGHTS:2manualviewers and DDC/Nephro publisher terms;8queries/0PDFbody attempts.
- EXTRACT_TOOL: local extraction/triage CLI proposal plus meaningful tests;0network.
- Download batch01/02:up to30 HTTPPDF attempts each;batch03 reserve30 only for resolved legitimate PDFlinks.
- No source publication, humanacceptance, paidAPI, autonomousrunner or newRAGexperiment.
- Evidence:[decision0004](decisions/0004-local-corpus-preparation.md)

## 2026-10-05T23:24:09+07:00 — legitimate alternate-source verification

- From: coordinator
- To: MIRROR_DDC_DM and MIRROR_CRA_PORTAL verifiers
- Type: assignment
- Run:20261005-local-prep-mirrors
- Rights/viewer verifiers handed off:7queries each/0PDFdownloads; their claims release now.
- Fifteen direct sources returned403 during downloads; do not retry restricted URLs, spoof headers or bypass controls.
- Seek independently published public issuer/partner mirrors or actual advertised alternative download channels; unknown editions remain held.
- Each verifier:up to8queries/0PDFbodies/max5strongalternatecandidates;isolatedoutput JSON/research logs.
- Root download04 reserve:up to20 attempts only after provenance/edition review.

## 2026-10-05T23:48:35+07:00 — local preparation handoff

- From:rootcurator/coordinator
- To:user/nextsession
- Type:handoff
- Run:20261005-local-prep
- Usersteering:requestedHANDOFF.md andboard.md update whenfinished;updatedwithactualresults/remainingqueues.
- Result:39localPDF/39uniquehashes/1799pages;30privateextractions/1766pages;6OCRsamplepages.
- Issues:9explicitpermissionholds,14remaining403works,2manualPDFgaps;OCRword/unit/spacing/columnerrorsremain.
- Manifest:58records:30extracted/28source_verified;accepted0/nohumanapproval.
- Tools:foregroundfetch/extractCLI,rights gate,25offlinecheckspassed;existingpypdf/Poppler/Tesseract,noinstall/paidAPI.
- Publication scope:code/metadata/reports only;raw/text/images/OCRstaylocalignored.
- Allworkers/claimsreleased;next:rights/edition/adultcurrentness/contentQA/humanacceptancebeforeSTCPUbaseline.
- Evidence:[HANDOFF](../HANDOFF.md),[board](../board.md),[localprep](../docs/local_preparation_20261005.md).

## 2026-10-05T23:53:49+07:00 — preparation publication verified

- From:coordinator
- To:user/nextsession
- Type:update
- Run:20261005-local-prep
- Published40code/metadata/reportfiles:9751d509d22dbf529a56033112d1c1c3ab233b82;remote mainverifiedmatcheslocalHEAD.
- No rawPDF/text/image/OCR artifacts staged;39localPDF/30privateextractionsremainignored,accepted0.
- HANDOFF/rootboard updatedwithpublicationevidence;allclaims/workersreleased.


## 2026-10-06T00:15:50+07:00 — reviewed data publication verified

- From:coordinator
- To:user/nextsession
- Type:handoff
- Run:20261006-data-github
- User authorized data upload;follow-up asked whether educational purpose is sufficient;no publisher permission evidence supplied.
- Published:55retrieval.json/33extraction.json/39reviewed historical agent files;READMEs/allowlists/inventory;149tracked data files total.
- Commit:0182f05369c65ca769a691b8cf0be663b287b2c1;push succeeded and remote main verified equal to local HEAD.
- Checks:JSON/JSONL parse,inventory/index match,source-body exclusion,manifest58/accepted0,orchestra check passed.
- Standard diff check flagged one historical blank line at EOF in LIPID_research.md;preserved historical bytes;check excluding blank-at-EOF passed.
- Held:39PDFs/33page JSONL/6OCR text/6images pending redistribution rights;2cache files excluded.
- No workers/claims started;no paid API/no new corpus acceptance.
- Evidence:[data README](../data/README.md),[inventory](../data/manifests/github_data_inventory_20261006.json),[decision0005](decisions/0005-data-github-metadata.md).


## 2026-10-06T19:20:30+07:00 — disease folder catalogue ready

- From:coordinator/curator
- To:user/nextsession
- Type:update
- Run:20261006-disease-folders
- User requested document folders identifying their topics,with changes published to GitHub.
- Created:data/by_disease with DM17/HT10/LIPID13/CKD9/NCD_SERVICE6 and excluded3;58record folders,124derived catalogue files.
- Each record:Thai title/publisher/edition/document type/source links,README/document.json and available raw/processed/OCR summary links.
- Checks:all canonical records appear once;55selected/3excluded;58JSON snapshots match canonical records;335internal links resolve;builder --check and manifest/orchestra validation passed.
- Source bodies not staged;raw/processed paths unchanged for tool compatibility;rights/clinicalacceptance unchanged.
- No workers/claims/paid API started;publication result will be recorded after verified push.
- Evidence:[catalogue](../data/by_disease/README.md),[decision0006](decisions/0006-disease-folder-catalogue.md).


## 2026-10-06T19:21:06+07:00 — disease catalogue publication verified

- From:coordinator
- To:user/nextsession
- Type:handoff
- Run:20261006-disease-folders
- Published:134files including124derived catalogue files;commitfadf5b7e9db2033b202eeb58119c36e5992ad094.
- git push succeeded;remote main verified equal to local HEAD;rootboard/HANDOFF record publication evidence.
- Folder catalogue covers58records/55selected/3excluded;no PDFs/full-text/OCR added.
- No activeworkers/claims;next corpus review gates unchanged.
