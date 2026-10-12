# Thai NCD Guideline Q&A

โปรเจกต์ NLP สำหรับค้นและถาม–ตอบแนวทางเวชปฏิบัติภาษาไทยด้าน NCDs ในผู้ใหญ่
เริ่มจากเบาหวานชนิดที่ 2 ความดันโลหิตสูง และไขมันในเลือดผิดปกติ
โดยใช้หลาย agents ช่วยรวบรวมและตรวจแหล่งข้อมูล ก่อนสร้างและประเมินระบบ RAG

**สถานะ: corpus preparation** — manifest58/selected55;มี39localPDFและ30เอกสารสกัดเพื่อreviewแล้ว;accepted0
ยังไม่มีระบบ Q&A, autonomous agent runner, corpus ที่รับครบ หรือผลทดลอง

## Track C: ตอบคำถามจากหลักฐาน, ประเมินคุณภาพ และความปลอดภัย (อัปเดต 2026-10-12)

> บรรทัดสถานะด้านบนเป็นของช่วง corpus preparation และล้าสมัยแล้ว (ระบบ Q&A มีแล้ว) เจ้าของ repo ควรปรับให้ตรงกับสถานะล่าสุดของทุก Track ส่วนนี้เขียนเฉพาะส่วนที่ Track C ทำและวัดจริง

**ระบบ:** คำถาม → ตัวกรองอินพุต (ปิดบังข้อมูลส่วนบุคคล, ปฏิเสธขอสั่งยา/วินิจฉัยรายบุคคล, ความยาว, รูปแบบ injection) → ค้นคืน top-5 (bge-m3 + BM25 แบบ hybrid) → prompt (กติกา, ตัวคั่นข้อมูล, ย้ำคำสั่งท้าย, ตอบเป็น claim พร้อม citation) → LLM `typhoon-v2.5-30b-a3b-instruct` (API) → ตรวจทุก claim (citation ต้องเป็นหลักฐานที่ส่งจริง, ตัวเลขและคำอังกฤษต้องอยู่ในหลักฐาน) → output guard → คำตอบพร้อมแหล่งอ้างอิง (เอกสาร ฉบับ หน้า PDF) หรือปฏิเสธ/งดตอบ
มีสามรูปแบบเพื่อเปรียบเทียบ: pipeline คงที่ (Python), เวอร์ชัน LangGraph (เส้นทางเดียวกัน ผลเท่ากัน), และ agent แบบ ReAct (เรียก tool ค้นเอง; เขียนทั้ง Python และ LangGraph ผลตรงกัน)

**เดโม:**
```bash
python -X utf8 demo.py "ค่าเป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร"     # ต้องมีดัชนีในเครื่องและ TYPHOON_API_KEY ใน .env
python -X utf8 demo.py "..." --graph --variant C --show-evidence
```
ทำซ้ำผลทั้งหมดและติดตั้ง: [docs/track_c_reproduce.md](docs/track_c_reproduce.md)

**ผลบน test (52 ข้อที่ตอบได้ + 4 ข้อไม่มีคำตอบ, รันครั้งเดียวต่อระบบหลัง freeze; judge gpt-5.6-luna ไม่มีคนตรวจ):**

| ระบบ | correctness | faithfulness | hit@5 | token/ข้อ |
|---|---|---|---|---|
| A dense | 0.798 | 0.803 | 43/52 | 4.8k |
| B hybrid | 0.885 | 0.827 | 46/52 | 4.8k |
| C hybrid + rerank | **0.904** | **0.886** | 48/52 | 4.8k |
| D BM25 ล้วน | 0.808 | 0.768 | 42/52 | 4.8k |
| ReAct (Python = LangGraph) | 0.827 | 0.833 | 47/52 | 26.5k |

metric: BERTScore (bge-m3 ชั้น 8; แทบไม่ไวต่อถูก/ผิด ใช้ดูอย่างเดียว), Faithfulness แบบ RAGAS ที่เขียนเอง, correctness อ้างอิงเฉลย, citation correctness, abstention, hit@5, token/เวลา; ablation = A/B/C/D และ pipeline คงที่เทียบ ReAct

**ความปลอดภัย:** ชุดเคส prompt injection อิง OWASP Top 10 for LLM Applications 2025 (LLM01, 02, 05, 06, 07, 08, 09, 10) 76 เคส: ผลโจมตีที่ถึงผู้ใช้ 0.58 (ไม่มีการป้องกัน) → 0.09 (ชั้นเดิม) → **0/45** (ระบบที่ส่งมอบ; ReAct 1/51 ซึ่งเป็นเคสที่ผู้ใช้สั่งเอง) ดู [docs/owasp_guardrails.md](docs/owasp_guardrails.md)

**ข้อจำกัดที่ต้องรู้:** test มี 52 ข้อ (ช่วงเชื่อมั่นกว้าง), judge เป็น LLM มีความแปรปรวนราว ±0.03 (judge ตัวที่สอง Gemini ตรงกัน 0.87–0.92 บนข้อที่ตัดสินได้ ครอบคลุม ~75%), เคส injection และ input guard วัดบนชุดที่ AI เขียน (silver ไม่มีคนตรวจ), การ mask ข้อมูลส่วนบุคคลพลาดชื่อไม่มีคำนำหน้า, chunk ปลอมที่เขียนเหมือนแนวทางจริงกันไม่ได้ที่ชั้นตอบ, ผลเป็นของ LLM ตัวเดียว ไม่ใช่คำแนะนำทางการแพทย์
รายละเอียดข้อผิดพลาดและสาเหตุ: [docs/error_analysis_track_c.md](docs/error_analysis_track_c.md) • คำตัดสินของเจ้าของ: [docs/decisions_guardrail_harness.md](docs/decisions_guardrail_harness.md) • สถานะ/งานค้าง: [docs/CHECKPOINT_TRACK_C_20261012.md](docs/CHECKPOINT_TRACK_C_20261012.md) • การใช้ AI: [AI_AUDIT.md](AI_AUDIT.md)

## เริ่มอ่าน

- [โฟลเดอร์เอกสารแยกตามโรคและระบบบริการ](data/by_disease/README.md)
- [ภาพออกแบบระบบ RAG สำหรับโครงการนี้](docs/rag_architecture.md)
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
- [Catalogue 55 PDF/คู่มือ (รวมรอบโรคละ 10)](docs/source_catalog_50.md)
- [CSV รายการ candidates ทั้งหมด](data/manifests/corpus_50_candidates.csv)
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
