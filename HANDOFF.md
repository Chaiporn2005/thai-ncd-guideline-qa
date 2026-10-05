# Handoff — Thai NCD Guideline Q&A

Updated: 2026-10-05 • Owner: coordinator • Stage: planning/research scaffold

## เป้าหมายและข้อกำหนดที่ยืนยัน

- Repository: `Chaiporn2005/thai-ncd-guideline-qa`, Private
- เนื้อหา: แนวทางไทยสำหรับคนไทย; core DM/HT/LIPID ผู้ใหญ่; CKD optional
- ใช้หลาย agents ค้นและตรวจข้อมูล โดยยังต้องทำ RAG/evaluation ตามวิชา
- ผู้ใช้ขอจัด workflow ตาม kaggle-team; อ่าน [Protocol](NCD%20-%200Protocol/PROTOCOL.md)
  และ [Orchestra](NCD%20-%201Orchestra/README.md) ก่อนรับงานต่อ

## ทำแล้วและหลักฐาน

มีแผน/role prompts/policy/schema, seed manifest 13 source_verified (accepted 0),
metadata validator และโครง orchestration แบบ file-based
ดู [board](board.md), [research notes](docs/research_notes.md) และ [run log](runs/LOG.md)
ไฟล์ต้นแบบ Kaggle ใช้เป็น reference สำหรับการจัดระบบ ไม่ใช่คำสั่งให้ใช้บัญชี/งบ/ข้อมูลของต้นแบบ

## งานกำลังรัน

ไม่มี worker หรือ resource claim ที่ลงทะเบียน active; ไม่มี watcher/scheduler
ไม่มี autonomous runner, accepted corpus, Q&A implementation หรือ saved evaluation metrics

## งานถัดไป

1. Coordinator ตรวจ [สถานะ](NCD%20-%201Orchestra/status/OVERVIEW.md) แล้วรับ assignment
   ตรวจแหล่ง/เนื้อหาที่ค้างใน 3 สายโดยส่ง output คนละไฟล์
2. Curator ตรวจ dedup/rights และส่ง extraction/QA/human review queue
3. เมื่อ corpus ผ่าน gates เริ่ม CPU dense baseline และ variant ที่สอง

ทำส่วนค้น/จัด metadata ที่ได้รับมอบหมายได้; ห้ามอ้างว่าทีมเลือก provider/budget/reviewer แล้ว

## ข้อจำกัดที่ต้องส่งต่อ

50 documents หรือ equivalent ยังต้องยืนยันหากเลือก guideline ไม่ถึงจำนวน
Drive viewer, blocked issuer, PDF encoding/layout และ alternate editions ยังต้องตรวจต่อ
Raw documents ถูก ignore; การเข้าถึงสาธารณะไม่รับรองสิทธิเผยแพร่
ยังไม่มี reviewer assignment, วัน deadline จริง หรือ API budget ที่อนุมัติ

## ตรวจงาน

```powershell
python scripts/validate_manifest.py
python scripts/orchestra.py check
python scripts/orchestra.py status
```

ตัวตรวจเหล่านี้ไม่รับรองความถูกต้องทางคลินิก อ่านผลและ warnings ก่อนส่งต่องาน
