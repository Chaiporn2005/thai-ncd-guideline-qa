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
