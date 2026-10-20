# คู่มือเตรียมเครื่อง Mac เพื่อรัน demo (ใช้ Typhoon API เป็น LLM)

เป้าหมาย: รัน `demo.py` บน Mac (Apple Silicon หรือ Intel) ให้ถามคำถามแล้วได้คำตอบพร้อม citation หรือการงดตอบ
ใช้ Typhoon (`typhoon-v2.5-30b-a3b-instruct`) เป็นตัวสร้างคำตอบเท่านั้น ส่วน retrieval (bge-m3 + BM25) รันในเครื่อง ไม่ใช้ GPU
เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำทางการแพทย์

ขั้นที่ 1–3 ทำได้ทันทีจากรีโปนี้ ขั้นที่ 5 ต้องมีไฟล์ดัชนีที่ **ไม่อยู่ใน git** (ขั้นที่ 4) ถ้าไม่มี demo จะหยุดที่ `FileNotFoundError: data/index/chunks-v12-t512/chunks.jsonl`

## 1. ติดตั้ง Python 3.12 และ dependency
requirements ล็อกเวอร์ชันที่ต้องใช้ Python ≥ 3.10 (Python 3.9 ของ Command Line Tools ใช้ไม่ได้) วิธีที่ใช้ได้โดยไม่ต้องมี Homebrew คือ uv

```bash
python3 -m pip install --user uv            # หรือ brew install uv ถ้ามี Homebrew
export PATH="$HOME/Library/Python/3.9/bin:$PATH"   # ที่อยู่ของ uv จาก pip --user (ปรับเลขเวอร์ชันตาม python3 ของคุณ)
uv venv --python 3.12 .venv                 # uv ดาวน์โหลด Python 3.12 ให้เอง
uv pip install --python .venv/bin/python -r requirements-rag.txt -r requirements-agent.txt sentencepiece
```
ต่างจาก `docs/track_c_reproduce.md` ที่เขียนสำหรับ Windows (`.venv/Scripts/python.exe`): บน Mac ใช้ `.venv/bin/python`
torch บน macOS จาก PyPI ใช้งาน CPU ได้เลย ไม่ต้องใส่ `--index-url`
ครั้งแรกที่รัน demo จะดาวน์โหลดโมเดล `BAAI/bge-m3` (ประมาณ 2.3 GB) ไปที่ `~/.cache/huggingface`

## 2. ตั้งค่า Typhoon API
1. สมัครและสร้าง API key ที่ Typhoon (opentyphoon.ai) ด้วยบัญชีของคุณเอง
2. สร้างไฟล์ `.env` ที่รากรีโป (ถูก `.gitignore` ไว้แล้ว) **ใส่คีย์ในไฟล์นี้เท่านั้น อย่าวางลงแชต เอกสาร หรือคอมมิต**
   ```bash
   cp .env.example .env
   # เปิด .env แล้วกรอกบรรทัด TYPHOON_API_KEY=...  (ช่องอื่นเว้นว่างได้ demo ใช้เฉพาะ TYPHOON_API_KEY)
   ```
3. สร้างไฟล์ provider (ก็ถูก `.gitignore` ไว้): `cp configs/llm/providers.example.yaml configs/llm/providers.yaml`
   `demo.py` อ่าน provider `typhoon_api` ที่ `configs/rag/generate_v1.json` (base URL `https://api.opentyphoon.ai/v1`, temperature 0)
4. ตรวจว่าคีย์ใช้ได้และ model id ตรงกับที่บัญชีของคุณเรียกได้ (ไม่พิมพ์คีย์ออกมา):
   ```bash
   .venv/bin/python -X utf8 scripts/check_llm_env.py                          # บอกแค่ว่าตัวแปรถูกตั้งหรือไม่
   .venv/bin/python -X utf8 scripts/check_llm_env.py --list-models            # รายการ model id ที่คีย์นี้ใช้ได้
   .venv/bin/python -X utf8 scripts/check_llm_env.py --ping --provider typhoon_api
   ```
   ในไฟล์ example ระบุว่า base URL ของ Typhoon ยังเป็นค่าที่ "ไม่ยืนยัน" ถ้า `--list-models` ไม่ตอบหรือไม่เห็น `typhoon-v2.5-30b-a3b-instruct`
   ให้แก้ `base_url` / `model` ใน `configs/llm/providers.yaml` (ไฟล์ในเครื่อง) ตามที่ API ตอบ **อย่าแก้ `configs/rag/frozen_v1.json`** เพราะเป็นค่าที่ freeze แล้ว

ทุกคำขอ LLM ถูกแคชใน `data/index/llm_cache/` (ถามคำถามเดิมซ้ำจะไม่เสียโทเคนเพิ่ม) ไม่มีการอนุมัติงบ API แบบเสียเงินสำหรับโปรเจกต์นี้ ใช้เท่าที่ quota ของบัญชีตัวเองให้

## 3. ตรวจโค้ดโดยไม่ต้องใช้ดัชนีหรือคีย์
```bash
.venv/bin/python -X utf8 -m unittest tests.test_rag_pipeline tests.test_rag_graph tests.test_guardrail_eval tests.test_eval_metrics
```
ผลที่ได้บนเครื่องนี้: 66 เทสต์ผ่าน (นี่ตรวจโค้ด pipeline/guard/metric ไม่ได้ตรวจคำตอบจริงหรือการเชื่อมต่อ Typhoon)

## 4. ไฟล์ที่ demo ต้องมี (ไม่อยู่ใน git)
`configs/retrieval/serve_v1.json` ชี้ไปที่ 3 โฟลเดอร์นี้ (มีข้อความเอกสาร จึงถูก ignore ทั้ง `data/index/`):

