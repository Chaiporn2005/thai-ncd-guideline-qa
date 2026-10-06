# Progress — เหตุผลและสิ่งที่เรียนรู้

บันทึกความก้าวหน้าที่เกิดจริง; checklist อยู่ [board.md](board.md)
รายละเอียดแหล่งข้อมูล canonical อยู่ [research notes](docs/research_notes.md)

## 2026-10-05 — Research scaffold

เทียบ instruction แล้ว collection agents เป็นส่วนช่วยรวบรวม corpus;
ยังต้องทำ dense retrieval, chunking, >=2 variants, >=2 course metrics และงานส่ง
ผู้ใช้ยืนยันแนวทางไทยสำหรับคนไทย จึงไม่จำกัดให้ทุก reference ใน guideline เป็นงานศึกษาคนไทย
ได้ seed 13 รายการ แต่การตรวจ publisher ไม่ทำให้ accepted หรือได้อ่านเนื้อหาครบ

## 2026-10-05 — Workflow organization

จากรูปแบบ kaggle-team เลือกใช้ protocol กลาง + coordinator + ownership + append-only board
และ per-stream status เพื่อป้องกัน scouts ทับ manifest หรือ session ถัดไปตีความ seed เป็น corpus สำเร็จ
คง root plan/board เป็นเอกสารหลัก เพิ่ม HANDOFF และ run log สำหรับส่งงาน
งบค้น/token/API ใน config เป็น proposed limits; การตั้งโครงไม่เริ่ม runner หรือใช้ paid API

## หลักการอัปเดต

เพิ่ม entry เมื่อมีผลหรือ decision ใหม่พร้อม evidence; ไม่เติมผลทดลองย้อนหลัง
ผลเชิงตัวเลขเก็บใน run/results ที่ทำซ้ำได้ แล้วอ้างอิงจากที่นี่

## 2026-10-05 — เพิ่มข้อมูลโรคละ10

ผู้ใช้ยืนยันPDF/คู่มือ จึงตัดHTMLarticlesออกจากการนับเอกสาร
3scoutsส่งผลให้curatorรวม30newcandidateIDs:20patienteducation,8servicemanuals,2reports
manifestรวม43, accepted0;19newPDFbodiesดึงได้แต่ยังไม่ผ่านQA/rights/humanreview
พบว่าผู้จัดทำเดียวกันหรือหัวข้อคล้ายกันไม่ได้พิสูจน์ว่าเป็นคนละwork
จึงตัดTratfatleafletที่ยังเทียบกับSirirajไม่ชัด และแทนDOHform-gatedPDFด้วยSirirajcholesterolleafletที่ตรวจจริง
shortURLเมนู77จังหวัดใช้ไม่ได้ แต่พบmanualreaderของหน่วยงานรัฐบาลที่เปิดได้; คงป้ายe-bookแทนการอ้างdirectPDF
หลักฐาน: [catalogue](https://github.com/Chaiporn2005/thai-ncd-guideline-qa/blob/f28eb5b/docs/source_catalog_20261005.md), [researchrun](research/20261005-ncd-plus10.md)

## 2026-10-05 — ครบอย่างน้อย50 PDF/คู่มือ

ผู้ใช้ขอโรคหลัก + optional CKD + NCD Clinic Plus; 3scoutsค้นเพิ่ม15งาน
manifest58 source_verified records; เลือก55 provisional worksหลังกันJPG/possibleexcerpt/historicalCOVID-specificออก3
DM17/HT10/LIPID13/CKD9/NCD_SERVICE6; เอกสารข้ามโรคนับงานเดียว
accepted0,ไม่มีrawPDFsบันทึก; ยังต้อง rights/content/hash/OCR/clinical/humanreview
รอบนี้18queries/26PDFattemptsรวมfailures/repeats;ไม่มีnewpaidAPI
Registryเพิ่มCKD/NCD_SERVICEรวม8workstreams; CKDยังoptional
หลักฐาน: [catalogue ล่าสุด](docs/source_catalog_50.md), [research run](research/20261005-ncd-50.md)

## 2026-10-05 — local corpus preparation

ผู้ใช้ขอทำต่อและให้อัปเดตHANDOFF/board จึงทำpublicreviewdownload+hash/page provenance+privateextractionqueue
ดาวน์โหลด39PDF/39uniquehashes/1799หน้า;30private-review docs/1766หน้า ไม่มีtruncation/documenterror
สื่อศูนย์เบาหวานศิริราช9รายการมีexplicitpriorpermissionnotice จึงholdautomaticextractionและRAG
OCRtha+eng6หน้าตัวอย่างรันได้แต่พบคำ/หน่วย/spacing/columnorderผิด ไม่แก้ตัวเลขโดยเดาหรือclearQAflags
14แหล่งยัง403/2manualviewersไม่มีworkingPDF;ทางpublicNCDportalช่วยให้OnlinePDF1งานดึงได้
เพิ่มforegroundCLI/rights gate/metadataCSV/JSON;raw/text/imagesignore;accepted0 ไม่มีST/RAGbaseline
หลักฐาน:[ผลเตรียม](docs/local_preparation_20261005.md),[actualresearch](research/20261005-local-prep.md)
