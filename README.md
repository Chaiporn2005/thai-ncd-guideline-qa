# Thai NCD Guideline Q&A

โปรเจกต์ NLP สำหรับค้นและถาม–ตอบแนวทางเวชปฏิบัติภาษาไทยด้าน NCDs ในผู้ใหญ่
เริ่มจากเบาหวานชนิดที่ 2 ความดันโลหิตสูง และไขมันในเลือดผิดปกติ
โดยใช้หลาย agents ช่วยรวบรวมและตรวจแหล่งข้อมูล ก่อนสร้างและประเมินระบบ RAG

**สถานะ: planning / research scaffold** — มีแผน, agent prompts, seed manifest และตัวตรวจ metadata แล้ว
ยังไม่มีระบบ Q&A, autonomous agent runner, corpus ที่รับครบ หรือผลทดลอง

## เริ่มอ่าน

- [แผนงานและข้อกำหนดรายวิชา](plan.md)
- [บอร์ดสถานะงาน](board.md)
- [วิธีใช้ agents ช่วยค้นข้อมูล](docs/agent_workflow.md)
- [นโยบายรับเอกสารและการนับ corpus](docs/corpus_policy.md)
- [บทบาทและ prompts](agents/README.md)
- [ค่าเริ่มต้นของรอบค้น](configs/collection_agents.json)
- [รายการแหล่งข้อมูลตั้งต้น](data/manifests/documents.jsonl)
- [ผลค้นและข้อจำกัดของรอบแรก](docs/research_notes.md)

## ตรวจ manifest

ใช้ Python 3.10 ขึ้นไป; ตัวตรวจนี้ใช้ standard library ไม่ต้องติดตั้ง dependencies

```powershell
python scripts/validate_manifest.py
```

ตรวจ required fields, URL/date, IDs, สถานะรับเอกสาร และการอนุมัติ
แล้วสรุปจำนวน unique works, editions และ accepted documents
**ไม่ตรวจเนื้อหา PDF หรือความถูกต้องทางคลินิก และไม่รับรองว่าผ่านเกณฑ์ 50 เอกสาร**

## ทำงานกับหลาย agents

ใช้ coordinator dispatch งานตาม [workflow](docs/agent_workflow.md)
ให้ scouts ทำงานในคนละ scope และส่งผลคนละไฟล์ แล้วให้ curator รวมผลเพียงตัวเดียว
prompts ใน `agents/` ใช้กับเครื่องมือที่รองรับ subagents ได้
การวาง prompt files ใน repository ไม่ได้เริ่ม agents อัตโนมัติ

## ข้อมูลและขอบเขต

- Repository เก็บ metadata และลิงก์; raw PDFs, keys และข้อมูลผู้ป่วยไม่อยู่ใน Git
- เอกสารตั้งต้นเป็น candidates แม้ตรวจหน้า publisher แล้ว; ยังไม่มี human approval
- ระบบเป้าหมายเป็นเครื่องมือศึกษาและค้นหลักฐานจากเอกสาร
- เน้นบริบทคนไทย; แยกแนวทางไทยออกจากงานวิจัยที่เก็บข้อมูลประชากรไทยจริง
- งานส่งสุดท้ายต้องมี demo, evaluation/results, slides และ `AI_AUDIT.md` ตาม instruction

เจ้าของ repository: `Chaiporn2005` • Visibility เริ่มต้น: Private
