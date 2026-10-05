# แผนประสานงาน

แผนเทคนิคและ instruction matrix ฉบับหลักคือ [root plan.md](../plan.md)
ไฟล์นี้กำหนดลำดับและเจ้าของงานร่วม ไม่คัดลอกข้อกำหนดทั้งหมดมาสร้างอีกฉบับ

| ลำดับ | สายงาน / owner role | งานถัดไป | Dependency / exit evidence |
| --- | --- | --- | --- |
| 1 | DM / scout | ตรวจฉบับและเนื้อหา candidates เบาหวานที่ยังเป็น viewer | source/content evidence + output แยก |
| 1 | HT / scout | ตรวจต้นทาง/ฉบับกับ mirror ความดัน | identity/access evidence + output แยก |
| 1 | LIPID / scout | ตรวจฉบับ lipid และความสัมพันธ์ alternate URLs | edition evidence + output แยก |
| 2 | CORPUS / curator | dedup, rights review, คิว extract/QA/human review | 3 สายค้นส่งผล; accepted gates + validator |
| 3 | RAG / rag_engineer | CPU dense baseline แล้ว hybrid variant | accepted corpus, chunking policy, approved tool choice |
| 4 | EVAL / evaluator | gold set + >=2 course metrics + ablation | competent gold review + same corpus/test set + variants |
| 5 | Coordinator + ทีม | demo, slides, failure analysis, AI Audit | measured results และ course deliverables |

Verifier, extractor และ QA reviewer เป็น roles ที่สลับเข้ามาตาม dependency ของ CORPUS
CKD ยังเป็น optional/requires_scope_expansion; ไม่ dispatch เป็น core เพื่อเติมยอดเอกสาร
ทีมต้องยืนยันความหมาย corpus equivalent หาก source documents ไม่ถึง 50

## Dispatch contract

ทุก assignment ระบุ `workstream`, `run_id`, `owner/session`, `scope`, `role_prompt`,
`limits`, `output_path`, `dependencies`, `done_when`, `resource_claim`
ค้นคู่ขนานได้ไม่เกิน 3 workers นอกเหนือจาก coordinator และลดลงได้ตามทรัพยากรจริง
pipeline นี้ไม่บังคับว่าทั้ง 6 สายต้องมี agent รันพร้อมกัน

## Freeze

Deadline/freeze date: ยังไม่ทราบ; ใช้ Week 15 ตาม instruction จนทีมกำหนดวันจริง
ก่อน freeze เก็บ commit, corpus version, configs, คำสั่ง reproduce และ saved metrics

## Current collection assignment — 2026-10-05

ผู้ใช้ขอเอกสารเพิ่มโรคละ 10 ชิ้น; รอบ `20261005-ncd-plus10` มุ่ง 30 new distinct works
ใน DM/HT/LIPID ไม่ซ้ำ seeds เดิม ไม่รับรองว่าแต่ละชิ้นเป็น clinical guideline
ตรวจชนิด/ผู้จัดทำ/ฉบับ/เนื้อหาที่เข้าถึงได้ก่อน curator รวม metadata และ source catalog
Claim per stream ลงทะเบียนใน RESOURCES; ไม่เปลี่ยน CKD เป็น core
