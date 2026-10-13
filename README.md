# Thai NCD Guideline Q&A

ระบบถาม–ตอบ (RAG) จาก **แนวทางเวชปฏิบัติโรคไม่ติดต่อเรื้อรัง (NCD) ภาษาไทย**: เบาหวานชนิดที่ 2, ความดันโลหิตสูง, ไขมันในเลือดผิดปกติ และไตเรื้อรัง ตอบเป็นข้อเท็จจริงสั้น ๆ **พร้อมแหล่งอ้างอิง (เอกสาร ฉบับ หน้า PDF)** ถ้าหลักฐานไม่พอจะ **งดตอบ** ไม่เดา
โครงงานรายวิชา NLP with Deep Learning (KMITL) ทีม 4 คน; เป็นเครื่องมือเพื่อการศึกษา **ไม่ใช่คำแนะนำทางการแพทย์**

| รายการส่งตามโจทย์ | อยู่ที่ |
|---|---|
| โค้ดที่รันได้ + README | repo นี้ (หัวข้อ 2 = ติดตั้งและรัน) |
| เดโม | [`demo.py`](demo.py) (CLI และหน้าเว็บในเครื่อง `--web`) |
| สคริปต์ประเมิน + ผลที่บันทึกเป็นไฟล์ | หัวข้อ 6 (ผลอยู่ใน [`runs/`](runs)) |
| AI Audit | [`AI_AUDIT.md`](AI_AUDIT.md) |
| สไลด์ | โครงร่างที่ [`docs/slides_track_c_outline_TH.md`](docs/slides_track_c_outline_TH.md) |

## 1. ระบบทำอะไร และผลสรุป

```text
คำถาม ─► ตัวกรองอินพุต ─► ค้นคืน top-5 ─► prompt ─► LLM ─► ตรวจทุก claim ─► ตัวกรองเอาต์พุต ─► คำตอบ + แหล่งอ้างอิง / งดตอบ
         (ปิดบังข้อมูลส่วนบุคคล  (bge-m3 dense     (กติกา, ตัวคั่น,  Typhoon   (citation ต้องเป็น     (markup, ลิงก์,
          ปฏิเสธสั่งยา/วินิจฉัย   + BM25 ไทย        ย้ำคำสั่งท้าย,   v2.5-30B   chunk ที่ส่งจริง,      ข้อความ prompt,
          ฉุกเฉิน→1669, ความยาว,  แบบ hybrid)       ตอบเป็น claim)             เลข/คำอังกฤษต้องอยู่     ข้อมูลส่วนบุคคล)
          รูปแบบ injection)                                                       ในหลักฐาน)
```

- **Corpus จริง:** 66 เอกสาร / 3,716 หน้า PDF (แนวทางเวชปฏิบัติไทย, คู่มือ, เอกสารบริการ NCD) → 4,347 chunk (parent 512 token) และ 23,819 chunk (child 128 token)
- **ตัวแปรที่เทียบ (ablation):** A dense · B hybrid (dense + BM25 ไทย) · C B + cross-encoder rerank · D BM25 ล้วน · pipeline คงที่ (Python) เทียบ **LangGraph** เทียบ **ReAct agent** (tool calling; เขียนทั้ง Python และ LangGraph)
- **Metric:** correctness (judge อ้างเฉลย), Faithfulness แบบ RAGAS (เขียนเอง), BERTScore, citation correctness, hit@5/Recall@k/MRR, abstention, token/เวลา, attack success rate (ความปลอดภัย)
- **ผลหลัก (test, 52 ข้อที่ตอบได้, รันครั้งเดียวหลัง freeze):** hybrid ดีกว่า dense, rerank ช่วยต่อ, **agent (ReAct) ไม่ชนะ pipeline คงที่** ที่ต้นทุน ~5.5 เท่า (ตารางหัวข้อ 5)

## 2. ติดตั้งและรัน (เครื่องใหม่ ทำตามได้ทีละขั้น)

> **คู่มือละเอียดพร้อมภาพหน้าจอจริงทุกขั้น (สำหรับเพื่อนที่จะเปิดเดโมวันจริง): [`docs/SETUP_GUIDE_TH.md`](docs/SETUP_GUIDE_TH.md)** · สรุปสั้นด้านล่าง

