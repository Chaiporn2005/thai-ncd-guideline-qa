# Decision 0001 — ใช้รูปแบบการทำงานจาก kaggle-team

- Date: 2026-10-05
- Decision maker: coordinator ตามคำขอผู้ใช้ในแชตนี้
- Request: “ช่วยจัดระบบการทำงานให้เหมือนกับไฟล์นี้ได้ไหม” อ้างโฟลเดอร์ kaggle-team
- Outcome: accept_with_changes
- Authorization basis: ผู้ใช้ขอปรับ workflow; repository Private ชื่อเดิมได้รับยืนยันแล้ว
- Rationale: ใช้ protocol, orchestra, shared ownership, proposals, per-stream status,
  HANDOFF, PROGRESS และ run log เพื่อส่งงานระหว่าง agents ได้
- Adaptation: รักษาแผน NCD, Thai guidance และ course requirements;
  แยก root task board จาก append-only message board
- Exclusions from adoption: credentials, Kaggle rules/data, quota เครื่องอื่น,
  watcher และงบใช้เงินจริงจากต้นแบบไม่ได้รับมาปฏิบัติ
- Resources: ไม่เริ่ม paid API runner; $5/run ใน config ยังเป็นเพียงข้อเสนอ
- Follow-up: ตรวจไฟล์/registry และ manifest; ส่งโครงที่ตรวจแล้วขึ้น GitHub
