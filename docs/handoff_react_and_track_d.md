# ส่งต่อจาก Track C: เพื่อนทำ ReAct agent และ Track D

สถานะ: Track C ทำถึงจุดที่ "รับงานต่อได้" แล้ว (ดูหัวข้อ 1) ผลที่ freeze แล้ว: `configs/rag/frozen_v1.json`; ผลสรุป: `runs/frozen_gen_v1/`; รายงาน: `output/TRACK_C_FINAL_REPORT_TH.md` (ในโฟลเดอร์งานของเจ้าของ); วิธีทำซ้ำ: `docs/track_c_reproduce.md`

## 1. ทำไมถึงพร้อมรับต่อ (สิ่งที่มีแล้ว)
- **สัญญาเดียวกันทุก pipeline:** `answer(question, retrieved=None) -> dict` ที่คืน `status, answer, claims[{text,cite}], citations[{id,chunk_id,document_id,edition_id,pdf_pages}], config_id, trace` ดู `src/ncdqa/rag/pipeline.py` (ฟังก์ชัน `interpret()` ตรวจและสร้างคำตอบ ใช้ซ้ำได้)
- **ตัวต้นแบบ 2 แบบให้ดูเป็นตัวอย่าง:** `pipeline.py` (Python ธรรมดา) และ `graph.py` (LangGraph + node `recover`)
- **รันและวัดด้วยสคริปต์ที่มี:** `scripts/run_generation.py --pipeline module:Class` (คลาสของตัวเอง สร้างด้วย `Class(retriever, client, cfg)`) → `scripts/eval_generation.py` → ตารางเทียบ
- **ตัวเทียบ (baseline) ที่ต้องเอาชนะ/เทียบ:** dev ตัวแปร B (hybrid) correctness 0.876, faithfulness 0.910; test B: 0.885 / 0.827 (`runs/frozen_gen_v1/eval/`)
- **เครื่องมือค้นที่เรียกเป็น tool ได้:** `ncdqa.retrieval.search.Retriever.search(query, variant, k, filters)` (ต้องมีดัชนีในเครื่อง ดู `HANDOFF.md`)
- **ตัวตรวจ/กัน:** `ncdqa.rag.validate.validate`, `ncdqa.rag.prompt.defuse` (เอาข้อความ observation มาใส่ prompt ต้องผ่านตัวนี้), `ncdqa.rag.guards.default_guards()`
- **ชุดทดสอบ injection ใช้กับ agent ได้:** `scripts/eval_guardrails.py` (ต้องรับ `retrieved=`) และ `data/eval/guardrail/` (silver)
- เทสต์ 75 ตัว: `python -X utf8 -m unittest tests.test_guards tests.test_rag_pipeline tests.test_rag_graph tests.test_guardrail_eval tests.test_eval_metrics`

## 2. ReAct agent (tool calling): เจ้าของทำเสร็จแล้ว 2026-10-12; เพื่อนใช้ต่อหรือปรับได้
สถานะ: มี `react_core.py`, `react_agent.py` (Python), `react_graph.py` (LangGraph), freeze `configs/rag/frozen_react_v1.json` และผล test ใน `runs/frozen_gen_v1/react_test_results.md` ผลสรุป: ReAct (seed_search, 3 รอบ) correctness 0.827 ต่ำกว่า B 0.885 / C 0.904 และใช้ token ราว 5.5 เท่า; test ถูกใช้แล้วสำหรับ config นี้ การปรับต่อต้องทำบน dev แล้ว freeze ไฟล์ใหม่ (ห้ามรัน test ซ้ำเพื่อปรับ)
ข้อกำหนดเดิมสำหรับคนที่จะทำ agent ตัวใหม่:
ทำ: คลาสใหม่ เช่น `src/ncdqa/rag/react_agent.py` ที่ทำตามสัญญาข้อ 1, tools อ่านอย่างเดียว (search, read_page, calculator), `max_steps` และงบ token, ผลลัพธ์สุดท้ายต้องผ่าน `validate`, เก็บ `trace["raw_output"]` และ `trace["evidence"]` (id → chunk_id ของ **ทุก** chunk ที่เห็น) เพื่อให้ตัวประเมินทำงานได้ รายละเอียดการออกแบบ R1–R4: `output/TRACK_C_REACT_AGENT_PLAN_TH.md` (สำเนาอยู่ในโฟลเดอร์งานของเจ้าของ)
กติกาการวัดที่ต้องรักษา: ปรับ prompt/ค่าบน **dev เท่านั้น** แล้ว freeze ก่อนรัน test **ครั้งเดียว**; ใช้ judge ชุดเดียวกัน (gpt-5.6-luna high ผ่าน codex) และ validator N7 เพื่อเทียบได้; ใช้แคชของ LLM client ทุกคำขอ; อย่าแก้ `configs/rag/frozen_v1.json` (ทำไฟล์ freeze ใหม่ของตัวเอง)
ค่าเชิงปฏิบัติ: LLM ตอบคำถามคือ Typhoon (`TYPHOON_API_KEY` ใน `.env`); judge ต้องล็อกอิน `codex` ในเครื่องที่รัน

## 3. สำหรับ Track D (คำตอบ/เดโม/รวมระบบ)
มีให้แล้ว: `demo.py` (CLI, input guard เปิดอยู่), disclaimer, การแสดงแหล่งอ้างอิง (เอกสาร ฉบับ หน้า PDF), `--graph`, `--variant`, `--show-evidence`
ยังเป็นงานของ D / ต้องตัดสินใจ: UI (ถ้าต้องการนอกจาก CLI), ข้อความ disclaimer ฉบับสุดท้าย (G7), นโยบายบันทึกคำถาม (G2), เกณฑ์ "ไม่พบ" (G4), README และสไลด์, การตรวจ clean-clone, โฟลว์ปฏิเสธเมื่อ guard บล็อก (ข้อความอยู่ใน `guards.py`)
ข้อควรรู้ที่ต้องบอกผู้ใช้/ในรายงาน: input guard เป็นกฎและวัดบนชุด silver เท่านั้น ตรวจชื่อที่ไม่มีคำนำหน้าไม่ได้; ระบบยังตอบกลุ่มประชากรใกล้เคียงแต่ไม่ตรงได้ (q157) และบางคำตอบมีหลาย claim ที่ตัวเลขขัดกัน (q088, q176) ซึ่งเป็นข้อจำกัดที่ทราบแล้ว

## 4. ก่อนเพื่อนจะรับต่อได้ ต้องมี (เช็กลิสต์)
- [x] สัญญา I/O และตัวอย่าง 2 แบบ, ปลั๊กอิน `--pipeline module:Class`
- [x] baseline ที่ freeze พร้อมตัวเลข, สคริปต์วัด, ชุดทดสอบ injection
- [x] เอกสารนี้ + `docs/track_c_reproduce.md`
- [ ] **โค้ดอยู่บน remote ที่เพื่อนดึงได้ (push/PR)** ตอนนี้ commit อยู่ในเครื่องเจ้าของเท่านั้น → ต้องให้เจ้าของสั่ง push
- [ ] **เพื่อนมีดัชนี/แพ็กเกจข้อมูลในเครื่อง** (`data/index/*`, `data/handoff/track_c_20261012/` ไม่อยู่ใน git) → ต้องส่งแยก (zip ที่ทำไว้แล้วในแพ็กเกจ handoff ใช้ได้; ข้อความ Siriraj ห้ามเผยแพร่ ตาม Decision 0008)
- [ ] เพื่อนมีคีย์ Typhoon และ `codex` login (หรือเจ้าของรัน judge ให้)
