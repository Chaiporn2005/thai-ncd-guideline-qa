# Extraction review summaries

ขึ้น GitHub เฉพาะ `extraction.json` 33 รายการ: สรุป extraction 30 เอกสาร
และการทดลอง OCR 3 เอกสาร โดยมี source hash, จำนวนหน้า, config และ QA flags
ไม่มีข้อความรายหน้าในไฟล์สรุปเหล่านี้

`pages.jsonl`, `ocr/*.txt` และ `images/*.png` ยังอยู่เฉพาะในเครื่อง
รอหลักฐานสิทธิเผยแพร่ซ้ำ; OCR ยังพบคำ/หน่วย/ลำดับการอ่านผิดและยังไม่ผ่าน QA
ผลสกัดไม่ใช่ clinical approval หรือ accepted corpus

ไฟล์สรุปเป็นหลักฐานรอบ 2026-10-05; path ของเครื่องเดิมเป็น provenance
ไม่ใช่ path ที่จะมีอยู่หลัง clone โดยอัตโนมัติ
ดู [extraction pipeline](../../docs/extraction_pipeline.md) และ
[rights queue](../manifests/rights_review_20261005.json)
