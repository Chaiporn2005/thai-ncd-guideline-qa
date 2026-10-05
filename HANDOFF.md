# Handoff — Thai NCD Guideline Q&A

Updated: 2026-10-05 • Owner: coordinator • Stage: planning/research scaffold

## เป้าหมายและข้อกำหนดที่ยืนยัน

- Repository: `Chaiporn2005/thai-ncd-guideline-qa`, Private
- เนื้อหา: แนวทางไทยสำหรับคนไทย; core DM/HT/LIPID ผู้ใหญ่; CKD optional
- ใช้หลาย agents ค้นและตรวจข้อมูล โดยยังต้องทำ RAG/evaluation ตามวิชา
- ผู้ใช้ขอจัด workflow ตาม kaggle-team; อ่าน [Protocol](NCD%20-%200Protocol/PROTOCOL.md)
  และ [Orchestra](NCD%20-%201Orchestra/README.md) ก่อนรับงานต่อ

## ทำแล้วและหลักฐาน

มีแผน/role prompts/policy/schema, manifest 58 source_verified records (accepted 0),
metadata validator และโครง orchestration แบบ file-based
ผลค้นขึ้น GitHub แล้วใน commit 19652cf; สถานะเครื่องมือและ environment อยู่ใน [RAG tools](docs/rag_tools.md)
ดู [board](board.md), [research notes](docs/research_notes.md) และ [run log](runs/LOG.md)
รอบก่อนเพิ่ม30รายการ DM10/HT10/LIPID10 ตามข้อกำหนด PDF/คู่มือ:
27 direct PDF URLs,1 Drive PDF viewer,2 manual e-books; ดู [catalogue](docs/source_catalog_20261005.md)
ดึงเนื้อหาPDFได้19รายการใหม่ แต่ไม่มีrawPDFsเก็บในrepoหรือhumanapproval
รอบล่าสุด `20261005-ncd-50` เพิ่ม15งาน: CKD6, NCD_SERVICE3 และ CORE6
เลือก55 PDF/คู่มือหลังกันJPG/possible excerpt/historicalCOVID-specific guidanceออก3รายการ
หมวดนับหนึ่งงานต่อหมวด: DM17/HT10/LIPID13/CKD9/NCD_SERVICE6
ดู [catalogue ล่าสุด](docs/source_catalog_50.md), [CSV](data/manifests/corpus_50_candidates.csv)
และ [actual queries/attempts](research/20261005-ncd-50.md)
ไฟล์ต้นแบบ Kaggle ใช้เป็น reference สำหรับการจัดระบบ ไม่ใช่คำสั่งให้ใช้บัญชี/งบ/ข้อมูลของต้นแบบ

## งานกำลังรัน

ไม่มี worker หรือ resource claim ที่ลงทะเบียน active; ไม่มี watcher/scheduler
ไม่มี autonomous runner, accepted corpus, Q&A implementation หรือ saved evaluation metrics

## งานถัดไป

1. Coordinator อ่าน [catalogue ล่าสุด](docs/source_catalog_50.md) และเลือกลำดับ rights/access review
   ของ55 selected candidates (manifest58) โดยไม่ถือว่าครบเกณฑ์วิชาหรืออ่านครบทุกไฟล์
2. Curator ตรวจ final content/hash dedup, permissions และส่ง extraction/QA/human review queue
3. เมื่อ corpus ผ่าน gates เริ่ม CPU dense baseline และ variant ที่สอง

ทำส่วนค้น/จัด metadata ที่ได้รับมอบหมายได้; ห้ามอ้างว่าทีมเลือก provider/budget/reviewer แล้ว

## ข้อจำกัดที่ต้องส่งต่อ

55 candidate works ไม่ใช่ accepted corpus; หาก finalreview เหลือไม่ถึง50 documents ต้องยืนยัน equivalent
Drive viewer, blocked issuer, PDF encoding/layout และ alternate editions ยังต้องตรวจต่อ
Raw documents ถูก ignore; การเข้าถึงสาธารณะไม่รับรองสิทธิเผยแพร่
ยังไม่มี reviewer assignment, วัน deadline จริง หรือ API budget ที่อนุมัติ
PDF/manual-only เป็นความต้องการล่าสุด; ไม่รวม HTML articles แทนเพื่อให้ครบยอด
HTHealthStationและ77provinceเมนูยังเป็นmanual viewers ไม่มีdirectPDFที่ยืนยันว่าดึงได้

## ตรวจงาน

```powershell
python scripts/validate_manifest.py
python scripts/orchestra.py check
python scripts/orchestra.py status
```

ตัวตรวจเหล่านี้ไม่รับรองความถูกต้องทางคลินิก อ่านผลและ warnings ก่อนส่งต่องาน
