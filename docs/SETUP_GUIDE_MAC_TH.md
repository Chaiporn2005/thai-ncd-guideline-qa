# คู่มือติดตั้งและเปิดเดโมบน Mac — Thai NCD Guideline Q&A (ฮูกไกด์)

> **สถานะ:** หน้าเว็บใหม่ (`--web`) **ยังไม่ได้ทดสอบบน Mac** คู่มือนี้เขียนจากการตรวจโค้ดว่าใช้ได้ข้ามระบบ และจากการทดสอบขั้นเดียวกันทั้งหมดบน Windows ในโฟลเดอร์ใหม่ (2026-10-19, ไม่มีคีย์ API, โหมดออฟไลน์) ส่วน**โหมดบรรทัดคำสั่ง (CLI) ทดสอบบน Mac Apple Silicon จริงแล้วโดยเพื่อนร่วมทีม (2026-10-20, Typhoon API จริง)** ดูหัวข้อ "ผลที่เพื่อนทดสอบบน Mac" ท้ายไฟล์ ถ้าเจอปัญหา ให้จดข้อความที่ขึ้นทั้งบรรทัดแล้วส่งให้เจ้าของทีม และกรอกตาราง "ผลทดสอบบน Mac" ท้ายไฟล์
> คู่มือ Windows: [`SETUP_GUIDE_TH.md`](SETUP_GUIDE_TH.md)

**เวลาโดยประมาณ:** ครั้งแรก 20–40 นาที (ส่วนใหญ่คือดาวน์โหลดแพ็กเกจราว 1–2 GB และโมเดล bge-m3 ราว 2.3 GB) ครั้งต่อไปเปิดได้ในไม่กี่นาที

## ขั้น 0 ตรวจเครื่องก่อน (สำคัญที่สุด)

**ต้องเป็น Mac ชิป Apple (M1 ขึ้นไป รวม M5)** ตรวจด้วยคำสั่งนี้ใน Terminal (เปิดด้วย ⌘ + Space พิมพ์ `Terminal`):
```bash
uname -m
```
- ขึ้น `arm64` = ใช้ได้ ทำต่อ
- ขึ้น `x86_64` = Mac ชิป Intel **ติดตั้งไม่ได้** เพราะ PyTorch รุ่นที่โปรเจกต์ใช้ (2.14.1) ไม่มีให้ Mac Intel แล้ว ให้ใช้เครื่อง Windows หรือเครื่อง Mac ชิป Apple ของเพื่อนแทน

| ต้องมี | หมายเหตุ |
|---|---|
| RAM 8 GB ขึ้นไป (แนะนำ 16 GB) | โมเดลค้นคืนใช้หน่วยความจำหลาย GB ปิดโปรแกรมหนักอื่นก่อนเปิดเดโม |
| พื้นที่ว่าง ~6 GB | แพ็กเกจ + โมเดล + ข้อมูล |
| สิทธิ์เข้า GitHub repo `Chaiporn2005/thai-ncd-guideline-qa` (Private) | ขอเจ้าของ repo เชิญเป็น collaborator |
| ไฟล์ `ncd_demo_bundle.zip` (63.4 MB, ชุดวันที่ 2026-10-19) | จาก Drive ของทีม: https://drive.google.com/file/d/1bymLN9NMlyGG6Mb3bjHWC8n2Gt3wXW5D/view?usp=sharing (เปิดไม่ได้ให้ขอสิทธิ์จากเจ้าของทีม) **ห้ามส่งต่อนอกทีม** (มีข้อความเอกสาร รวมแผ่นพับศิริราช) |
| คีย์ `TYPHOON_API_KEY` (ไม่บังคับ) | ขอเจ้าของทีมทางแชตส่วนตัว ไม่มีคีย์ก็ใช้คำถามแนะนำและชุดทดสอบ 11 ข้อได้ แต่คำถามใหม่ที่พิมพ์เองต้องมีคีย์ |
| อินเทอร์เน็ต | ครั้งแรกต้องใช้ คำถามใหม่ต้องใช้เน็ตเรียก API |

