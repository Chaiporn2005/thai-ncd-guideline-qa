# Proposal 0006 — Data engineering rules และผล review รอบ 2026-10-06

- Author / actual timestamp: เพื่อนร่วมทีม (review ผ่าน Claude Code), 2026-10-06
- Workstream / run: CORPUS / review of `8044691`
- State: open
- Existing authorization / scope: งาน corpus preparation ตาม decision 0004–0005
- Requested change:
  1. รับ [data engineering rules](../../docs/data_engineering_rules.md) เป็นกติกาของสาย data
  2. แก้ข้อค้นพบใน [review](../../docs/reviews/20261006-data-engineering-review.md) R1–R12 ตามลำดับที่เสนอ
  3. บันทึก decision ของทีมเรื่องการใช้เอกสารเพื่อการศึกษา (ด้านล่าง)
  4. ระบุ curator และผู้ตรวจที่เป็นคนในทีม (แทน root agent ใน decision 0004)
  5. เปลี่ยนสถานะสกัดจากรายเล่มเป็นรายหน้า และแยก `corpus_version` ใน processed output
- Why / evidence: ดูตัวเลขใน review (0 accepted, ธง encoding เกือบทุกหน้าใน guideline หลัก,
  ยอดใช้ได้สูงสุด 30–39 จาก 55, PDF อยู่เครื่องเดียว)
- Files and owners affected:
  - `docs/data_engineering_rules.md`, `docs/reviews/` — ใหม่
  - `AGENTS.md`, `agents/extractor.md`, `agents/curator.md` — เพิ่มลิงก์ไปยัง rules (coordinator เป็น owner)
  - `CLAUDE.md` — ใหม่ ให้ Claude Code โหลด `AGENTS.md` ชุดเดียวกับ Codex
- Resources / cost delta / alternatives: ไม่มีค่าใช้จ่ายเพิ่ม; OCR/บริการภายนอกต้องมี decision แยก
- Dependencies / acceptance criteria: coordinator รับ/ปรับ/ปฏิเสธเป็น decision 0006 และ owner สาย data
  ปิด R1–R12 ตามเกณฑ์ "ถือว่าแก้แล้วเมื่อ" ใน review
- Decision link: pending

## ข้อเสนอ decision เรื่องการใช้เพื่อการศึกษา

ทีมตัดสินใช้เอกสารใน corpus รวม 9 สื่อที่ถูกพักไว้ เพื่อการศึกษาในรายวิชาเท่านั้น ภายใต้เงื่อนไข:

- repo และช่องทางแชร์ไฟล์ของทีมเป็น private เฉพาะสมาชิก
- ไม่เผยแพร่ PDF หรือข้อความเต็มต่อ และไม่ deploy เป็นบริการสาธารณะ
- demo และรายงานอ้างแหล่งที่มาทุกครั้ง
- ไม่ลบ notice ลิขสิทธิ์ และคงบันทึกใน rights queue

ข้อจำกัดที่ต้องบันทึกไว้ด้วย: นี่เป็นการตัดสินและรับความเสี่ยงของทีม ไม่ใช่การอนุญาตจากผู้จัดทำ
decision 0005 บันทึกแล้วว่าวัตถุประสงค์การศึกษาอย่างเดียวยังไม่ยุติเรื่องสิทธิเผยแพร่
และศูนย์เบาหวานศิริราชประกาศชัดว่าต้องขออนุญาตก่อน จึงเสนอให้ส่งคำขออนุญาตควบคู่
และบันทึกผลตอบกลับ ถ้าผู้จัดทำปฏิเสธให้ถอดออกจาก corpus
