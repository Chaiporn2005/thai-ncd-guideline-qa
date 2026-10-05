# Thai NCD Guideline Q&A

โปรเจกต์ NLP สำหรับค้นและถาม–ตอบแนวทางเวชปฏิบัติภาษาไทยด้าน NCDs ในผู้ใหญ่
เริ่มจากเบาหวานชนิดที่ 2 ความดันโลหิตสูง และไขมันในเลือดผิดปกติ
โดยใช้หลาย agents ช่วยรวบรวมและตรวจแหล่งข้อมูล ก่อนสร้างและประเมินระบบ RAG

**สถานะ: corpus preparation** — manifest58/selected55;มี39localPDFและ30เอกสารสกัดเพื่อreviewแล้ว;accepted0
ยังไม่มีระบบ Q&A, autonomous agent runner, corpus ที่รับครบ หรือผลทดลอง

## เริ่มอ่าน

- [ส่งต่องานล่าสุด](HANDOFF.md)
- [ผลเตรียมเอกสารในเครื่อง](docs/local_preparation_20261005.md)
- [คิวตรวจรายเอกสาร](data/manifests/local_preparation_20261005.csv)
- [วิธีดาวน์โหลดและสกัด/OCR](docs/download_pipeline.md)
- [Protocol กลาง](NCD%20-%200Protocol/PROTOCOL.md)
- [Orchestra: แบ่งงานและประสาน agents](NCD%20-%201Orchestra/README.md)
- [สถานะ 8 สายงาน](NCD%20-%201Orchestra/status/OVERVIEW.md)
- [รายการล่าสุด 55 PDF/คู่มือ: DM/HT/ไขมัน/CKD/NCD Clinic Plus](docs/source_catalog_50.md)
- [CSV รายการที่เลือก 55 งาน](data/manifests/corpus_50_candidates.csv)
- [ผลค้นรอบครบอย่างน้อย 50](research/20261005-ncd-50.md)
- [เอกสารเพิ่มโรคละ 10: PDF/คู่มือ](docs/source_catalog_20261005.md)
- [CSV รายการใหม่ 30 เอกสาร](data/manifests/collection_20261005.csv)
- [แผนงานและข้อกำหนดรายวิชา](plan.md)
- [บอร์ดสถานะงาน](board.md)
- [วิธีใช้ agents ช่วยค้นข้อมูล](docs/agent_workflow.md)
- [นโยบายรับเอกสารและการนับ corpus](docs/corpus_policy.md)
- [บทบาทและ prompts](agents/README.md)
- [ค่าเริ่มต้นของรอบค้น](configs/collection_agents.json)
- [รายการแหล่งข้อมูลตั้งต้น](data/manifests/documents.jsonl)
- [ผลค้นและข้อจำกัดของรอบแรก](docs/research_notes.md)
- [Actual queries และการคัดเลือกรอบเพิ่มเอกสาร](research/20261005-ncd-plus10.md)
- [ตำแหน่งเก็บ PDF/ข้อความ/metadata](data/README.md)
- [เครื่องมือ RAG และสถานะการติดตั้ง](docs/rag_tools.md)

## โครงสร้างการทำงาน

```text
NCD - 0Protocol/     คู่มือวงจรงานและ templates
NCD - 1Orchestra/    governance, shared plan, resources, messages, proposals, status
HANDOFF.md          จุดรับงานของ session ถัดไป
PROGRESS.md         ความก้าวหน้าและเหตุผลที่มีหลักฐาน
runs/LOG.md         บันทึกรอบค้น/ทดลองที่ทำจริง
research/notes.md   จุดเข้าถึง research notes ฉบับหลัก
configs/            limits และ registry สายงาน
agents/             role prompts
```

Coordinator ประสาน DM, HT, LIPID, optional CKD, NCD_SERVICE, CORPUS, RAG และ EVAL ตาม dependency
Curator เป็นผู้รวม manifest เพียงรายเดียว; `board.md` เป็น checklist ผู้ใช้
ส่วน `NCD - 1Orchestra/BOARD.md` เป็นข้อความ agents แบบ append-only
ค่า budget เป็นข้อเสนอ ยังไม่มี paid API runner หรือ watcher ที่เริ่มโดยโครงนี้

```powershell
python scripts/orchestra.py status
python scripts/orchestra.py check
```

CLI นี้อ่านสถานะและตรวจไฟล์/config เท่านั้น ไม่ dispatch agents

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
มีforegroundCLIสำหรับpublicreviewdownloadและlocalextractionแล้ว;ยังไม่มีautonomousagentdispatcher
Basic dependency:[requirements-ingest.txt](requirements-ingest.txt);rights gateและคิวhumanreviewยังคงแยกจากmetadata checks

## ข้อมูลและขอบเขต

- Repository เก็บ metadata และลิงก์; raw PDFs, keys และข้อมูลผู้ป่วยไม่อยู่ใน Git
- เอกสารตั้งต้นเป็น candidates แม้ตรวจหน้า publisher แล้ว; ยังไม่มี human approval
- ระบบเป้าหมายเป็นเครื่องมือศึกษาและค้นหลักฐานจากเอกสาร
- เน้นบริบทคนไทย; แยกแนวทางไทยออกจากงานวิจัยที่เก็บข้อมูลประชากรไทยจริง
- งานส่งสุดท้ายต้องมี demo, evaluation/results, slides และ `AI_AUDIT.md` ตาม instruction

เจ้าของ repository: `Chaiporn2005` • Visibility เริ่มต้น: Private
