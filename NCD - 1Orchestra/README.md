# Orchestra — ประสานงานหลาย agents

ใช้รูปแบบ coordinator + สายงานจากต้นแบบ Kaggle โดยมีโครงการ NCD เดียว
DM, HT, LIPID, optional CKD และ NCD_SERVICE เป็นสายค้นข้อมูล; CORPUS รวมและตรวจ; RAG และ EVAL เป็นสายพัฒนา
หลาย logical roles ใช้ worker session เดียวต่อกันได้

อ่านตามลำดับ:

1. [GOVERNANCE](GOVERNANCE.md): ใครแก้ไฟล์ใด และข้อเสนอแบบไหนต้องตัดสินใจ
2. [PLAN](PLAN.md): ลำดับงานและ dependency
3. [RESOURCES](RESOURCES.md): ขีดจำกัด การจอง และการใช้จริง
4. [OVERVIEW](status/OVERVIEW.md): ภาพรวมสถานะ
5. [BOARD](BOARD.md): ข้อความ append-only ระหว่าง agents

[board.md](../board.md) เป็น checklist สำหรับผู้ใช้; BOARD ในโฟลเดอร์นี้เป็น message log
Registry อยู่ที่ [workstreams.json](../configs/workstreams.json)

Coordinator คือ agent ที่รับหน้าที่ประสานงานในรอบนั้น ไม่ใช่ daemon หรือ session ถาวร
ขณะตั้งโครงไม่มี worker กำลังรันและไม่มี claim ทรัพยากรที่ active
ดูสถานะด้วย `python scripts/orchestra.py status`; ตรวจโครงด้วย `python scripts/orchestra.py check`
