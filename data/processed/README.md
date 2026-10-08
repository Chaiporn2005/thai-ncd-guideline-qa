# Normalized text summaries

ข้อความสำหรับ retrieval อยู่ที่ `normalized-v2/<document_id>/` สร้างด้วย
[normalize_thai.py](../../scripts/normalize_thai.py) จาก PDF ใน `raw/` (30 เอกสาร / 1766 หน้า)

ขึ้น GitHub เฉพาะ `normalization.json` 30 รายการ: hash ต้นทาง, จำนวนหน้า, การซ่อมฟอนต์,
จำนวนกฎที่ใช้ และสถานะรายหน้า (`ok`, `ok_minor_issues`, `degraded`, `garbled`, `figure_review`, `review_hold`,
`ocr_unreviewed`, `empty`); ควร index เฉพาะ `ok`/`ok_minor_issues` ก่อนให้คนตรวจหน้าที่เหลือ
ไม่มีข้อความเอกสารในไฟล์สรุปเหล่านี้

`pages.jsonl` (ข้อความเต็มรายหน้า) ยังอยู่เฉพาะในเครื่อง รอหลักฐานสิทธิเผยแพร่ซ้ำ
ถ้า clone ใหม่ ให้ดาวน์โหลด PDF ตามช่องทางที่มีสิทธิแล้วรันคำสั่งใน
[normalization pipeline](../../docs/normalization_pipeline.md)
สถานะเป็นเกณฑ์คัดกรองสำหรับ retrieval ไม่ใช่ clinical approval หรือ accepted corpus

`normalized-v1` (2026-10-06) ถูกแทนด้วย v2 เมื่อ 2026-10-08 หลังแก้ปัญหาจาก fidelity review
(≥/≤ ขีดเส้นใต้, เลขอ้างอิงยกกำลัง, flowchart ที่เป็นภาพ); สรุป v1 ดูได้ใน git history ที่ commit `624edb7`

ผลสกัดรอบแรก (`<document_id>/extraction.json`, `pages.jsonl` และ `ocr-review-v1/`) ถูกลบเมื่อ 2026-10-06
เพราะฟอนต์ไทยเพี้ยนจนใช้ค้นไม่ได้; สรุปเดิมยังดูได้ใน git history ที่ commit `7c98d8e`
และสร้างใหม่ได้ด้วย [extract_pages.py](../../scripts/extract_pages.py)
ดู [rights queue](../manifests/rights_review_20261005.json)