## ขั้น 1 ติดตั้ง git และ uv (ครั้งเดียว)
**git:** พิมพ์ `git --version` ถ้า Mac ถามให้ติดตั้ง "command line developer tools" ให้กด Install แล้วรอจนเสร็จ (หลายนาที) จากนั้นพิมพ์ `git --version` อีกครั้ง ต้องขึ้นเลขเวอร์ชัน
```bash
git --version
```
**uv** (ตัวจัดการ Python ไม่ต้องติดตั้ง Python เอง):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
แล้ว **ปิด Terminal และเปิดใหม่** (หรือพิมพ์ `source $HOME/.local/bin/env`) จากนั้นตรวจ:
```bash
uv --version
```
ถ้าขึ้น `zsh: command not found: uv` แปลว่ายังไม่ได้เปิด Terminal ใหม่

## ขั้น 2 ดาวน์โหลดโค้ด
```bash
cd ~/Desktop
```
```bash
git clone -b rag/track-b-l1 https://github.com/Chaiporn2005/thai-ncd-guideline-qa
```
```bash
cd thai-ncd-guideline-qa
```
ถ้าถูกถามรหัสผ่าน GitHub: GitHub ไม่รับรหัสผ่านบัญชีแล้ว ต้องใช้ Personal Access Token (Settings → Developer settings → Personal access tokens) หรือติดตั้ง GitHub Desktop / `gh auth login` ถ้าขึ้น `Repository not found` = ยังไม่ได้รับเชิญ ล็อกอินผิดบัญชี หรือพิมพ์ URL ผิด

## ขั้น 3 สร้างสภาพแวดล้อม Python 3.12 และติดตั้งแพ็กเกจ
```bash
uv venv --python 3.12 .venv
```
```bash
source .venv/bin/activate
```
หน้าบรรทัดคำสั่งจะมี `(.venv)` นำหน้า **ทุกครั้งที่เปิด Terminal ใหม่ ต้อง `cd` เข้าโฟลเดอร์แล้วรัน `source .venv/bin/activate` ใหม่**
```bash
uv pip install -r requirements-rag.txt -r requirements-agent.txt
```
ครั้งแรกใช้เวลาหลายนาที (torch ใหญ่) ถ้าหยุดกลางทางให้รันซ้ำได้ ถ้าขึ้น `No solution found` หรือ `torch==2.14.1 ... no wheels` แทบแน่นอนว่าเป็น Mac ชิป Intel (ดูขั้น 0)

## ขั้น 4 ติดตั้งชุดข้อมูล (bundle)

> **ไม่ต้องไปเอาโฟลเดอร์ `data/index/...` (ดัชนีของ Track B) จากที่อื่น** มีครบใน zip นี้แล้ว (`chunks-v12-t512`, `chunks-v12-t128`, `dense-bge-m3-t128-v12` และแคชคำตอบ) ให้ติดตั้งด้วยสคริปต์ในขั้นนี้เท่านั้น **อย่าแตก zip เองแล้วลากโฟลเดอร์ไปวาง** (สคริปต์ตรวจ checksum ให้) คำแนะนำสร้างดัชนีใน `HANDOFF.md` ไว้สำหรับคนที่สร้างดัชนีเอง ไม่ต้องทำตาม

1. ดาวน์โหลด `ncd_demo_bundle.zip` จาก Drive: https://drive.google.com/file/d/1bymLN9NMlyGG6Mb3bjHWC8n2Gt3wXW5D/view?usp=sharing (ถ้าหน้า Google Drive ขึ้น **"Virus scan warning" / "Google Drive can't scan this file for viruses"** เป็นเรื่องปกติของไฟล์ zip ขนาดนี้ ให้กด **"Download anyway"** (ไฟล์นี้เราสร้างเอง ตรวจความถูกต้องด้วย SHA256 ในขั้นถัดไป)) แล้ว **ย้ายไฟล์มาไว้ในโฟลเดอร์ `thai-ncd-guideline-qa`** (โฟลเดอร์เดียวกับ `demo.py`)
   - **ระวัง Safari:** Safari อาจแตกไฟล์ zip ให้อัตโนมัติจนเหลือแต่โฟลเดอร์ ซึ่งใช้ไม่ได้ ให้ดาวน์โหลดด้วย Chrome หรือปิด Safari → Settings → General → "Open safe files after downloading" แล้วโหลดใหม่ ต้องเห็นไฟล์ชื่อ `ncd_demo_bundle.zip` ไม่ใช่โฟลเดอร์
   - ถ้าย้ายด้วย Finder ไม่ถนัด: `mv ~/Downloads/ncd_demo_bundle.zip .`
