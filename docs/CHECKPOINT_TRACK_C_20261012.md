# Checkpoint ของ Track C, 2026-10-12 (เขียนก่อนเจ้าของออฟไลน์; อ่านอันนี้ก่อน)

กำหนดส่ง 2026-10-16 สาขา `rag/track-b-l1` (repo `Chaiporn2005/thai-ncd-guideline-qa`) ทุกอย่างในเอกสารนี้ commit และ push แล้ว ยกเว้นข้อ "ยังไม่ขึ้น git" ด้านล่าง

## 1. ทำเสร็จแล้ว (ดูรายละเอียดในไฟล์ที่ระบุ)
| งาน | ที่ไหน | ผลสั้นๆ |
|---|---|---|
| pipeline คงที่ (Python, LangGraph), A/B/C/D, judge luna | `docs/track_c_reproduce.md`, `runs/frozen_gen_v1/` | test correctness A 0.798 / B 0.885 / C 0.904 / D 0.808 |
| ReAct (Python = LangGraph), freeze `frozen_react_v1`, test รันครั้งเดียว | `runs/frozen_gen_v1/react_test_results.md` | 0.827 ไม่ชนะ B/C; token ราว 5.5 เท่า |
| ชุดเคส injection OWASP LLM Top 10 (76 เคส, silver) + guardrail input/tool/output | `docs/owasp_guardrails.md`, `src/ncdqa/rag/owasp_guards.py` | ระบบที่ส่งมอบ ASR ถึงผู้ใช้ 0/45 (pipeline), 1/51 (ReAct, เคสผู้ใช้สั่งเอง) |
| `demo.py` ต่อ guardrail ครบ (mask ข้อมูลส่วนบุคคล, ขอบเขต, injection, output guard, log เฉพาะ metadata, validator N8) | `demo.py` | ทดสอบ 4 คำถามผ่าน |
| คำตัดสินของเจ้าของ G1–G7, H1–H5, O1–O4 | `docs/decisions_guardrail_harness.md` | ยังเป็น `[FILL IN]`: G4 (ยืนยันคงปิดเกณฑ์คะแนน), H5 (ยืนยันปิดข้อ) |
| error analysis + ตัวอย่าง metformin | `docs/error_analysis_track_c.md` | สาเหตุหลัก: ตอบไม่ครบ, ตาราง, validator ตัดเลขที่ผู้ใช้เขียนเอง |
| ชุดแก้ v2 (prompt p4 + validator) | `configs/rag/generate_v2.json`, error_analysis §8 | **ไม่รับ** ตามกติกาที่ประกาศก่อนรัน (B faith −0.05, C corr −0.03); ไม่ได้รัน test |
| วัดการ mask ข้อมูลส่วนบุคคล | `scripts/eval_masking.py`, error_analysis §9 | รูปแบบปกติ 11/11, นอกรูปแบบ 4/7 |
| AI_AUDIT ส่วน Track C | `AI_AUDIT.md` (§2C, §3.3, §4.4, Contribution Map) | เหตุการณ์จริงเท่านั้น |
| รายงานภาษาไทย (อยู่นอก repo) | `../output/TRACK_C_FINAL_REPORT_TH.md` หัวข้อ 11 และ 12 | ไม่ขึ้น git |

## 2. งานที่ยังรันค้างอยู่ตอนเขียน (ต้องมีเน็ต)
- **judge ตัวที่สอง Gemini 3.8 Flash high ผ่าน `agy` วัด correctness บน test เฉพาะ B, C, ReAct**: คำสั่งรันเป็น process เบื้องหลังที่ต้องใช้อินเทอร์เน็ต ถ้าออฟไลน์ระหว่างรัน มันจะล้มเหลวและไม่เขียนผล ผลลัพธ์ที่คาดหวัง: `data/index/runs/eval/test_agy_gemini_N7/` (ไม่ขึ้น git) ถ้าไม่มีโฟลเดอร์นี้ ให้รันใหม่ (แคชเก็บคำตัดสินที่เสร็จแล้วไว้ที่ `data/index/llm_cache/judge.jsonl` จึงไม่ต้องเริ่มจากศูนย์):
```bash
Q=data/handoff/track_c_20261012/questions_all_reviewed.jsonl
python -X utf8 scripts/eval_generation.py --answers B=data/index/runs/gen/test-B/answers.jsonl C=data/index/runs/gen/test-C/answers.jsonl ReActPy=data/index/runs/gen/test-react-py/answers.jsonl \
  --chunks data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl --validator N7 --judge agy --workers 6 --no-faithfulness --bert-model BAAI/bge-m3 --bert-layer 8 --idf-questions $Q \
  --out data/index/runs/eval/test_agy_gemini_N7
```
  ช้ามาก (ราว 1–2 คำตัดสิน/นาที) จึงตัด faithfulness ของ Gemini ออก (ครบทุกระบบจะราว 100 นาที) หลังเสร็จ ให้เทียบ correctness กับ luna (`data/index/runs/eval/test_luna_N7`, `test_react-py_luna_N7`) แล้วบันทึกใน error_analysis และ AI_AUDIT (C-D20)
