# เอกสารแยกตามโรคและระบบบริการ

เปิดโฟลเดอร์หมวด แล้วเลือกโฟลเดอร์เอกสารเพื่อดูชื่อ/ผู้จัดทำ/ฉบับ/ประเภท/ลิงก์ต้นทางและบันทึกที่เกี่ยวข้อง
55 selected candidates แบ่งหมวดหลักหนึ่งหมวดต่อเอกสาร;อีก3รายการเก็บใน99_excluded
เอกสารข้ามโรคมี disease_tags ใน metadata และไม่นับซ้ำ

| หมวด | รายการ | ดาวน์โหลดสำเร็จในบันทึก | มีผลสกัด |
| --- | --- | --- | --- |
| [เบาหวาน](01_diabetes/README.md) | 25 | 23 | 6 |
| [ความดันโลหิตสูง](02_hypertension/README.md) | 14 | 11 | 3 |
| [ไขมันในเลือดผิดปกติ](03_dyslipidemia/README.md) | 16 | 16 | 11 |
| [โรคไตเรื้อรัง (optional)](04_ckd_optional/README.md) | 11 | 11 | 9 |
| [NCD Clinic Plus / ระบบบริการ](05_ncd_clinic_plus/README.md) | 10 | 7 | 1 |
| [ไม่นับในชุดเป้าหมาย](99_excluded/README.md) | 3 | 0 | 0 |

แต่ละโฟลเดอร์มี README.md และ document.json;เป็นสารบัญ/metadata ไม่ใช่ไฟล์PDFหรือข้อความเต็ม
raw/processed เก็บบันทึกตาม document_id เพื่อใช้กับ download/extraction pipeline
accepted0;สิทธิ/QA/human reviewยังค้าง;CKDเป็นoptional

สร้าง/อัปเดต: `python scripts/build_disease_catalogue.py`
ตรวจความตรงกับต้นทาง: `python scripts/build_disease_catalogue.py --check`
ข้อมูลหลักอยู่ที่ [canonical manifest](../manifests/documents.jsonl) และ [ชุดที่เลือก](../manifests/corpus_50_candidates.json)
[Folder index สำหรับโปรแกรม](index.json)