2. ตรวจว่าไฟล์ไม่เสียหาย:
```bash
shasum -a 256 ncd_demo_bundle.zip
```
   ต้องขึ้นค่านี้ (ชุดวันที่ 2026-10-19) **ถ้าไม่ตรง ให้หยุด** แล้วโหลดใหม่หรือถามเจ้าของทีม:
   `d8cd67587066a773d03b455a1d76ee54a82c63e34b7d2e6ca87d2f32517d24fc`
3. ติดตั้ง:
```bash
python -X utf8 scripts/install_demo_bundle.py ncd_demo_bundle.zip
```
   ผลที่ถูกต้อง: `installed 9 files, skipped 0 existing; checksum mismatches: 0`
   ถ้าเคยติดตั้งชุดเดิมแล้ว จะขึ้น `checksum mismatches: 1` ให้รันคำสั่งเดิมต่อท้าย ` --force` เพื่อทับแคชคำตอบเดิม

## ขั้น 5 ค่าตั้งและคีย์
```bash
cp configs/llm/providers.example.yaml configs/llm/providers.yaml
```
```bash
[ -f .env ] || cp .env.example .env
```
(คำสั่งที่สองสร้าง `.env` เฉพาะเมื่อยังไม่มี ไม่ทับคีย์ที่ใส่ไว้แล้ว)
**ถ้ามีคีย์:** เปิดไฟล์ด้วย nano (อย่าใช้ TextEdit เพราะอาจเปลี่ยนเครื่องหมายหรือบันทึกเป็น rich text):
```bash
nano .env
```
เลื่อนไปบรรทัด `TYPHOON_API_KEY=` วางคีย์ต่อท้าย `=` (ไม่มีช่องว่าง ไม่มีเครื่องหมายคำพูด) กด Control+O, Enter เพื่อบันทึก แล้ว Control+X เพื่อออก
ตรวจโดยไม่แสดงคีย์:
```bash
grep -q '^TYPHOON_API_KEY=.' .env && echo "มีค่าแล้ว" || echo "ยังว่าง"
```
`.env` ไม่ถูก git ติดตาม (`git status` ต้องไม่เห็น `.env`) **อย่าถ่ายภาพหน้าจอตอนที่คีย์แสดงอยู่**

## ขั้น 6 ตรวจเครื่องด้วยคำสั่งเดียว
```bash
python -X utf8 demo.py --check
```
`[OK]` = ผ่าน, `[!!]` = ขาด พร้อมบรรทัด `fix:` บอกวิธีแก้ ต้องจบด้วย `READY to run the demo.` (ถ้าไม่ได้ใส่คีย์ บรรทัด `TYPHOON_API_KEY` จะเป็น `[!!]` แต่ยัง READY ได้)

## ขั้น 7 อุ่นเครื่อง (ครั้งแรกจะดาวน์โหลดโมเดล ~2.3 GB)
```bash
python -X utf8 demo.py --warm
```
ต้องเห็น `[1]` ถึง `[11]` ครบ ผลที่ได้บน Windows ในโฟลเดอร์ใหม่ (ไม่มีคีย์) คือ:
[1]–[5] `answered` · [6] `abstained_model` (งดตอบ) · [7] [8] [10] `refused_input` (ขอสั่งยา, ฉุกเฉิน, injection) · [9] `answered` (ปิดบังชื่อและเบอร์ก่อนตอบ) · [11] `answered` (จุดอ่อนที่ทราบ: ตอบด้วยเกณฑ์ผู้ป่วยไตทั่วไปทั้งที่ถามเรื่องหญิงตั้งครรภ์)
ข้อความ `You are sending unauthenticated requests to the HF Hub` และแถบ `Loading weights` ไม่ใช่ข้อผิดพลาด

