# บอร์ดงาน Thai NCD Guideline Q&A

อัปเดต: 5 ตุลาคม 2569 • เจ้าของ GitHub: Chaiporn2005

สถานะนี้บันทึกสิ่งที่ทำจริง ไม่มีการติ๊กงาน implementation หรือ clinical review ที่ยังไม่ได้ทำ

## เสร็จแล้ว

- [x] อ่าน PROJECT_INSTRUCTION ครบ 8 หน้าและเทียบกับหัวข้อ clinical/NCDs
- [x] ยืนยันบัญชี GitHub `Chaiporn2005`
- [x] ผู้ใช้เลือกชื่อ `thai-ncd-guideline-qa` และ visibility Private
- [x] เขียน `plan.md` ครอบคลุม corpus, agents, mandatory RAG, ablation, evaluation และงานส่ง
- [x] เขียน README และ AGENTS.md สำหรับทำงานต่อใน repository
- [x] เตรียม role prompts: coordinator, scout, verifier, extractor, curator, QA reviewer
- [x] กำหนด config budgets/concurrency และระบุชัดว่า runtime ยังไม่ถูกสร้าง
- [x] เตรียม corpus policy และ JSON schema ที่แยก source/content/human approval
- [x] ให้ 3 agents ช่วยงานจริง: ค้นเบาหวาน; ค้น HT/ไขมัน/CKD; ตรวจแผน agents กับ instruction
- [x] เพิ่มข้อกำหนดบริบทคนไทย และแยก Thai guidance จาก Thai participant research
- [x] ผู้ใช้ยืนยันขอบเขต “แนวทางไทยสำหรับคนไทย”
- [x] สร้าง board.md ตามคำขอ
- [x] รวมผลค้นเป็น seed manifest 13 รายการ พร้อมสถานะและข้อจำกัด; accepted ยังเป็น 0
- [x] ตรวจ manifest ผ่าน และปฏิเสธข้อมูลผิด 8 กรณี; ตรวจลิงก์ local Markdown ผ่าน
- [x] สร้าง [GitHub repository](https://github.com/Chaiporn2005/thai-ncd-guideline-qa) แบบ Private ในบัญชี Chaiporn2005
- [x] Commit และ push ไฟล์เริ่มต้นขึ้น branch `main` สำเร็จ
- [x] อ่านโครง kaggle-team แล้วปรับเป็น Protocol + Orchestra สำหรับ NCD
- [x] แบ่ง 6 workstreams พร้อม ownership, dependencies และ status files
- [x] เพิ่ม HANDOFF, PROGRESS, run log และ templates สำหรับส่งต่องาน
- [x] แยก task checklist จาก append-only agent message board; เพิ่ม proposal/decision/resource ledger
- [x] เพิ่ม registry และ CLI สำหรับดูสถานะ/ตรวจ workflow โดยไม่เริ่ม agents อัตโนมัติ
- [x] ตรวจ workflow/local links ผ่าน; registry ปฏิเสธข้อมูลผิด 8 กรณี และ manifest เดิมยังผ่าน
- [x] ผู้ใช้ยืนยันเอกสารเพิ่มเฉพาะ PDF/คู่มือ
- [x] ให้3scoutsค้นเพิ่ม DM10/HT10/LIPID10; curatorรวม30 new candidate IDs ไม่ซ้ำseedIDsเดิม
- [x] เพิ่ม source catalogue, CSV/cohort IDs และ actual research/query log; manifest รวม 43 accepted 0
- [x] อัปโหลดผลค้นและ metadata รอบเพิ่มเอกสารขึ้น GitHub `main` แล้ว: commit `19652cf`
- [x] ตรวจเครื่องมือจริง: Python 3.12.14 และ pypdf มีแล้ว; SentenceTransformers/PyTorch ยังไม่มีใน runtime ที่ตรวจ
- [x] บันทึกตำแหน่งเก็บข้อมูลและแผนเครื่องมือใน [data layout](data/README.md) และ [RAG tools](docs/rag_tools.md)
- [x] ผู้ใช้ขออย่างน้อย50 PDF/คู่มือ รวม CKD optional และ NCD Clinic Plus
- [x] ใช้3scoutsค้นเพิ่ม15งาน: CKD6, NCD_SERVICE3, CORE6; รวมmanifest58 source_verified records
- [x] เลือก55 candidate worksหลังกันJPG/possible excerpt/historicalCOVID-specific guidanceออก3รายการ
- [x] เพิ่ม catalogue ล่าสุด, CSV/cohort และ actual research logs; แบ่งregistryเป็น8workstreams
- [x] ตรวจ metadata58/CSV55/workflowผ่าน และpushรอบล่าสุดขึ้นGitHubแล้ว: commit `7c4f1cb`
- [x] ทำต่อรอบlocal preparation:ดาวน์โหลด39PDF/39hashไม่ซ้ำ/1799หน้าในเครื่อง
- [x] สกัดprivate review30เอกสาร/1766หน้า;เก็บPDFpage number/labels/hashและtriage flags
- [x] ทดลองlocalOCRtha+eng6หน้าจาก3เอกสาร;outputแยก ไม่ผ่านQAและไม่ทับPDFtext
- [x] ตรวจrights/viewers/legitimatealternatives;9explicitmediaholds,14remaining403,2manualviewer gaps
- [x] เพิ่มdownload/extractCLI,rights gate,reviewCSV/JSONและอัปเดตHANDOFFตามคำขอ
- [x] ทดสอบ25กรณี/metadata58/workflowผ่าน และpushcode/metadata/reportsรอบเตรียมแล้ว:commit `9751d50`

## งานรอบนี้

ผลเตรียมล่าสุดขึ้นGitHubแล้วใน [commit9751d50](https://github.com/Chaiporn2005/thai-ncd-guideline-qa/commit/9751d509d22dbf529a56033112d1c1c3ab233b82)
ตรวจremote mainตรงกับlocalHEADหลังpush;PDF/text/images/OCRไม่อยู่ในcommit

ผลค้นล่าสุดเผยแพร่แล้วใน [commit 7c4f1cb](https://github.com/Chaiporn2005/thai-ncd-guideline-qa/commit/7c4f1cbc3e4a511dc4bee6c82685e48396e44ac7)
ตรวจ remote mainตรงกับcommitนี้หลังpushจริง; ขึ้นเฉพาะmetadata/ลิงก์/แผน/บอร์ด ไม่รวมPDFต้นฉบับ

รอบค้นล่าสุดมี **55 selected PDF/คู่มือ** ตาม [catalogue ล่าสุด](docs/source_catalog_50.md)
หมวดนับ: DM17/HT10/LIPID13/CKD9/NCD_SERVICE6; เอกสารข้ามโรคนับงานเดียว
**ผลเตรียมล่าสุด:**39PDFอยู่ในเครื่อง;30เอกสารสกัดเพื่อreviewแล้ว/1766หน้า;accepted0
พักautomaticextraction9สื่อ;14แหล่งยัง403/2manualviewersไม่มีworkingPDF
OCR6หน้าพบคำ/หน่วย/spacingเพี้ยน จึงเก็บคิวQA ไม่ใช้เป็นgoldหรือclinicalanswer
ดู [ผลรอบนี้](docs/local_preparation_20261005.md),[reviewCSV](data/manifests/local_preparation_20261005.csv),[rights queue](data/manifests/rights_review_20261005.json)
ใช้ [HANDOFF](HANDOFF.md) รับงานต่อ และ [Orchestra overview](NCD%20-%201Orchestra/status/OVERVIEW.md) ติดตามแต่ละสาย
Implementation ยังอยู่ใน backlog; scoutsจบรอบแล้ว ไม่มีworkeractive

ผลค้น, CSV และ manifest เผยแพร่ใน repository Private แล้ว ดู
[commit ผลค้น](https://github.com/Chaiporn2005/thai-ncd-guideline-qa/commit/19652cf0a06063a012382bf0cc1fcebaae6bdc19)
ตอนรอบค้นยังไม่มีrawPDFs;ตอนนี้39ไฟล์บันทึกใน `data/raw/` แล้ว แต่ยังไม่ได้อัปโหลดPDF/ข้อความ/ภาพขึ้นGitHub

เครื่องมือ RAG ใช้ Python และไลบรารี; ยังไม่มี `.venv` ของโปรเจกต์หรือระบบ Q&A ที่รันได้
งานถัดไปคือ rights/access review, ดาวน์โหลดตามสิทธิ, OCR/QA และเตรียม environment
รายละเอียด: [RAG tools](docs/rag_tools.md)

## รอข้อกำหนด/การตรวจจากทีม

- [ ] ยืนยัน corpus equivalent กับอาจารย์ หากใช้ guideline ไม่ถึง 50 source documents
- [ ] รายชื่อสมาชิก 3–4 คนและผู้ตรวจ domain
- [ ] provider/model/search tool, เครื่องรัน และงบที่ทีมเลือกจริง
- [ ] ตรวจ rights และฉบับของเอกสารก่อนดาวน์โหลด/รับเข้า corpus

## ยังต้องทำ

- [ ] Autonomous collection agent runner
- [ ] เติมlocalPDFสำหรับ16รายการที่ยังขาด ผ่านช่องทางที่ถูกต้อง
- [ ] ตรวจ/แก้OCR/layout/table/flowchart,rightsและhumanapproval;automatic extractionเสร็จเฉพาะ30reviewdocs
- [ ] Accepted corpus ตามเกณฑ์วิชา
- [ ] Token-aware chunking และ dense retrieval บน CPU
- [ ] BM25 + RRF และ reranker variants
- [ ] Q&A demo พร้อมคำตอบและ citation
- [ ] Gold QA set, evaluation harness, saved metrics และ failure analysis
- [ ] Final AI_AUDIT.md ตาม standardized prompt และข้อมูลจริง
- [ ] Slides ≤10 หน้า และซ้อม presentation/Q&A

## หลักฐานและการติดตาม

Seed13 +รอบเพิ่ม30 +รอบล่าสุด15 =58 records: core3/supporting55; accepted0
สถานะmanifestล่าสุด30extracted/28source_verified;ไม่มีqa_passed/human_approved/accepted
ชุดเป้าหมาย55กัน3รายการออก แต่ยังเก็บmetadataเดิมเพื่อรักษาประวัติ
CKDเป็นoptional collectionตามคำขอผู้ใช้; ไม่ใช่การรับทุกงานเข้า clinicalQ&A
เป็น candidate identities; ยังต้อง final content/hash dedup และrights/humanreview
Source verification ไม่เท่ากับการตรวจเนื้อหาครบหรือ human approval; ยังไม่ผ่านเกณฑ์ corpus วิชา

- แผน: [plan.md](plan.md)
- Workflow: [docs/agent_workflow.md](docs/agent_workflow.md)
- Source notes: [docs/research_notes.md](docs/research_notes.md)
- Seed manifest: [data/manifests/documents.jsonl](data/manifests/documents.jsonl)
- Validator: [scripts/validate_manifest.py](scripts/validate_manifest.py)
- ผลตรวจ: [docs/verification.md](docs/verification.md)
- Workflow protocol: [PROTOCOL](NCD%20-%200Protocol/PROTOCOL.md)
- Agent messages: [Orchestra BOARD](NCD%20-%201Orchestra/BOARD.md)
- Run log: [runs/LOG.md](runs/LOG.md)
- เอกสารใหม่โรคละ10: [source catalogue](docs/source_catalog_20261005.md)
- รายการล่าสุด55งาน: [catalogue](docs/source_catalog_50.md), [CSV](data/manifests/corpus_50_candidates.csv)
- หลักฐานการนับ/คัดออก: [cohort JSON](data/manifests/corpus_50_candidates.json), [research log](research/20261005-ncd-50.md)

อัปเดตบอร์ดทุกครั้งที่มีงานเสร็จหรือ requirement เปลี่ยน
แยก “ค้นพบ”, “ตรวจแหล่ง”, “ดึงข้อมูล”, “คนตรวจแล้ว” และ “accepted” ให้ชัดเสมอ
