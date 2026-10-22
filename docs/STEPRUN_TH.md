# Step run: รันเว็บ demo บน Mac

ทำตามลำดับ คัดลอกคำสั่งไปวางในเทอร์มินัลได้เลย รายละเอียดและวิธีแก้ปัญหาอยู่ที่ [SETUP_GUIDE_MAC_TH.md](SETUP_GUIDE_MAC_TH.md)
เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำทางการแพทย์ ข้อมูลเอกสารในบันเดิลใช้ภายในทีมเท่านั้น (Decision 0008)

## ก่อนเริ่ม ต้องมี
- Mac ที่ต่ออินเทอร์เน็ต (ครั้งแรกดาวน์โหลดโมเดลประมาณ 2.3 GB)
- Typhoon API key ของตัวเอง
- โค้ดของรีโปนี้ (โฟลเดอร์ `NLPJEC`) และ branch `demoUpdate`

## ขั้นตอน

**1. เข้าโฟลเดอร์โปรเจกต์**
```bash
cd "/Users/chaiyaporn/work/งาน/งาน/AI/NLPJEC"      # แก้ path ให้ตรงกับเครื่องคุณ
git switch demoUpdate
```

**2. ติดตั้ง Python 3.12 และ dependency** (ทำครั้งเดียว)
```bash
python3 -m pip install --user uv
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-rag.txt -r requirements-agent.txt sentencepiece
```

**3. ใส่ API key** (ทำครั้งเดียว)
```bash
cp .env.example .env
open -e .env          # กรอกหลัง TYPHOON_API_KEY= แล้วบันทึก (ใช้แป้นพิมพ์ภาษาอังกฤษ)
cp configs/llm/providers.example.yaml configs/llm/providers.yaml
```
ใส่คีย์ใน `.env` เท่านั้น ห้ามใส่ใน `.env.example` ห้ามแชร์หรือ commit ตรวจว่าโค้ดเห็นคีย์:
```bash
.venv/bin/python -X utf8 scripts/check_llm_env.py --ping --provider typhoon_api      # ต้องเห็น answer: 'ok'
```

**4. ดาวน์โหลดและตรวจไฟล์ข้อมูล** (ทำครั้งเดียว)
- ลิงก์ดาวน์โหลดบันเดิล `ncd_demo_bundle` อยู่ที่ [SETUP_GUIDE_MAC_TH.md หัวข้อ 4](SETUP_GUIDE_MAC_TH.md) ดาวน์โหลดแล้วแตก zip ไว้ที่ `~/Downloads/ncd_demo_bundle`
- ตรวจไฟล์ ต้องขึ้น `OK ทุกไฟล์ตรง`:
```bash
python3 - <<'PY'
import hashlib, json, pathlib
b = pathlib.Path.home() / "Downloads/ncd_demo_bundle"
m = json.loads((b / "BUNDLE_MANIFEST.json").read_text())["files"]
bad = [p for p, h in m.items() if hashlib.sha256((b / p).read_bytes()).hexdigest() != h]
print("OK ทุกไฟล์ตรง" if not bad else f"ไม่ตรง: {bad}")
PY
```
- คัดลอกเข้ารีโป:
```bash
B=~/Downloads/ncd_demo_bundle
mkdir -p data/index/llm_cache
cp -R "$B"/data/index/chunks-v12-t128 "$B"/data/index/chunks-v12-t512 "$B"/data/index/dense-bge-m3-t128-v12 data/index/
cp "$B"/data/index/llm_cache/demo/typhoon_api.jsonl data/index/llm_cache/typhoon_api.jsonl
```

**5. เปิดเว็บ** (ทุกครั้งที่ใช้)
```bash
.venv/bin/python -X utf8 app.py
```
ต้องเห็น `เปิดที่ http://127.0.0.1:8000` **ปล่อยเทอร์มินัลนี้ไว้ ห้ามปิด** (ถ้าพอร์ตชน ใช้ `--port 8123`)

**6. เปิดในเบราว์เซอร์**
ไปที่ <http://127.0.0.1:8000> รอ 20 วินาทีจนมุมขวาบนขึ้น "พร้อมใช้งาน" แล้วกดคำถามตัวอย่างหรือพิมพ์คำถามเอง กดป้าย S1, S2 ในคำตอบเพื่อดูข้อความหลักฐาน

**7. ปิด**
กด `Ctrl+C` ในเทอร์มินัลของขั้นที่ 5

## ตรวจว่าทำงานถูกต้อง (ขั้นตอนทดสอบเต็มอยู่ใน SETUP_GUIDE หัวข้อ 6)
- ตัวอย่าง "ค่าเป้าหมาย HbA1c" ได้คำตอบพร้อมแหล่งอ้างอิงอย่างน้อย 1 ข้อ
- ถามคำถามนอกเรื่อง (เช่น วิธีทำต้มยำกุ้ง) ระบบงดตอบ ไม่ตอบนอกเอกสาร
- ถามขอสั่งยาให้ตัวเอง ระบบปฏิเสธ

## ถ้าติดปัญหา
| อาการ | ทำอะไร |
|---|---|
| `FileNotFoundError ... chunks.jsonl` | ยังไม่ได้ทำขั้นที่ 4 |
| `เรียกโมเดลไม่สำเร็จ` หรือ ping ไม่ผ่าน | ตรวจ `.env` ว่ามีคีย์ครบและไม่มีอักษรไทยติดมา; รัน `check_llm_env.py --ping` |
| `Address already in use` | ใช้ `--port 8123` แล้วเปิด `http://127.0.0.1:8123` |
| เปิดเว็บไม่ขึ้น | ต้องรัน `app.py` ทิ้งไว้ และพิมพ์ URL ในเบราว์เซอร์ (ดับเบิลคลิก `web/index.html` ใช้ไม่ได้) |
| ช่องถามกดไม่ได้ | ยังโหลดโมเดลอยู่ รอจนขึ้น "พร้อมใช้งาน"; ถ้าขึ้น "โหลดไม่สำเร็จ" ดูข้อความใน terminal |