## ขั้น 8 เปิดเดโม
```bash
python -X utf8 demo.py --web
```
เมื่อขึ้น `เปิดเบราว์เซอร์ที่ http://127.0.0.1:8780` ให้เปิด Terminal อีกแท็บ (⌘ + T) หรือเปิดเบราว์เซอร์เอง:
```bash
open "http://127.0.0.1:8780/?theme=light"
```
วิธีใช้หน้าเว็บ:
- **พิมพ์คำถามเอง** ในช่องด้านล่าง กด Enter (Shift+Enter = ขึ้นบรรทัดใหม่) ระหว่างรอ ปุ่มจะเป็น "ยกเลิก"
- **คำถามแนะนำ** บนหน้าแรก หรือปุ่ม "ตัวอย่าง" → แท็บ "ชุดทดสอบระบบ" สำหรับดูการปฏิเสธ การปิดบังข้อมูลส่วนบุคคล และ injection
- **⚙ ตั้งค่า:** เลือกวิธีหาหลักฐาน (A/B/C) และวิธีควบคุมขั้นตอน (คงที่/LangGraph/ReAct) พร้อมเวลาที่วัดจริง C ช้ามากบน CPU (ครั้งแรกราว 3 นาที)
- **ดูว่าระบบตอบอย่างไร** ใต้คำตอบ: เส้นทางผ่าน 5 ขั้น (กด "เล่นซ้ำ") และหลักฐานที่ส่งให้โมเดล
- ปิดเซิร์ฟเวอร์: กลับไปหน้าต่างที่รัน แล้วกด Control+C

บรรทัดคำสั่ง (ไม่ต้องเปิดเว็บ):
```bash
python -X utf8 demo.py "ผู้ป่วยโรคไตเรื้อรังระยะ 3 ควรใช้ยา metformin ขนาดเท่าไร"
```

**ตอนนำเสนอถ้าเน็ตไม่แน่นอน** (หลังโหลดโมเดลแล้ว) ตั้งค่านี้ในหน้าต่างเดียวกันก่อนรัน `demo.py`:
```bash
export HF_HUB_OFFLINE=1
```

## ปัญหาที่พบบ่อยบน Mac
| อาการ | สาเหตุที่อาจเป็น | แก้ |
|---|---|---|
| `uname -m` ขึ้น `x86_64` หรือติดตั้ง torch ไม่ได้ | Mac ชิป Intel | ใช้เครื่องอื่น (ขั้น 0) |
| `zsh: command not found: uv` | ยังไม่เปิด Terminal ใหม่หลังติดตั้ง uv | เปิด Terminal ใหม่ หรือ `source $HOME/.local/bin/env` |
| `ModuleNotFoundError` | ยังไม่ `source .venv/bin/activate` ในหน้าต่างนี้ | ขั้น 3 |
| `[!!] local data bundle ... missing` หรือมีแต่โฟลเดอร์ ไม่มีไฟล์ zip | Safari แตก zip อัตโนมัติ หรือวางไฟล์ผิดโฟลเดอร์ | ขั้น 4 |
| `checksum mismatches` ไม่ใช่ 0 / SHA256 ไม่ตรง | ไฟล์ไม่ใช่ชุดล่าสุดหรือเสียหาย | โหลดใหม่ ถามเจ้าของทีมว่าชุดล่าสุดค่าอะไร |
| `Address already in use` | พอร์ต 8780 ถูกใช้ (เช่นเปิดเซิร์ฟเวอร์ค้างไว้) | `python -X utf8 demo.py --web --port 8790` แล้วเปิดพอร์ตนั้น หรือดูว่าใครใช้: `lsof -i :8780` |
| macOS ถามว่า "Allow incoming network connections" | Firewall ของ Mac | กด Allow ได้ (เซิร์ฟเวอร์เปิดเฉพาะ 127.0.0.1 ในเครื่องนี้) หรือ Deny ก็ยังใช้ในเครื่องได้ |
| `เรียกโมเดลไม่สำเร็จ (ตรวจ TYPHOON_API_KEY และเครือข่าย)` | ไม่มีคีย์ คีย์ผิด หรือไม่มีเน็ต | ขั้น 5; คำถามแนะนำและชุดทดสอบยังใช้ได้ |
| เครื่องร้อน/ช้ามากตอนเลือก C + reranker | reranker รันบน CPU | ใช้ B hybrid (ค่าเริ่มต้น) |
| ฟอนต์บนหน้าเว็บดูต่างจากของเพื่อน | ไม่มีเน็ตโหลด Google Fonts ระบบจึงใช้ฟอนต์ไทยของ Mac (Sukhumvit Set/Thonburi) | ไม่ใช่ข้อผิดพลาด |

