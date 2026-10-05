# แผนประสานงาน

แผนเทคนิคและ instruction matrix ฉบับหลักคือ [root plan.md](../plan.md)
ไฟล์นี้กำหนดลำดับและเจ้าของงานร่วม ไม่คัดลอกข้อกำหนดทั้งหมดมาสร้างอีกฉบับ

| ลำดับ | สายงาน / owner role | งานถัดไป | Dependency / exit evidence |
| --- | --- | --- | --- |
| 1 | DM / scout | ตรวจฉบับและเนื้อหา candidates เบาหวานที่ยังเป็น viewer | source/content evidence + output แยก |
| 1 | HT / scout | ตรวจต้นทาง/ฉบับกับ mirror ความดัน | identity/access evidence + output แยก |
| 1 | LIPID / scout | ตรวจฉบับ lipid และความสัมพันธ์ alternate URLs | edition evidence + output แยก |
| 1 optional | CKD / scout | ค้นคู่มือ CKD ไทยตามคำขอผู้ใช้ | distinct PDF/manual identities + adult scope notes |
| 1 supporting | NCD_SERVICE / scout | คู่มือ NCD Clinic Plus และคุณภาพบริการ | distinct works; ไม่เพิ่มต่างปีของงานเดิม |
| 2 | CORPUS / curator | dedup, rights review, คิว extract/QA/human review | 3 สายค้นส่งผล; accepted gates + validator |
| 3 | RAG / rag_engineer | CPU dense baseline แล้ว hybrid variant | accepted corpus, chunking policy, approved tool choice |
| 4 | EVAL / evaluator | gold set + >=2 course metrics + ablation | competent gold review + same corpus/test set + variants |
| 5 | Coordinator + ทีม | demo, slides, failure analysis, AI Audit | measured results และ course deliverables |

Verifier, extractor และ QA reviewer เป็น roles ที่สลับเข้ามาตาม dependency ของ CORPUS
CKD เป็น optional collection ที่ผู้ใช้อนุญาตแล้วตาม decision 0003; clinical inclusion ต้อง review
ทีมต้องยืนยันความหมาย corpus equivalent หาก source documents ไม่ถึง 50

## Dispatch contract

ทุก assignment ระบุ `workstream`, `run_id`, `owner/session`, `scope`, `role_prompt`,
`limits`, `output_path`, `dependencies`, `done_when`, `resource_claim`
ค้นคู่ขนานได้ไม่เกิน 3 workers นอกเหนือจาก coordinator และลดลงได้ตามทรัพยากรจริง
pipeline นี้ไม่บังคับว่าทั้ง 8 สายต้องมี agent รันพร้อมกัน

## Freeze

Deadline/freeze date: ยังไม่ทราบ; ใช้ Week 15 ตาม instruction จนทีมกำหนดวันจริง
ก่อน freeze เก็บ commit, corpus version, configs, คำสั่ง reproduce และ saved metrics

## Completed collection assignment — 20261005-ncd-plus10

ผู้ใช้ขอเอกสารเพิ่มโรคละ 10 ชิ้น; รอบ `20261005-ncd-plus10` มุ่ง 30 new distinct works
ใน DM/HT/LIPID ไม่ซ้ำ seeds เดิม ไม่รับรองว่าแต่ละชิ้นเป็น clinical guideline
ตรวจชนิด/ผู้จัดทำ/ฉบับ/เนื้อหาที่เข้าถึงได้ก่อน curator รวม metadata และ source catalog
Claim per stream ลงทะเบียนใน RESOURCES; ไม่เปลี่ยน CKD เป็น core

## Current collection assignment — 20261005-ncd-50

ผู้ใช้ขอครบ 50 เอกสาร ครอบคลุมโรคหลัก + optional CKD + NCD Clinic Plus
ใช้ CKD/NCD_SERVICE/CORE scouts รวมไม่เกิน 3 workers และ curator เป็นผู้รวม manifest
แยก JPG, possible excerpt และ historical COVID-specific guidance ออกจากยอดเป้าหมาย
PDF/คู่มือที่ตรวจตัวตนแล้วเป็น candidates; accepted corpus ยังต้องผ่าน rights/content/human review
