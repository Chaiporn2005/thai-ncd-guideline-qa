# Data layout

## เปิดเอกสารตามหมวด

เปิด [โฟลเดอร์เอกสารแยกหมวด](by_disease/README.md) เพื่อดูว่าแต่ละรายการเกี่ยวกับอะไร

| โฟลเดอร์ | หมวด | selected candidates |
| --- | --- | --- |
| [01_diabetes](by_disease/01_diabetes/README.md) | เบาหวาน | 17 |
| [02_hypertension](by_disease/02_hypertension/README.md) | ความดันโลหิตสูง | 10 |
| [03_dyslipidemia](by_disease/03_dyslipidemia/README.md) | ไขมันในเลือดผิดปกติ | 13 |
| [04_ckd_optional](by_disease/04_ckd_optional/README.md) | โรคไตเรื้อรัง — optional | 9 |
| [05_ncd_clinic_plus](by_disease/05_ncd_clinic_plus/README.md) | NCD Clinic Plus / ระบบบริการ | 6 |
| [99_excluded](by_disease/99_excluded/README.md) | ไม่นับในชุดเป้าหมาย พร้อมเหตุผล | 3 excluded |

แต่ละรายการมีโฟลเดอร์ชื่อ `document_id` พร้อม `README.md` และ `document.json`
ระบุชื่อ/ผู้จัดทำ/ฉบับ/ประเภท/ประชากรและลิงก์แหล่งต้นทาง
พร้อมลิงก์ไปบันทึกดาวน์โหลดและผลสกัดที่มีอยู่;PDFและข้อความเต็มยังอยู่เฉพาะในเครื่อง
ข้อมูลใน `by_disease/` สร้างจาก canonical manifest/cohort ไม่ใช่ manifest หลักอีกฉบับ
อัปเดตด้วย `python scripts/build_disease_catalogue.py`;ตรวจด้วย `--check`
inventoryรอบupload20261006เป็นsnapshotก่อนเพิ่มby_disease;ไม่ใช่inventoryแบบlive

## เก็บข้อมูลที่ไหน

โฟลเดอร์ข้อมูลของเครื่องนี้คือ `E:/งาน/งาน/AI/NLPJEC/data/`

| ข้อมูล | ตำแหน่งและรูปแบบที่กำหนด | ขึ้น GitHub |
| --- | --- | --- |
| PDF ต้นฉบับ/บันทึกดาวน์โหลด | `raw/<document_id>/source.pdf` และ `retrieval.json` | ขึ้นเฉพาะ55retrieval records;PDF39ไฟล์รอสิทธิ |
| ข้อความ/OCR และผลสกัด | `processed/<document_id>/` | ขึ้น33extraction summaries;ข้อความ/OCR/ภาพยังignored |
| Vector/BM25 index | `indexes/<corpus_version>/` เมื่อสร้าง retrieval | ไม่ขึ้น; ignored |
| ชื่อโรค/เอกสาร/ฉบับ/ต้นทาง/hash/สถานะ | `manifests/documents.jsonl` | ขึ้น; canonical metadata |
| รายการใหม่โรคละ10 | `manifests/collection_20261005.csv` และ cohort JSON | ขึ้น; metadata/URLs |
| ชุดล่าสุดอย่างน้อย50 | `manifests/corpus_50_candidates.csv` และ cohort JSON | ขึ้น; 55 selected candidate works |
| Local download/extraction queue | `manifests/local_preparation_20261005.csv` และ JSON | ขึ้น; counts/hash/paths/outcomes ไม่มีsource text |
| Rights review | `manifests/rights_review_20261005.json` | ขึ้น;55pending,9explicit automatic-extraction holds |
| Outputs ของ agents แต่ละรอบ | `agent_runs/<run_id>/` | ขึ้น39reviewed metadata/log/code files ตามallowlist |

ใช้ `document_id` ตาม manifest เป็นชื่อโฟลเดอร์ แยกฉบับเอกสารและตรวจ hash ก่อนใช้
เมื่อไฟล์ที่ URL เดิมเปลี่ยน ห้ามทับเวอร์ชันโดยไม่ตรวจความสัมพันธ์ฉบับ
raw path คำนวณจาก ID; schema ปัจจุบันยังไม่มี field สำหรับ path ที่ผู้ใช้กำหนดเอง

**สถานะปัจจุบัน:** metadata58/selected55;39localPDF/39hashไม่ซ้ำ/1799หน้าอยู่ใน `raw/`
30เอกสารสกัดเพื่อprivate review1766หน้าใน `processed/`;OCRsample6หน้าแยกใน `processed/ocr-review-v1/`
9สื่อพักautomaticextractionตามexplicitpermissionnotice;14แหล่ง403/2manualviewersยังไม่มีlocalPDF
Extract/OCRยังไม่ผ่านQA/humanacceptance;indexesยังไม่ได้สร้างและไม่ใช่accepted corpusพร้อมRAG
คู่มือe-book2เล่มยังไม่มีdirectPDFที่ยืนยัน; rights/OCR/humanreviewยังต้องทำก่อนaccepted

## รอบเผยแพร่ data — 2026-10-06

ผู้ใช้ขออัปโฟลเดอร์ data และระบุวัตถุประสงค์เพื่อการศึกษา
การศึกษายังไม่ใช่หลักฐานอนุญาตเผยแพร่ซ้ำรายเอกสาร จึงเผยแพร่โครงสร้างทุกหมวด
พร้อม metadata/bันทึกงานที่ตรวจแล้ว และเก็บ PDF/ข้อความเต็ม/OCR/ภาพไว้เฉพาะในเครื่อง
ไม่มีการเปลี่ยน rights status หรือ human inclusion approval

- [raw records](raw/README.md):55retrieval.json
- [processed summaries](processed/README.md):33extraction.json
- [agent outputs](agent_runs/README.md):39ไฟล์ที่ตรวจแล้ว;โค้ดรอบเก่าเป็นประวัติข้อเสนอ
- [indexes](indexes/README.md):มีREADME;ยังไม่มีindexจริง
- [inventory](manifests/github_data_inventory_20261006.json):รายการไฟล์/hash/ขนาดและเหตุผลที่ขึ้นหรือพักไว้

`.gitignore` ของแต่ละหมวดอนุญาตเฉพาะ metadata ที่กำหนด
รอบใหม่ต้องตรวจเนื้อหา/credentials/rights ก่อนเพิ่มallowlist
Git clone ยังไม่ได้ PDF หรือ extracted page text

Tracked: manifests, schema, retrieval/extraction summaries and reviewed run records.
Ignored: source PDFs, page text, OCR text/images, indexes and unreviewed agent outputs.

Source PDFs are not included. Link access does not grant redistribution permission.
Source-verified seeds are not downloaded/QA-passed/accepted by implication.
Populate actual hash/page values only after retrieving bytes.
Run `python scripts/validate_manifest.py` after edits.