| โฟลเดอร์ | ใช้ทำอะไร |
|---|---|
| `data/index/chunks-v12-t512/` | chunk แม่ที่ส่งเป็นหลักฐานให้ LLM (`chunks.jsonl`) |
| `data/index/chunks-v12-t128/` | chunk ลูกที่ใช้จับคู่กับ dense |
| `data/index/dense-bge-m3-t128-v12/` | เวกเตอร์ bge-m3 |

**ขอจากเจ้าของ Track B** เป็นบันเดิล `ncd_demo_bundle` (มี `BUNDLE_MANIFEST.json` พร้อม SHA-256 ของทุกไฟล์ และโฟลเดอร์ `data/index/` ที่มีครบทั้งสามชุดข้างบน) แล้วคัดลอกเข้ารีโป:
```bash
B=~/Downloads/ncd_demo_bundle        # ปรับตามที่วางบันเดิล
mkdir -p data/index/llm_cache
cp -R "$B"/data/index/chunks-v12-t128 "$B"/data/index/chunks-v12-t512 "$B"/data/index/dense-bge-m3-t128-v12 data/index/
cp "$B"/data/index/llm_cache/demo/typhoon_api.jsonl data/index/llm_cache/typhoon_api.jsonl   # ไม่บังคับ: แคชคำตอบที่บันทึกไว้ ถามคำถามเดิมซ้ำโดยไม่เสียโทเคน
```
ตรวจบันเดิลก่อนใช้: ทุกไฟล์ตรงกับ SHA-256 ใน manifest, เวกเตอร์ 23,819 × 1024 ตรงกับ `chunk_ids.json` และ `chunks-v12-t128` ทั้งจำนวนและลำดับ, `chunks-v12-t512` มี 4,347 chunks จาก 66 เอกสาร (corpus v12)
ชื่อโฟลเดอร์แคชในบันเดิลคือ `llm_cache/demo/` แต่ demo อ่านที่ `data/index/llm_cache/typhoon_api.jsonl` จึงต้องคัดลอกเป็นชื่อนี้ตามคำสั่งข้างบน
ห้ามขึ้น git: ข้อมูลมีข้อความเอกสารรวมแผ่นพับ Siriraj ที่ใช้ภายในทีมเท่านั้น (Decision 0008); `data/index/` ถูก `.gitignore` ไว้แล้ว

ถ้าไม่มีบันเดิล สร้างใหม่เองบนเครื่องนี้ไม่ได้ในสภาพปัจจุบัน: ดัชนีเป็นของ corpus v12 แต่ในรีโปมี `data/processed/normalized-v*` เฉพาะ `normalization.json` ไม่มี `pages.jsonl` (ถูก ignore) ต้องรัน extract/OCR/normalize ใหม่ก่อนจึงจะรัน `scripts/build_chunks.py` และ `scripts/splice_index.py` ได้ และผลอาจไม่ตรงกับ v12 ที่ freeze ไว้

## 5. รัน demo
```bash
.venv/bin/python -X utf8 demo.py "ค่าเป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร"
.venv/bin/python -X utf8 demo.py                       # โหมดโต้ตอบ (บรรทัดว่างเพื่อออก)
.venv/bin/python -X utf8 demo.py "..." --show-evidence # แสดงข้อความ chunk ที่ส่งให้โมเดลด้วย
.venv/bin/python -X utf8 demo.py "..." --graph         # เวอร์ชัน LangGraph (ลองใหม่ได้หนึ่งครั้งถ้าโมเดลตอบรูปแบบเสีย)
.venv/bin/python -X utf8 demo.py "..." --variant A     # A dense / B hybrid (ค่าเริ่มต้น) / C + reranker (ช้ามากบน CPU)
```
เริ่มครั้งแรกใช้เวลาโหลดโมเดลประมาณ 20 วินาทีบน CPU; ถามครั้งถัดไปในโหมดโต้ตอบเร็วกว่ามาก
ทดสอบแล้วบน Mac (Apple Silicon, 2026-10-20) กับ Typhoon จริง: โหมดปกติ (variant B), `--graph`, `--variant A --show-evidence` และโหมดโต้ตอบ ตอบได้พร้อม citation; `--variant C` ยังไม่ได้ทดสอบ
demo บันทึกเฉพาะ metadata (ไม่มีข้อความคำถาม/คำตอบ) ที่ `data/index/demo_log/metadata.jsonl` ปิดได้ด้วย `--no-log`
ข้อมูลส่วนตัวในคำถามถูกปิดบังก่อนส่งไป Typhoon (G1 = B) แต่ข้อความคำถามที่เหลือถูกส่งไปที่ API ของ Typhoon จริง อย่าพิมพ์ข้อมูลผู้ป่วยจริง

## ปัญหาที่พบบ่อย
| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| `FileNotFoundError: ...chunks-v12-t512/chunks.jsonl` | ยังไม่มีดัชนี ดูหัวข้อ 4 |
| `เรียกโมเดลไม่สำเร็จ (ตรวจ TYPHOON_API_KEY และเครือข่าย)` | ไม่ได้ตั้งคีย์ใน `.env`, คีย์ผิด, quota หมด หรือ `base_url`/`model` ใน `providers.yaml` ไม่ตรง รัน `check_llm_env.py --ping` |
| `FileNotFoundError: configs/llm/providers.yaml` | ยังไม่ได้ทำขั้น 2.3 |
| `ModuleNotFoundError` หรือ pip หาเวอร์ชันไม่เจอ | ใช้ Python 3.9 อยู่ ให้ใช้ `.venv/bin/python` ที่สร้างด้วย uv |
| ตัวอักษรไทยเพี้ยนใน Terminal | ใช้ `python -X utf8` ตามตัวอย่างและตั้ง Terminal เป็น UTF-8 |
