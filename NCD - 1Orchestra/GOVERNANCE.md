# Ownership และการตัดสินใจ

## ผู้รับผิดชอบ

ผู้ใช้กำหนดเป้าหมายและข้อจำกัด; คำสั่งผู้ใช้มีลำดับสูงกว่า protocol ที่ดัดแปลงจากต้นแบบ
Coordinator จัด dependency, dispatch, สรุปผลและดูแลไฟล์กลาง ไม่แทนผู้ตรวจเนื้อหาคลินิก

| ไฟล์ | ผู้แก้หลัก |
| --- | --- |
| root plan.md, board.md, HANDOFF.md, PROGRESS.md | Coordinator |
| Orchestra PLAN, GOVERNANCE, RESOURCES, status/OVERVIEW, registry | Coordinator |
| status/DM, HT, LIPID, CKD, NCD_SERVICE | Scout ที่ได้รับมอบหมายในรอบนั้น |
| status/CORPUS และ canonical manifest | Curator |
| status/RAG, status/EVAL | ผู้รับผิดชอบสายพัฒนา/ประเมิน |
| data/agent_runs/<run>/<agent>.jsonl | Agent เจ้าของ output เท่านั้น |
| BOARD, runs/LOG | ผู้ทำงาน append ผลของตน |

ไฟล์ status ตั้งต้นสร้างโดย coordinator; ผู้เขียนรอบต่อไปต้องรับ assignment ก่อน
มี writer หนึ่งรายต่อไฟล์ในขณะเดียวกัน อ่านเวอร์ชันล่าสุดก่อนเขียนและไม่ทับงานผู้อื่น
ผู้ตรวจคนเท่านั้นอนุมัติ inclusion; curator บันทึกผลอนุมัติจริงตาม schema

## ข้อเสนอและ decision

งานใน scope ที่ได้รับและไม่เพิ่มทรัพยากรทำต่อได้ ไม่ต้องส่ง proposal ทุกครั้ง
ใช้ [proposal template](proposals/TEMPLATE.md) เมื่อเปลี่ยน scope, shared plan,
allocation หรือแก้ความขัดแย้ง เช่น ต้องการเพิ่ม CKD เป็น core
Coordinator บันทึก accept / accept_with_changes / reject / needs_user_input
พร้อมเหตุผลและ evidence ใน decisions แล้วอ้างอิงกลับ proposal
การรับ proposal โดย coordinator ไม่สร้างอำนาจอนุมัติค่าใช้จ่ายใหม่
เรื่องที่ผู้ใช้ยังไม่ได้ให้ข้อมูลหรืออนุมัติจริงส่งต่อผู้ใช้; ทำงานส่วนอิสระต่อได้

## Append-only communication

BOARD ใช้ timestamp ที่มี timezone, from, to, type, workstream/run และ evidence
types: assignment, update, question, proposal, decision, blocker, handoff
ไม่แก้ข้อความเก่าเพื่อตกแต่งประวัติ หากข้อมูลผิด append correction อ้างข้อความเดิม
RESOURCES เก็บ claim/release/usage/correction เป็น events; coordinator append จากรายงาน agents
closed claims ต้องมี release; usage ที่ไม่มี meter ให้ unknown

## สิ่งที่ต้องรักษา

Thai guidance for Thai people, rights/access gates, canonical manifest single writer,
human approval, mandatory course retrieval/evaluation และ AI Audit ที่อิงเหตุการณ์จริง
ห้ามนำบัญชี, budget, GPU quota หรือกฎการแข่งขัน Kaggle มาเป็นข้อกำหนดงานนี้
การจัดระบบไฟล์ไม่เริ่ม background watcher และไม่เปลี่ยน repository visibility