- ใน AI_AUDIT C-D20 ระบุว่าใช้ Gemini วัดซ้ำบน test: ถ้ารอบนี้ไม่เสร็จ ให้แก้ข้อความเป็น "ไม่เสร็จ (ช้า/โควตา/ออฟไลน์)" อย่าอ้างว่ามีผล

## 3. ยังต้องทำ (ลำดับความสำคัญ)
1. **เจ้าของเขียนเอง (กติกาวิชา ห้าม AI เขียนแทน):** "What Would Break?" ใน AI_AUDIT, `[FILL IN]` ระดับที่ตรวจโค้ด/ผล, ยืนยัน C-D18 (N8), G4, H5, คำตอบสะท้อน 3 ข้อของวิชา
2. README และสไลด์ (ยังไม่มี; ใช้ `docs/track_c_reproduce.md`, `docs/error_analysis_track_c.md`, `docs/owasp_guardrails.md` เป็นแหล่ง)
3. clean-clone ตรวจว่าทำตาม `docs/track_c_reproduce.md` แล้วรันถึง `demo.py` ได้ (ต้องมีดัชนีและแพ็กเกจ `data/handoff/track_c_20261012/` ซึ่งไม่อยู่ใน git; ข้อความ Siriraj ห้ามเผยแพร่ ตาม Decision 0008)
4. ถ้ามีเวลา: แก้ที่เหลือตาม error analysis (ตาราง, ตอบไม่ครบ, claim ขัดกัน, ประชากรไม่ตรง q157) ต้อง freeze ใหม่ + test ครั้งเดียว; ห้ามรัน test ซ้ำเพื่อปรับ

## 4. ข้อควรระวัง
- test split ถูกใช้แล้วสำหรับ `frozen_v1` และ `frozen_react_v1` ห้ามรันซ้ำเพื่อปรับค่า
- judge เป็น LLM ไม่มีคนตรวจ และมีความแปรปรวน ±0.03 (error_analysis §5): อ่านผลเป็นทิศทาง, test มี 52 ข้อ
- เคส injection ทั้งหมดเป็น silver (ไม่มีคนตรวจ ตามที่เจ้าของตัดสิน)
- ห้ามใส่คีย์ใน git (`.env` ไม่ขึ้น git); คีย์ Typhoon อยู่ใน `.env`

## 5. ยังไม่ขึ้น git (ตั้งใจ) / ต้องจัดการเอง
- `data/external/` (ชุดข้อมูลสาธารณะ ใบอนุญาตต่างกัน) และ `data/index/` (ดัชนี ผลดิบ แคช) อยู่ในเครื่องเท่านั้น
- `data/eval/guardrail/cases_owasp_v1.jsonl` (ชุดแรกที่ออกแบบผิด) ไม่ track ใช้ v2 เท่านั้น ลบได้
- `C:\Users\acer\Downloads\kaggle (2).json` (โทเคน Kaggle บัญชีที่สอง) ควรลบออกจาก Downloads
- Kaggle kernel เก่าของบัญชีแรกอาจยังรันอยู่ (ไม่มีคำสั่งยกเลิก)
- รายงานภาษาไทยและแผนทั้งหมดอยู่ที่ `D:\KMITL\NLP\NLP-Year3\team-project\output\` (นอก repo): `TRACK_C_FINAL_REPORT_TH.md`, `TRACK_C_*_TH.md`, `AI_AUDIT_TRACK_C_DRAFT_TH.md`