## ผลที่เพื่อนทดสอบบน Mac จริง (2026-10-20, Mac Apple Silicon, Python 3.12 ผ่าน uv, Typhoon API จริง)
ทดสอบกับโค้ด**รุ่นเก่าที่ยังเป็น CLI** (ก่อนมีหน้าเว็บ) บันทึกเต็มอยู่ใน `board.md`, `HANDOFF.md` และ `AI_AUDIT.md` หัวข้อ Demo บน Mac:
- ตรวจ bundle: SHA-256 ตรง manifest ทั้ง 9 ไฟล์ · เวกเตอร์ 23,819 × 1024 ตรงกับ `chunk_ids.json` และ `chunks-v12-t128` ทั้งจำนวนและลำดับ
- Typhoon (`typhoon-v2.5-30b-a3b-instruct`): `--list-models` HTTP 200, `--ping` ตอบ · เทสต์หน่วย 66 ตัวผ่าน
- `demo.py` โหมดปกติ (B), `--graph`, `--variant A --show-evidence` และโหมดโต้ตอบ ตอบพร้อม citation
- **ยังไม่ได้ทดสอบบน Mac:** หน้าเว็บ `--web`, `--variant C` (reranker), ความถูกต้องทางคลินิกของคำตอบตัวอย่าง

**สิ่งที่เพื่อนเจอจริง และคู่มือนี้เพิ่มให้แล้ว:**
- **คีย์ใน `.env` มีอักษรไทยติดท้าย 1 ตัว** ทำให้ส่งคำขอไม่ได้ (header ผิด) ให้ตรวจว่าท้ายบรรทัด `TYPHOON_API_KEY=` ไม่มีอักขระแปลกปลอม แล้วใช้คำสั่งตรวจนี้ (ไม่พิมพ์คีย์ออกมา ต้องอยู่ใน venv):
```bash
python -X utf8 scripts/check_llm_env.py --list-models
```
```bash
python -X utf8 scripts/check_llm_env.py --ping --provider typhoon_api
```
  ผลที่ดี: `--list-models` ขึ้น HTTP 200 และ `--ping` ตอบกลับ
- **ถ้า `python3` ของ Mac เป็น 3.9** (จาก Command Line Tools) ใช้ไม่ได้ แพ็กเกจต้องการ Python ≥ 3.10 คู่มือนี้จึงให้ uv โหลด 3.12 ให้ และสั่งผ่าน `.venv` เสมอ
- ถ้ามีข้อความเกี่ยวกับ `sentencepiece` ตอนโหลดโมเดล ให้ลง `uv pip install sentencepiece` (เพื่อนลงเพิ่มไว้ตั้งแต่แรก; บน Windows ติดมากับแพ็กเกจอื่นอยู่แล้ว)
- ทดสอบโค้ดโดยไม่ต้องมีดัชนีหรือคีย์: `python -X utf8 -m unittest tests.test_rag_pipeline tests.test_rag_graph tests.test_guardrail_eval tests.test_eval_metrics` (ที่เพื่อนได้: 66 ตัวผ่าน)
- **ความปลอดภัยของคีย์:** อย่าให้คีย์ปรากฏใน diff หรือผลคำสั่ง (เคยเกิดขึ้นแล้วระหว่างทดสอบ ต้อง rotate คีย์) `.env.example` ต้องว่างเสมอ ใส่คีย์ใน `.env` เท่านั้น

## ผลทดสอบหน้าเว็บบน Mac (ให้คนที่ทำตามกรอก แล้ว commit หรือส่งให้เจ้าของทีม)
| ข้อ | ผล (ผ่าน/ไม่ผ่าน + ข้อความถ้าไม่ผ่าน) |
|---|---|
| รุ่นเครื่อง / ชิป / macOS / RAM | `[FILL IN]` |
| ขั้น 3 ติดตั้งแพ็กเกจ | `[FILL IN]` |
| ขั้น 4 SHA256 และ `checksum mismatches: 0` | `[FILL IN]` |
| ขั้น 6 `READY` | `[FILL IN]` |
| ขั้น 7 สถานะ [1]–[11] ตรงกับที่เขียนไว้ | `[FILL IN]` |
| ขั้น 8 หน้าเว็บเปิดได้ ถามคำถามแนะนำได้ | `[FILL IN]` |
| พิมพ์คำถามเองได้ (ต้องมีคีย์) | `[FILL IN]` |
| เวลาโดยประมาณทั้งหมด | `[FILL IN]` |
