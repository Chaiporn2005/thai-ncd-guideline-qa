# CORPUS status

- Owner role: curator
- Active session / last run: none / 20261006-disease-folders (catalogue complete; review pending)
- Updated: 2026-10-06
- State: local_preparation_complete_review_pending

## Evidence

[Disease folders](../../data/by_disease/README.md):58document folders,55selected/3excluded;
README/document.jsonแยก5หมวดและexcludedพร้อมต้นทาง/raw/processed links
เป็นderivedmetadata;สิทธิ/QA/clinicalacceptanceไม่เปลี่ยน;ตรวจด้วยbuild_disease_catalogue.py --check

[Manifest](../../data/manifests/documents.jsonl):58 records:30extracted/28source_verified;
core3/supporting55/accepted0; CKD optional collectionผู้ใช้อนุญาตแล้ว ไม่ใช่ clinical inclusion
เลือก55 PDF/คู่มือ ตาม [catalogue ล่าสุด](../../docs/source_catalog_50.md)
39localPDF/1799หน้า,30private-review extractions/1766หน้า;ไม่ใช่QAapproval/accepted corpus
รอบล่าสุดเพิ่ม15งาน; กันJPG/possibleexcerpt/historicalCOVID-specific guidanceออก3จากยอด
[Validator checks](../../docs/verification.md) ตรวจ metadata ไม่ใช่ clinical content

## Next / dependencies

รับผลและรวมmetadataแล้ว → finaldedup/rights → extraction → layoutQA → humanreview → acceptance
เหลือ9prior-permission automaticextractionholds,14blocked/2manualviewers
OCRsample6หน้าจาก3เอกสารยังมีword/unit/spacing errors;ไม่ใช้แทนsourcePDFหรือgold
หลักฐาน:[local prep](../../docs/local_preparation_20261005.md),[reviewCSV](../../data/manifests/local_preparation_20261005.csv)
หาผู้ตรวจและยืนยัน corpus equivalent หาก source documents ไม่ถึง 50
CKD ยังเป็น optional; การเปลี่ยน core scope ต้องมี decision จริง

## Resources

ไม่มี active claim, reviewer assignment หรือ raw corpus ที่รับครบ
