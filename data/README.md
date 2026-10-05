# Data layout

## เก็บข้อมูลที่ไหน

โฟลเดอร์ข้อมูลของเครื่องนี้คือ `E:/งาน/งาน/AI/NLPJEC/data/`

| ข้อมูล | ตำแหน่งและรูปแบบที่กำหนด | ขึ้น GitHub |
| --- | --- | --- |
| PDF ต้นฉบับ | `raw/<document_id>/source.pdf` หลังตรวจสิทธิและดาวน์โหลดจริง | ไม่ขึ้น; ignored |
| ข้อความ/OCR และ chunks | `processed/<document_id>/` เมื่อสร้าง extraction pipeline | ไม่ขึ้น; ignored |
| Vector/BM25 index | `indexes/<corpus_version>/` เมื่อสร้าง retrieval | ไม่ขึ้น; ignored |
| ชื่อโรค/เอกสาร/ฉบับ/ต้นทาง/hash/สถานะ | `manifests/documents.jsonl` | ขึ้น; canonical metadata |
| รายการใหม่โรคละ10 | `manifests/collection_20261005.csv` และ cohort JSON | ขึ้น; metadata/URLs |
| Outputs ของ agents แต่ละรอบ | `agent_runs/<run_id>/` | ไม่ขึ้น; curator publish สรุปที่ตรวจแล้ว |

ใช้ `document_id` ตาม manifest เป็นชื่อโฟลเดอร์ แยกฉบับเอกสารและตรวจ hash ก่อนใช้
เมื่อไฟล์ที่ URL เดิมเปลี่ยน ห้ามทับเวอร์ชันโดยไม่ตรวจความสัมพันธ์ฉบับ
raw path คำนวณจาก ID; schema ปัจจุบันยังไม่มี field สำหรับ path ที่ผู้ใช้กำหนดเอง

**สถานะปัจจุบัน:** metadata 43 candidatesพร้อมลิงก์; ไม่มีPDFต้นฉบับถูกบันทึกใน `raw/`
19 PDF ใหม่อ่านผ่านweb/in-memoryเพื่อยืนยันmetadataเท่านั้น ไม่ใช่ corpus ที่เก็บพร้อมใช้
โฟลเดอร์raw/processed/indexesเตรียมไว้ในเครื่อง; extraction/indexยังไม่ได้สร้าง
คู่มือe-book2เล่มยังไม่มีdirectPDFที่ยืนยัน; rights/OCR/humanreviewยังต้องทำก่อนaccepted

Tracked: source metadata (`manifests/`) and record schema (`schemas/`).
Ignored local folders: `raw/`, `processed/`, `indexes/`, `agent_runs/`.

Source PDFs are not included. Link access does not grant redistribution permission.
Source-verified seeds are not downloaded/QA-passed/accepted by implication.
Populate actual hash/page values only after retrieving bytes.
Run `python scripts/validate_manifest.py` after edits.