ต้องมี: Python 3.12, [`uv`](https://docs.astral.sh/uv/) (หรือ pip), อินเทอร์เน็ต **ครั้งแรก** (ดาวน์โหลดโมเดลหลาย GB และเรียก API), เครื่อง CPU ปกติใช้ได้ (ไม่ต้องมี GPU; โมเดลค้นคืนใช้ RAM หลาย GB)

```bash
# 1) โค้ด
git clone https://github.com/Chaiporn2005/thai-ncd-guideline-qa && cd thai-ncd-guideline-qa
git checkout rag/track-b-l1                      # สาขาที่ส่งงาน

# 2) สภาพแวดล้อมและแพ็กเกจ
uv venv --python 3.12 .venv
source .venv/bin/activate                        # Windows PowerShell: .venv\Scripts\Activate.ps1
uv pip install -r requirements-rag.txt -r requirements-agent.txt

# 3) ข้อมูลที่ไม่อยู่ใน git (ดัชนีมีข้อความเอกสาร; ขอไฟล์ ncd_demo_bundle.zip ~63 MB จากทีม ส่งในทีมเท่านั้น ห้ามเผยแพร่)
python -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip

# 4) ค่าตั้งและคีย์ (คีย์ Typhoon ขอจากทีม; ห้ามใส่ลง git)
cp configs/llm/providers.example.yaml configs/llm/providers.yaml
cp .env.example .env                             # แล้วใส่ค่าหลัง TYPHOON_API_KEY=

# 5) ตรวจเครื่อง: บอกสิ่งที่ขาดพร้อมคำสั่งแก้
python -X utf8 demo.py --check

# 6) รันเดโม
python -X utf8 demo.py --warm                    # ครั้งแรก: โหลดโมเดล + เตรียมแคชคำถามตัวอย่าง 9 ข้อ (ใช้เน็ต)
python -X utf8 demo.py --web                     # หน้าเว็บ http://127.0.0.1:8780 (ปุ่มคำถามตัวอย่าง, แผงหลักฐาน, แถบ disclaimer ถาวร)
python -X utf8 demo.py "ค่าเป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร"
```

**ตัวเลือกของเดโม:** `--graph` (LangGraph) · `--agent react` (ReAct) · `--variant A|B|C` (C ใช้ reranker ช้าบน CPU 15–36 วินาที) · `--show-evidence` · `--no-guard` (ปิด guard เพื่อ ablation) · `--no-log` (ไม่บันทึก metadata)

**วันนำเสนอ (เช็กลิสต์):** รัน `demo.py --check` และ `demo.py --warm` ล่วงหน้าบนเครื่องที่จะใช้ (เพื่อดาวน์โหลดโมเดลและเติมแคช) · คำถามตัวอย่าง 9 ข้อรันได้ **แม้ไม่มีอินเทอร์เน็ต** เพราะคำตอบอยู่ในแคช (ถ้าเครือข่ายช้า/ไม่เสถียร ตั้ง `HF_HUB_OFFLINE=1` เพื่อไม่ให้รอเช็กโมเดลออนไลน์) (`data/index/llm_cache/demo`, อยู่ใน bundle) · คำถามใหม่ต้องมีเน็ตและคีย์ · ถ้าเบราว์เซอร์ไม่เปิด ใช้โหมดบรรทัดคำสั่งแทนได้ · ปิดด้วย Ctrl+C

**เทสต์ (Track C, ไม่ต้องใช้ดัชนีหรือเครือข่าย):** `PYTHONPATH=src python -X utf8 -m unittest tests.test_guards tests.test_owasp_guards tests.test_rag_pipeline tests.test_rag_graph tests.test_react tests.test_guardrail_eval tests.test_eval_metrics tests.test_validate_question_numbers tests.test_demo_support` (เทสต์ของ Track A/B บางตัวต้องการแพ็กเกจเพิ่มจาก `requirements-ingest.txt`)

## 3. สถาปัตยกรรมและโค้ดหลัก

| ขั้น | ไฟล์ |
|---|---|
| chunk (ย่อหน้า→ประโยค→แถวตาราง, ไม่ตัดกลางคำ, token-aware) | [`src/ncdqa/retrieval/chunking.py`](src/ncdqa/retrieval/chunking.py) |
| ค้นคืน A/B/C (`Retriever.search`) | [`src/ncdqa/retrieval/search.py`](src/ncdqa/retrieval/search.py), [`dense.py`](src/ncdqa/retrieval/dense.py), [`bm25.py`](src/ncdqa/retrieval/bm25.py), [`fusion.py`](src/ncdqa/retrieval/fusion.py) |
| pipeline คงที่ / LangGraph | [`src/ncdqa/rag/pipeline.py`](src/ncdqa/rag/pipeline.py), [`graph.py`](src/ncdqa/rag/graph.py), [`prompt.py`](src/ncdqa/rag/prompt.py), [`validate.py`](src/ncdqa/rag/validate.py) |
| ReAct agent (Python / LangGraph) | [`react_agent.py`](src/ncdqa/rag/react_agent.py), [`react_graph.py`](src/ncdqa/rag/react_graph.py), [`react_core.py`](src/ncdqa/rag/react_core.py) |
| guardrail (input/tool/output, อิง OWASP LLM Top 10) | [`guards.py`](src/ncdqa/rag/guards.py), [`owasp_guards.py`](src/ncdqa/rag/owasp_guards.py) |
| ตัวประเมิน (BERTScore, Faithfulness, correctness) | [`src/ncdqa/eval/`](src/ncdqa/eval) |
| ค่าตั้งที่ freeze | [`configs/retrieval/frozen_v1.json`](configs/retrieval/frozen_v1.json), [`configs/rag/frozen_v1.json`](configs/rag/frozen_v1.json), [`configs/rag/frozen_react_v1.json`](configs/rag/frozen_react_v1.json) |

## 4. การตัดสินใจเทคนิคหลักและเหตุผล (รายละเอียดและหลักฐานตามลิงก์)

| เรื่อง | เลือก | ทำไม | หลักฐาน |
|---|---|---|---|
| ขนาด chunk | child 128 token ใช้ค้น → ส่ง parent 512 token ให้โมเดล (parent-child) | chunk เล็กตรงข้อเท็จจริง/ตัวเลขดีกว่า chunk ใหญ่ที่ให้บริบทครบ; ทดสอบ 128/256/384/512 | [`docs/chunk_size_evidence.md`](docs/chunk_size_evidence.md) |
| โมเดล embedding | `BAAI/bge-m3` (เทียบ multilingual-e5-base) | รองรับภาษาไทย ใช้บน CPU ได้; ทดสอบทั้ง bge-m3 และ e5-base แล้วเลือกตามผลบน dev (ไม่ใช้ test เลือก) | [`docs/hybrid_retrieval_experiment.md`](docs/hybrid_retrieval_experiment.md) |
| การค้น | hybrid: dense + BM25 ตัวอักษร 3 ตัว (convex α = 0.6) | ภาษาไทยไม่มีช่องว่างคั่นคำ BM25 ระดับตัวอักษรช่วยชื่อยาและตัวเลข; เทียบหลายวิธีในเอกสารที่อ้าง | เอกสารเดียวกัน; ผลบน benchmark สาธารณะ 14 ชุดใน `runs/frozen_gen_v1/public_benchmarks/` |
| rerank | cross-encoder `bge-reranker-v2-m3` เป็นตัวเลือก C | แม่นขึ้นที่อันดับต้น แต่ช้ามากบน CPU จึงไม่ใช่ค่าเริ่มต้น | `docs/handoff_track_c.md` |
| ตัวสร้างคำตอบ | Typhoon `typhoon-v2.5-30b-a3b-instruct` (API), temperature 0, แคชทุกคำขอ | ภาษาไทยดี; คำขอซ้ำใช้แคชเพื่อให้ผลทำซ้ำได้ | `configs/rag/generate_v1.json` |
| ตรวจคำตอบ | ทุก claim ต้องมี citation ที่ชี้ chunk ที่ส่งจริง และเลข/คำอังกฤษต้องอยู่ในหลักฐาน | ลดการแต่งตัวเลข/แหล่งอ้างอิง; ตัดทิ้ง ไม่ซ่อมให้ | `src/ncdqa/rag/validate.py`, [`docs/error_analysis_track_c.md`](docs/error_analysis_track_c.md) |
| ความปลอดภัย | หลายชั้น ไม่ใช้ LLM เพิ่ม | ไม่มีชั้นเดียวที่กัน prompt injection ได้หมด (OWASP) | [`docs/owasp_guardrails.md`](docs/owasp_guardrails.md) |
| นโยบาย | G1–G7, H1–H5 ตัดสินโดยเจ้าของ | ข้อมูลส่วนบุคคลถูก mask, ไม่วินิจฉัยรายบุคคล, ใช้ API ภายนอก | [`docs/decisions_guardrail_harness.md`](docs/decisions_guardrail_harness.md) |

## 5. ผลการทดลอง

**ก. Retrieval (Track B, test 52 ข้อที่ตอบได้):**

| ระบบ | R@1 | R@5 | R@10 | MRR@10 |
|---|---|---|---|---|
| A dense | 0.462 | 0.808 | 0.827 | 0.618 |
| B hybrid | 0.587 | 0.885 | 0.981 | 0.737 |
| C hybrid + rerank | 0.615 | 0.913 | 0.952 | 0.771 |

**ข. คำตอบ (Track C, test 52 ข้อที่ตอบได้ + 4 ข้อไม่มีคำตอบ, judge gpt-5.6-luna, validator N7):**

| ระบบ | correctness | faithfulness | BERTScore F1 | hit@5 | token/ข้อ |
|---|---|---|---|---|---|
| A dense | 0.798 | 0.803 | 0.821 | 43/52 | 4.8k |
| B hybrid | 0.885 | 0.827 | 0.821 | 46/52 | 4.8k |
| C hybrid + rerank | **0.904** | **0.886** | 0.821 | 48/52 | 4.8k |
| D BM25 ล้วน | 0.808 | 0.768 | – | 42/52 | 4.8k |
| ReAct (Python = LangGraph) | 0.827 | 0.833 | – | 47/52 | 26.5k |

อ่านผล: hybrid ชนะ dense ชัด (correctness +0.087), rerank ช่วยเพิ่มอีกเล็กน้อย (ในช่วงความไม่แน่นอน), **ReAct ไม่ดีกว่า pipeline คงที่แม้ใช้ token 5.5 เท่า** (ผลต่างกับ B −0.058, ช่วงเชื่อมั่น 95% [−0.154, +0.038]) BERTScore เท่ากันทุกระบบเพราะเป็นสมบัติของเมตริก (ไม่ไวต่อถูก/ผิด) ไม่ใช่บั๊ก; judge ตัวที่สอง (Gemini) ตรงกัน 0.85–0.96 บนข้อที่ตัดสินได้ ลำดับ C > B > ReAct เหมือนกัน

**ค. ความปลอดภัย (OWASP LLM Top 10, 76 เคส silver):** ผลโจมตีที่ถึงผู้ใช้ 0.58 (ไม่มีการป้องกัน) → 0.09 (ชั้นเดิม) → **0/45** (ระบบที่ส่งมอบ; ReAct 1/51 ซึ่งเป็นเคสที่ผู้ใช้สั่งเอง) คำถามปกติไม่ถูกปฏิเสธเพิ่ม

## 6. สคริปต์ประเมินและที่เก็บผล

| ประเมินอะไร | คำสั่ง (ต้นทาง) | ผลที่บันทึก |
|---|---|---|
| retrieval A/B/C | [`scripts/run_retrieval.py`](scripts/run_retrieval.py), [`scripts/compare_runs.py`](scripts/compare_runs.py) | [`runs/frozen_v1/`](runs/frozen_v1) |
| สร้างคำตอบ | [`scripts/run_generation.py`](scripts/run_generation.py) (`--pipeline plain\|graph\|module:Class`) | `data/index/runs/gen/` (ไม่ขึ้น git) |
| คะแนนคำตอบ (BERTScore, Faithfulness, correctness, citation, abstention) | [`scripts/eval_generation.py`](scripts/eval_generation.py) | [`runs/frozen_gen_v1/eval/`](runs/frozen_gen_v1/eval) |
| ReAct เทียบ pipeline คงที่ | `run_generation.py --pipeline ncdqa.rag.react_agent:ReactAgent` + `eval_generation.py` | [`runs/frozen_gen_v1/react_test_results.md`](runs/frozen_gen_v1/react_test_results.md) |
| prompt injection (OWASP) | [`scripts/build_owasp_cases.py`](scripts/build_owasp_cases.py), [`scripts/eval_owasp.py`](scripts/eval_owasp.py) | [`runs/frozen_gen_v1/owasp/`](runs/frozen_gen_v1/owasp) |
| input guard / การ mask / เกณฑ์ abstain | `eval_input_guard.py`, `eval_masking.py`, `calibrate_abstain.py` | `runs/frozen_gen_v1/guardrail/`, `error_analysis/`, `g4/` |
| benchmark สาธารณะ (14 ชุด, Kaggle T4) | [`scripts/eval_public_benchmarks.py`](scripts/eval_public_benchmarks.py), [`infra/kaggle_public_benchmarks/`](infra/kaggle_public_benchmarks) | `runs/frozen_gen_v1/public_benchmarks/` |

ทำซ้ำทุกขั้นตอนเต็ม (ต้องมีข้อมูลเต็มชุดและ judge CLI): [`docs/track_c_reproduce.md`](docs/track_c_reproduce.md) · ข้อควรระวังของการวัด: test ใช้ครั้งเดียวต่อ config ที่ freeze, judge เป็น LLM ไม่มีคนตรวจและแปรปรวนราว ±0.03

## 7. Failure analysis ย่อ (ฉบับเต็ม: [`docs/error_analysis_track_c.md`](docs/error_analysis_track_c.md))

ค้นเก่ง (hit@5 B 46/52) แต่ test ตอบไม่ผ่าน 9/52 ข้อ: ค้นพลาด 3, ตอบไม่ครบ 2, validator ตัดคำตอบที่ถูกเพราะเลข/คำอังกฤษที่ผู้ใช้เขียนเอง 2, โมเดลอ้างชิ้นผิด 1, claim ขัดกัน 1; ตัวอย่างที่ยังพลาด: ตารางที่ถูกแตกคนละ chunk (q141), ประชากรใกล้เคียงแต่ไม่ตรง (q157 หญิงตั้งครรภ์ที่เป็นไตระยะ 4 ตอบด้วยเกณฑ์ไตทั่วไป); ลองแก้ด้วย prompt/validator สองชุดแล้ว **ไม่ผ่านกติกาที่ประกาศก่อนรัน** จึงไม่ใช้ (ไม่แตะ test)

## 8. ข้อจำกัด

test มี 52 ข้อ (ช่วงเชื่อมั่นกว้าง) · judge เป็น LLM ไม่มีคนตรวจ · เคส injection และ input guard วัดบนชุดที่ AI เขียน (silver) · การ mask พลาดชื่อที่ไม่มีคำนำหน้า · chunk ปลอมที่เขียนเหมือนแนวทางจริงกันที่ชั้นตอบไม่ได้ · ผลเป็นของ LLM ตัวเดียว · ไม่ใช่คำแนะนำทางการแพทย์ ไม่ใช้กับผู้ป่วยจริง · ข้อมูลเอกสารบางส่วน (แผ่นพับศิริราช) ห้ามเผยแพร่ จึงไม่อยู่ใน git ตาม [`docs/security_and_ethics.md`](docs/security_and_ethics.md)

## 9. ทีม

| ชื่อ | งาน |
|---|---|
| ธนกฤต เสมอหน้า | Track B (ค้นคืน) และ Track C (ตอบคำถาม ประเมิน ความปลอดภัย) |
| ชัยพร ออฤดี | Track A (เอกสาร, สกัดข้อความ, normalize), เจ้าของ repo |
| ธนวัฒน์ สุริยะ, คณิณ แคลวิณ ชมวิวัฒน์ | ตรวจชุดคำถาม gold, fidelity review |

การใช้ AI ทั้งหมดบันทึกใน [`AI_AUDIT.md`](AI_AUDIT.md) (เครื่องมือ, prompt, การตัดสินใจ, ข้อผิดพลาดที่จับได้, ผู้ร่วมงาน) · สถานะและงานค้าง: [`docs/CHECKPOINT_TRACK_C_20261012.md`](docs/CHECKPOINT_TRACK_C_20261012.md)

## 10. เอกสารและโครงสร้างโฟลเดอร์

```text
src/ncdqa/        โค้ดหลัก (retrieval/, rag/, eval/, llm/)        configs/        ค่าตั้งที่ freeze
scripts/          สคริปต์รัน/ประเมิน/สร้างข้อมูล                  tests/          เทสต์
runs/             ผลสรุปที่ขึ้น git (ไม่มีข้อความเอกสาร)           docs/           เอกสารอธิบายและบันทึกการทดลอง
data/             metadata และ schema (ข้อความเอกสาร/ดัชนีอยู่ในเครื่อง ไม่ขึ้น git)
NCD - 0Protocol/, NCD - 1Orchestra/, agents/, board.md, plan.md, PROGRESS.md, HANDOFF.md   เอกสารกระบวนการทำงานของทีม (ช่วง corpus preparation)
```

สารบัญเอกสารทั้งหมดอ่านที่ [`docs/README.md`](docs/README.md) · เอกสารกระบวนการ corpus/Track A: [`docs/corpus_process_record.md`](docs/corpus_process_record.md), [`docs/download_pipeline.md`](docs/download_pipeline.md), [`docs/corpus_policy.md`](docs/corpus_policy.md) · Track B: [`docs/retrieval_process_record.md`](docs/retrieval_process_record.md)

เจ้าของ repository: `Chaiporn2005` · Visibility: Private
