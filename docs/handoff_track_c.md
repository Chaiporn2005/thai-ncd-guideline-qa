# ส่งมอบ Track B ให้ Track C (evaluation)

ระบบ retrieval ถึงระดับ L2 ของแผน: Variant A และ B ต่างกันองค์ประกอบเดียว (BM25), ค่า freeze แล้ว (`configs/retrieval/frozen_v1.json`), รัน test แล้วครั้งเดียว, truncation = 0 (ไม่มี chunk เกินลิมิต token), latency CPU วัดแล้ว

## ได้อะไรบ้าง
| สิ่งที่ส่ง | ที่อยู่ | หมายเหตุ |
|---|---|---|
| ฟังก์ชัน `search(query, variant, k, filters)` | `src/ncdqa/retrieval/search.py` (`Retriever`) | A dense / B hybrid (ค่าเริ่มต้น) / C + reranker; คืน hit พร้อม provenance + ข้อความ + `injection_flags`; โหลดครั้งเดียว ~19 วินาที แล้ว ~0.11 วินาที/คำถามบน CPU (A และ B) |
| CLI รันทั้งชุด | `scripts/run_retrieval.py` | A: ไม่ใส่อะไรเพิ่ม; B: `--hybrid ...`; C: `--rerank-scores`; คำสั่งเต็มใน docstring; `--split test` ต้องมี gold ครบและโค้ดที่ commit แล้ว |
| ผลรันที่ freeze | แพ็กเกจ zip (ด้านล่าง) และ metrics + manifest ใน `runs/frozen_v1/` | dev/test × A/B/C; `results.jsonl` ตาม `data/schemas/rag/retrieval_result.schema.json` |
| คำถามและ gold | `questions_all_reviewed.jsonl` ในแพ็กเกจ | 177 แถว: dev gold 106, test gold 56, rejected 15 (ไม่ใช้); schema `question.schema.json`; `alt_evidence` อยู่ในแถวชุดเสริม |
| chunk | `chunks-v12-t512` (หน่วยที่ส่งคืน) และ `chunks-v12-t128` | `text` เป็นข้อความต้นฉบับตรงตัว; `char_start/char_end` ย้อนกลับไปหน้า PDF ได้ |
| ค่าตั้งและวิธีทำซ้ำ | `configs/retrieval/frozen_v1.json`, `serve_v1.json`; `HANDOFF.md`; `docs/hybrid_retrieval_experiment.md` | ที่มาของทุกพารามิเตอร์ |

## ผลที่ C ใช้เทียบได้ทันที (test 52 ข้อที่ตอบได้, bge-m3, corpus v12)
| ระบบ | R@1 | R@5 | R@10 | MRR@10 |
|---|---|---|---|---|
| A dense | 0.462 | 0.808 | 0.827 | 0.618 |
| B hybrid | 0.587 | 0.885 | 0.981 | 0.737 |
| C + reranker (GPU) | 0.615 | 0.913 | 0.952 | 0.771 |

## กติกาที่ต้องใช้ร่วมกัน
- **สูตร metric ใช้โค้ดเดียว:** `src/ncdqa/retrieval/evaluate.py` (Recall@k = สัดส่วนหลักฐานที่เจอใน top-k, Hit@k, MRR@k; กฎ "เกี่ยวข้อง" = ฉบับเดียวกัน + หน้าอยู่ในช่วง + quote ตรงอย่างน้อยครึ่ง) พร้อมแบบ lenient (`docs/lenient_relevance.md`); คำถาม unanswerable ไม่นับใน Recall แต่ใช้ดูคะแนน top-1 สำหรับการงดตอบ; เทียบสองระบบด้วย `paired_bootstrap` (มีตัวอย่างใน `scripts/compare_runs.py`)
- **test ใช้ครั้งเดียวต่อ config ที่ freeze** ห้ามรันซ้ำเพื่อปรับค่า (ผล test ของ A/B/C ใช้ไปแล้ว)
- เทคนิคที่ **ไม่ได้ freeze และไม่ได้รัน test:** doc2query, query rewriting, e5-base, ColBERT/sparse ของ bge-m3 (มีผลบน dev เท่านั้น ห้ามอ้างว่าผ่าน test)
- gold ยืนยันว่า "ตรงกับเอกสาร" ไม่ใช่ความถูกต้องทางคลินิก; test 52 ข้อ ช่วงเชื่อมั่นกว้าง

## ส่วนที่เหลือของ C (ไม่ใช่งาน B)
- metric ของขั้นสร้างคำตอบตามโจทย์ (BERTScore และ RAGAS Faithfulness): ต้องมีคำตอบจาก D ก่อน; ให้ใช้ `answer` ใน gold เป็นอ้างอิง และ `hits[].text` เป็น context; **LLM ที่ใช้ตัดสินได้จริงคือ Typhoon `typhoon-v2.5-30b-a3b-instruct` เท่านั้น** (`src/ncdqa/llm/client.py` แคชทุกคำขอ; ที่ temperature 0 ผลซ้ำตรงกันเพียง ~24% ถ้าไม่แคช; Gemini/GLM ฟรีใช้กับ batch ไม่ได้); เลือกโมเดล BERTScore ภาษาไทยเอง ผมยังไม่ได้ตรวจตัวไหน
- ผล A vs B (หรือ B vs C) เป็น ablation ที่อธิบายกลไกได้: BM25 ช่วยตัวเลข/ศัพท์เฉพาะที่ dense พลาด (ดู `docs/hybrid_retrieval_experiment.md`)

## ข้อควรระวังเรื่องข้อมูล
แพ็กเกจ zip มีข้อความเอกสารรวมแผ่นพับ Siriraj (ใช้ภายในทีมตาม Decision 0008, ห้ามขึ้น git หรือเผยแพร่) และคำถามที่มี quote สั้นจากเอกสาร
