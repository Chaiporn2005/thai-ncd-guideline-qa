# วิธีใช้หลาย agents รวบรวมข้อมูล

Workflow นี้เป็น file-based protocol สำหรับเครื่องมือที่รองรับ subagents
ไม่ใช่ autonomous runner ที่ติดตั้งแล้ว และไม่มี scheduled searches หรือค่าใช้จ่าย API อัตโนมัติ

เริ่มรอบจาก [HANDOFF](../HANDOFF.md) และ [Protocol](../NCD%20-%200Protocol/PROTOCOL.md)
ใช้ [Orchestra](../NCD%20-%201Orchestra/README.md) สำหรับ ownership, assignments,
resource claims, proposals และ per-stream status; root `board.md` ใช้ดูงานเสร็จ

## รอบค้นหนึ่งรอบ

1. Coordinator อ่าน handoff, Orchestra, `plan.md`, policy และ configs แล้วสร้าง run ID
   ระบุ workstream/owner/output/done criteria, ตรวจ limits ที่ได้รับจริง และบันทึก resource claim
2. Dispatch scouts ตาม scope โดยส่ง role prompt + คำค้น + budget + output path
3. Scouts ค้นอย่างอิสระ ส่งหนึ่ง JSON record ต่อหนึ่ง candidate และ actual query log
4. Source verifier ตรวจ publisher/title/edition/access โดยไม่อ้างว่า Drive viewer คือ PDF ที่อ่านแล้ว
5. Curator รวมผลเข้า manifest; resolve IDs, alternate URLs และ duplicate editions
6. รัน `python scripts/validate_manifest.py` แล้วอ่าน warnings และสรุปจำนวน
7. Extractor รับเอกสารที่ตรวจแหล่งแล้ว ดึง local content ตามสิทธิและเก็บ extraction issues
8. QA reviewer เทียบข้อความกับภาพจริง แล้วส่ง human review queue
9. Curator เปลี่ยนเป็น accepted เฉพาะรายการที่ผ่าน gates; รายงาน corpus ที่ยังขาด
10. Workers อัปเดต status ของตนและ append run/handoff; coordinator รวม overview,
    root board, HANDOFF และ resource release โดยไม่ทับประวัติข้อความ

Scouts เขียนคนละไฟล์ `data/agent_runs/<run_id>/<agent_id>.jsonl`
ไฟล์รอบค้นถูก ignore; curator publish เฉพาะ metadata และบันทึกสรุปที่ตรวจแล้ว

## ตัวอย่าง task ที่ coordinator ส่ง

```text
ใช้ agents/scout.md และ AGENTS.md
Scope: แนวทางเบาหวานชนิดที่ 2 ในผู้ใหญ่ ภาษาไทย
Prioritize: dmthai.org, ddc.moph.go.th, cpg.dms.go.th
ค้นไม่เกิน 8 queries; ส่งไม่เกิน 10 distinct candidates
บันทึก query และ URL ที่ตรวจจริง ไม่ invent publication dates
ห้ามแก้ canonical manifest; ส่ง JSONL ตาม data/schemas/document.schema.json
Output: data/agent_runs/<run_id>/diabetes.jsonl
เมื่อถูกปฏิเสธการเข้าถึงให้ระบุ blocked และหยุด retry ตาม budget
```

## Human handoff

ให้ reviewer ตรวจ scope, source identity, extraction evidence และ rights notes
บันทึกชื่อ/วันที่/ขอบเขตการตรวจจริงใน `human_review`
การตรวจรูปแบบ JSON ไม่ถือว่าได้อ่านหรืออนุมัติ clinical content
ข้อความคำตอบทางคลินิกสำหรับ gold set ต้องให้ผู้รู้ตรวจแยกจาก metadata review

## รูปแบบ runner ใน milestone M1

Runner ที่จะพัฒนาควรมี structured outputs, queue state, retries, host rate limit,
per-run token/cost accounting และ checkpoint เพื่อ resume งานโดยไม่ค้นซ้ำ
หยุดเมื่อ budget หมด, tool access blocked, ไม่มี candidate ใหม่ หรือ curator พบ scope drift
ใช้ provider/tool ที่ทีมเลือกจริง; ห้ามสร้าง URL หรือหลักฐานทดแทนผล search ที่ไม่มี
