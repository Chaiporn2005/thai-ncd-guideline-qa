# Track C — วิธีทำซ้ำ: ตอบคำถาม + ประเมินคุณภาพคำตอบ + ทดสอบ injection

ทุกขั้นเขียนผลลงโฟลเดอร์ใหม่เสมอ (สคริปต์ไม่เขียนทับ); ผลดิบที่มีข้อความคำถาม/เอกสารอยู่ใน `data/index/runs/` (ไม่ขึ้น git) ผลสรุปตัวเลขอยู่ใน `runs/frozen_gen_v1/`
ค่าตั้งที่ freeze ก่อนรัน test: `configs/rag/frozen_v1.json` (ระบุว่าใครตัดสินแต่ละข้อ); pipeline: `configs/rag/generate_v1.json`

## 0. เตรียมเครื่อง
```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-rag.txt -r requirements-agent.txt sentencepiece
cp .env.example .env     # ใส่ TYPHOON_API_KEY (ตัวสร้างคำตอบ); judge ใช้ CLI ที่ล็อกอินไว้: codex (gpt-5.6-luna) และ/หรือ agy
```
ต้องมีดัชนีในเครื่อง (ไม่อยู่ใน git): `data/index/dense-bge-m3-t128-v12`, `chunks-v12-t128/512` และแพ็กเกจ `data/handoff/track_c_20261012/` (คำถาม gold, อันดับ A/B/C ที่ freeze, chunks) ดูวิธีสร้างใน `HANDOFF.md`
โมเดล BERTScore: bge-m3 (ชุดเดียวกับ retrieval)

## 1. สร้างคำตอบ (Typhoon, แคชทุกคำขอ)
```bash
Q=data/handoff/track_c_20261012/questions_all_reviewed.jsonl
C=data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl
for V in A B C; do
  python -X utf8 scripts/run_generation.py --questions $Q --split dev  --retrieval-results data/handoff/track_c_20261012/results/dev-$V/results.jsonl  --chunks $C \
      --set "llm.cache_dir=\"data/index/llm_cache/gen_$V\"" --out data/index/runs/gen/dev-$V
  python -X utf8 scripts/run_generation.py --questions $Q --split test --retrieval-results data/handoff/track_c_20261012/results/test-$V/results.jsonl --chunks $C \
      --set "llm.cache_dir=\"data/index/llm_cache/gen_test_$V\"" --out data/index/runs/gen/test-$V     # test: รันครั้งเดียวหลัง freeze
done
```
`--pipeline graph` ใช้เวอร์ชัน LangGraph (`src/ncdqa/rag/graph.py`); `--set recover.max_retries=1` เปิดการกู้คำตอบรูปแบบเสีย; รัน test ต้อง gold ครบและไม่มีไฟล์ที่ track แก้ค้าง

## 2. ให้คะแนนคำตอบ (judge: gpt-5.6-luna high ผ่าน codex)
```bash
python -X utf8 scripts/eval_generation.py --answers A=data/index/runs/gen/test-A/answers.jsonl B=data/index/runs/gen/test-B/answers.jsonl C=data/index/runs/gen/test-C/answers.jsonl \
    --chunks $C --validator N7 --judge codex-luna --workers 4 --bert-model BAAI/bge-m3 --bert-layer 8 --idf-questions $Q --out data/index/runs/eval/test_luna_N7
```
`--validator N2|N5|N7` คำนวณซ้ำจากคำตอบดิบ ไม่เรียก LLM; `--judge agy-claude|agy|api` ใช้ judge อื่น (Claude Sonnet 4.6 / Gemini ผ่าน agy ขึ้นกับโควตา); `--no-judge` ข้ามการตัดสิน
ผลแคชของ judge: `data/index/llm_cache/judge_<route>.jsonl` (judge เป็น LLM ไม่ได้ผลซ้ำตรงทุกครั้ง การทำซ้ำใช้แคช)

## 3. เลือก encoder BERTScore และตัวแปรของเมตริก (dev เท่านั้น)
```bash
python -X utf8 scripts/select_bertscore_model.py --per-question data/index/runs/eval/dev_codex-luna/per_question.csv --out data/index/runs/eval/bert_selection_dev.json
python -X utf8 scripts/bertscore_variants.py --dev-eval data/index/runs/eval/dev_p2_N7 --dev-answers A=... B=... C=... --test-answers A=... B=... C=... \
    --test-eval data/index/runs/eval/test_luna_N7 --chunks $C --out data/index/runs/eval/bertscore_variants.json
```

