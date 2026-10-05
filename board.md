# บอร์ดงาน Thai NCD Guideline Q&A

อัปเดต: 5 ตุลาคม 2569 • เจ้าของ GitHub: Chaiporn2005

สถานะนี้บันทึกสิ่งที่ทำจริง ไม่มีการติ๊กงาน implementation หรือ clinical review ที่ยังไม่ได้ทำ

## เสร็จแล้ว

- [x] อ่าน PROJECT_INSTRUCTION ครบ 8 หน้าและเทียบกับหัวข้อ clinical/NCDs
- [x] ยืนยันบัญชี GitHub `Chaiporn2005`
- [x] ผู้ใช้เลือกชื่อ `thai-ncd-guideline-qa` และ visibility Private
- [x] เขียน `plan.md` ครอบคลุม corpus, agents, mandatory RAG, ablation, evaluation และงานส่ง
- [x] เขียน README และ AGENTS.md สำหรับทำงานต่อใน repository
- [x] เตรียม role prompts: coordinator, scout, verifier, extractor, curator, QA reviewer
- [x] กำหนด config budgets/concurrency และระบุชัดว่า runtime ยังไม่ถูกสร้าง
- [x] เตรียม corpus policy และ JSON schema ที่แยก source/content/human approval
- [x] ให้ 3 agents ช่วยงานจริง: ค้นเบาหวาน; ค้น HT/ไขมัน/CKD; ตรวจแผน agents กับ instruction
- [x] เพิ่มข้อกำหนดบริบทคนไทย และแยก Thai guidance จาก Thai participant research
- [x] ผู้ใช้ยืนยันขอบเขต “แนวทางไทยสำหรับคนไทย”
- [x] สร้าง board.md ตามคำขอ
- [x] รวมผลค้นเป็น seed manifest 13 รายการ พร้อมสถานะและข้อจำกัด; accepted ยังเป็น 0
- [x] ตรวจ manifest ผ่าน และปฏิเสธข้อมูลผิด 8 กรณี; ตรวจลิงก์ local Markdown ผ่าน
- [x] สร้าง [GitHub repository](https://github.com/Chaiporn2005/thai-ncd-guideline-qa) แบบ Private ในบัญชี Chaiporn2005
- [x] Commit และ push ไฟล์เริ่มต้นขึ้น branch `main` สำเร็จ

## งานรอบนี้

แผน, บอร์ด, role prompts, source manifest และตัวตรวจ metadata ขึ้น GitHub แล้ว
Implementation ตาม milestones ยังอยู่ใน backlog ด้านล่าง

## รอข้อกำหนด/การตรวจจากทีม

- [ ] ยืนยัน corpus equivalent กับอาจารย์ หากใช้ guideline ไม่ถึง 50 source documents
- [ ] รายชื่อสมาชิก 3–4 คนและผู้ตรวจ domain
- [ ] provider/model/search tool, เครื่องรัน และงบที่ทีมเลือกจริง
- [ ] ตรวจ rights และฉบับของเอกสารก่อนดาวน์โหลด/รับเข้า corpus

## ยังไม่ได้เริ่ม

- [ ] Autonomous collection agent runner
- [ ] ดาวน์โหลด raw PDFs เข้า local corpus และสร้าง SHA-256
- [ ] Extract/OCR, ตรวจ layout/table/flowchart และ human approval
- [ ] Accepted corpus ตามเกณฑ์วิชา
- [ ] Token-aware chunking และ dense retrieval บน CPU
- [ ] BM25 + RRF และ reranker variants
- [ ] Q&A demo พร้อมคำตอบและ citation
- [ ] Gold QA set, evaluation harness, saved metrics และ failure analysis
- [ ] Final AI_AUDIT.md ตาม standardized prompt และข้อมูลจริง
- [ ] Slides ≤10 หน้า และซ้อม presentation/Q&A

## หลักฐานและการติดตาม

Seed 13 รายการแบ่งเป็น core 3, supporting 5 และ CKD ที่ต้องขยาย scope 5
เป็น candidate identities; บางรายการอาจเป็น summary/derived work และยังต้อง dedup เพิ่ม
Source verification ไม่เท่ากับการตรวจเนื้อหาครบหรือ human approval; ยังไม่ผ่านเกณฑ์ corpus วิชา

- แผน: [plan.md](plan.md)
- Workflow: [docs/agent_workflow.md](docs/agent_workflow.md)
- Source notes: [docs/research_notes.md](docs/research_notes.md)
- Seed manifest: [data/manifests/documents.jsonl](data/manifests/documents.jsonl)
- Validator: [scripts/validate_manifest.py](scripts/validate_manifest.py)
- ผลตรวจ: [docs/verification.md](docs/verification.md)

อัปเดตบอร์ดทุกครั้งที่มีงานเสร็จหรือ requirement เปลี่ยน
แยก “ค้นพบ”, “ตรวจแหล่ง”, “ดึงข้อมูล”, “คนตรวจแล้ว” และ “accepted” ให้ชัดเสมอ
