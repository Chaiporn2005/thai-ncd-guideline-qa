# ผลเตรียมเอกสารในเครื่อง — 2026-10-05

ผู้ใช้ขอทำต่อจากชุด55แหล่ง และให้แจ้งใน HANDOFF/board เมื่อเสร็จ
รอบนี้เตรียมสำเนาสำหรับตรวจ สกัดข้อความ และคิว review; ยังไม่มี accepted corpus หรือระบบ Q&A

| งานที่ทำจริง | ผล |
| --- | --- |
| PDF ในเครื่อง |39ไฟล์ /39 SHA-256ไม่ซ้ำ /1799หน้า |
| สกัดเพื่อ private fidelity review |30เอกสาร /1766หน้า; ไม่มี page truncation/document error |
| สถานะสกัด |15 needs_ocr,12 encoding_issue,3 extracted_unreviewed |
| OCR ไทย+อังกฤษ |6หน้าจาก3เอกสาร; outputแยกจาก PDF text; ไม่ผ่านQA |
| พัก automatic extraction ตามข้อกำหนดผู้จัดทำ |9สื่อศูนย์เบาหวานศิริราชที่มี prior-permission notice |
| ยังไม่มี local PDF |14แหล่งตอบ403 และ2คู่มือviewerที่ไม่มีPDFใช้งานได้ |
| Accepted / human approval |0 |

หลักฐาน:[รายงานรายเอกสาร CSV](../data/manifests/local_preparation_20261005.csv),
[summary+rows JSON](../data/manifests/local_preparation_20261005.json),
[rights queue](../data/manifests/rights_review_20261005.json),
[research run](../research/20261005-local-prep.md)

## ตำแหน่งไฟล์

- PDF:`E:/งาน/งาน/AI/NLPJEC/data/raw/<document_id>/source.pdf`
- Receipt:`data/raw/<document_id>/retrieval.json` — actualURL/time/hash/bytes/pages/outcome
- PDF text:`data/processed/<document_id>/pages.jsonl` และ summary:`extraction.json`
- OCR samples:`data/processed/ocr-review-v1/<document_id>/` — image/OCRแยก; ไม่ทับผลเดิม
- [private review selection](../data/manifests/private_review_selection.csv) เลือก30เอกสารสำหรับสกัด; ไม่ใช่รายชื่อaccepted

ไฟล์PDF/ข้อความ/ภาพ/OCRถูกignoreและไม่ขึ้นGitHub; code/metadata/reportขึ้นGitHub
Git clone จึงไม่มีสำเนา39PDFติดมาด้วย และบางแหล่งยังต้องเข้าถึงผ่านช่องทางผู้จัดทำที่ถูกต้อง

## สิ่งที่ตรวจและข้อจำกัด

ตรวจbytes/PDFstructure/pages/hashจริง;39ไฟล์ไม่ซ้ำแบบbyte hash ไม่ได้พิสูจน์ว่าเนื้อหาข้ามงานไม่ซ้ำ
ตรวจภาพปกHT/lipid/NCDonline และหน้าDM/CKD/Ramaตัวอย่างเพื่อยืนยันtitle/publisherและดูOCRfidelity
OCRพบคำเพี้ยน หน่วยเพี้ยน และลำดับข้อความในหลายคอลัมน์; ไม่แก้ตัวเลขหรือหน่วยโดยเดา
PDFpage numberเก็บครบรวมหน้าว่าง; printed page numberยังเป็นnull ต้องตรวจ citationหน้าเนื้อหาจริง
เครื่องหมายencoding/emptytextเป็นheuristics:บางหน้าว่างจริง ไม่ได้แปลว่าต้องOCRทุกหน้าเสมอ

ใช้ลิงก์downloadจากDriveviewerจริง5รายการและช่องDownloadของNCDpublicportalจริง1รายการ
แทนissuerHTที่เคย403ด้วยBangkokgovernmentmirrorที่ตรวจไว้ก่อนหน้า;ปกตรงtitle/ปี2567
NCDonlinePDFจากportalมี34หน้าและปกตรงtitle/DDC;byte/edition-equivalenceกับblockeduploadsPDFยังค้าง
Public downloadไม่ใช่reuse/redistribution permission;สิทธิและclinicalcurrencyต้องตรวจต่อ
ข้อมูลนี้เป็นแนวทาง/เอกสารไทย ไม่ได้ติดป้ายว่างานอ้างอิงทั้งหมดเก็บจากคนไทย

## งานถัดไป

1. ผู้ตรวจอ่านrights/edition/adult-scope queue และบันทึกหลักฐานการอนุญาต/รับเอกสารจริง
2. ตรวจ Thai glyphs,ตาราง/flowcharts,หน่วย/เงื่อนไข/ข้อยกเว้นกับภาพ;ปรับOCRและreading orderจากผลที่ตรวจ
3. จัดหาช่องทางถูกต้องสำหรับ14blockedแหล่ง/2manualviewers;ไม่เพิ่มภาพ/บท/ฉบับเก่าเพื่อเติมยอด
4. Curatorตั้งacceptedเมื่อครบgates;จากนั้นเริ่มtoken-awarechunking/STCPUbaselineและvariantที่สอง

วิธีรัน:[downloader](download_pipeline.md),[extraction/OCR](extraction_pipeline.md)