## 4. วิเคราะห์และตรวจ judge
```bash
python -X utf8 scripts/analyze_results.py --eval data/index/runs/eval/test_luna_N7 --out data/index/runs/eval/test_analysis.md     # ตามประเภทคำถาม, กฎตัวเลข, ตัวอย่าง error
python -X utf8 scripts/compare_splits.py --dev data/index/runs/eval/dev_p2_N7 --test data/index/runs/eval/test_luna_N7 --out data/index/runs/eval/dev_vs_test.md
python -X utf8 scripts/validate_judge.py --judge codex-luna --n 48 --out data/index/runs/eval/judge_sanity.json                     # คำตอบที่รู้เฉลยแน่นอน
python -X utf8 scripts/judge_bias.py --eval data/index/runs/eval/test_luna_N7 --answers B=data/index/runs/gen/test-B/answers.jsonl --out data/index/runs/eval/judge_bias.json
python -X utf8 scripts/compare_judges.py --a <per_question.csv ของ judge ตัวหนึ่ง> --b <ของอีกตัว> --names X Y --out <ไฟล์>.json    # ความสอดคล้องข้าม judge
```

## 5. ทดสอบ prompt injection (กฎล้วน ไม่ใช้ LLM ตัดสิน)
```bash
python -X utf8 scripts/build_guardrail_cases.py --questions $Q       # เคสร่างใน data/eval/guardrail/ (reviewed_by = null จนกว่าคนจะตรวจ)
python -X utf8 scripts/eval_guardrails.py --cases data/eval/guardrail/cases.jsonl --questions $Q --out data/index/runs/guard/<ชื่อ>          # N0..N7
python -X utf8 scripts/eval_guardrails.py --cases data/eval/guardrail/cases_adaptive_v2.jsonl --questions $Q --layers N1 N2 N3 N4 N5 N6 N7 --out data/index/runs/guard/<ชื่อ>
```
รายละเอียดชั้น N0–N7: docstring ของ `src/ncdqa/rag/guardrail_eval.py`

## 5b. input guard (กฎ) และ benchmark สาธารณะ
```bash
python -X utf8 scripts/eval_input_guard.py --questions $Q --out data/index/runs/guard/input_guard_silver.json      # ชุด silver + คำถามจริง 162 ข้อ
python -X utf8 scripts/eval_public_benchmarks.py --out data/index/runs/public_benchmarks/run1          # NanoMTEB-Thai + NitiBench (ดาวน์โหลดไป data/external)
python -X utf8 scripts/eval_public_benchmarks.py --out data/index/runs/public_benchmarks/run_med_en --tasks scifact nfcorpus cure_dermatology
python -X utf8 scripts/summarize_public_benchmarks.py --run data/index/runs/public_benchmarks/run1 --out data/index/runs/public_benchmarks/run1_table.md
```
บน GPU (Kaggle T4, 14 ชุดใน ~28 นาที): ดู `infra/kaggle_public_benchmarks/README.md`; ผลที่ได้: `runs/frozen_gen_v1/public_benchmarks/` (มีผล CPU float32 ของชุดไทย 8 ชุดไว้เทียบ)
ชุดข้อมูลสาธารณะอยู่ใน `data/external/` (ไม่ขึ้น git; ใบอนุญาตต่างกัน: CURE v1 เป็น CC-BY-NC-4.0 ใช้เพื่อการศึกษาเท่านั้น)

## 6. รวมผลสรุปเข้า git (ไม่มีข้อความคำถามหรือเอกสาร)
```bash
python -X utf8 scripts/collect_track_c_results.py     # -> runs/frozen_gen_v1/
```

## 7. เดโม
```bash
python -X utf8 demo.py "คำถาม"            # หรือไม่ใส่คำถามเพื่อโหมดโต้ตอบ; --graph, --variant A|B|C, --show-evidence
```

## เทสต์
```bash
python -X utf8 -m unittest tests.test_rag_pipeline tests.test_rag_graph tests.test_guardrail_eval tests.test_eval_metrics
```
(เทสต์เดิมของ Track A/B บางตัวต้องใช้ `PIL` ซึ่งไม่ได้ติดตั้งใน venv นี้ ไม่เกี่ยวกับ Track C)
