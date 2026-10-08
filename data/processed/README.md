# Normalized text summaries

## normalized-v11 (2026-10-08, **current for retrieval**)

`normalized-v10` (v9 + คนอนุมัติ OCR ใหม่ 90 หน้า พร้อมข้อแก้ 411 จุดจาก Codex) + ทำความสะอาดหนังสือ health literacy:
ตัด footer 525 บรรทัด, โลโก้ 38, ชื่อแถบหมวด 431, เนื้อหา OCR ซ้ำรอบสอง 14 (ทุกบรรทัดเก็บใน `boilerplate_removed` ของหน้านั้น) และบันทึก `category` ของทุกหน้าจากแถบสีเข้มในภาพ (ตรงกับสารบัญ 62/62)
ค้นได้ **67 เอกสาร / 3,749 หน้า**; หน้าที่เหลือว่างหลังตัด (p29) ไม่เข้า index; p71 ยังรอ OCR
รายละเอียด/ข้อจำกัด: [corpus_process_record.md](../../docs/corpus_process_record.md) ข้อ 4.15 · [inventory](../manifests/corpus_normalized-v11_inventory.json) · [บันทึกการตัด](../manifests/booklet_cleanup_normalized-v11.json) · [ผลตรวจแถบ](../manifests/booklet_side_tabs_normalized-v11.json)

```powershell
python -X utf8 scripts/apply_review_decisions.py --source data/processed/normalized-v9 --decisions data/manifests/ocr_review_decisions_reocr-v9_approved.json --reviewer Up2mEz --proposer "Codex CLI gpt-6-astra (medium), supervised by Claude" --out data/processed/normalized-v10
python -X utf8 scripts/side_tab_category.py --images data/agent_runs/20261008-sidebar/img --out data/agent_runs/20261008-sidebar/tabs.json
python -X utf8 scripts/clean_booklet_pages.py --source data/processed/normalized-v10 --tabs data/agent_runs/20261008-sidebar/tabs.json --out data/processed/normalized-v11 --manifest data/manifests/booklet_cleanup_normalized-v11.json
```

(ภาพหน้าสำหรับ `side_tab_category.py` เรนเดอร์ด้วย `pdftoppm -r 110` ทุกหน้า 1–96 ของเอกสาร ลงใน `img/`)

## normalized-v9 (2026-10-08, ตรวจแล้วเป็น v10)

`normalized-v8` + OCR ใหม่ 90 หน้าของ `ncd-ddc-health-literacy-fight-ncds-2566` (ข้อความเดิมเป็นรหัสฟอนต์)
หน้าเหล่านี้เป็น `ocr_unreviewed` ไม่เข้าการค้นจนกว่า Codex เสนอแก้และคนตัดสิน; 1 หน้า (p71) หมดเวลาสองครั้ง ยังรอ OCR
ที่มา/วิธี/ปัญหา: [corpus_process_record.md](../../docs/corpus_process_record.md) ข้อ 4.12–4.13

```powershell
python -X utf8 scripts/ocr_typhoon.py --pages-root data/processed/normalized-v8 --out-dir data/processed/ocr-typhoon-reocr-v8 --needs-ocr-only --shard 0 --num-shards 2 --env-file .env --api-key-env TYPHOON_OCR_API_KEY_A
python -X utf8 scripts/ocr_typhoon.py --pages-root data/processed/normalized-v8 --out-dir data/processed/ocr-typhoon-reocr-v8 --needs-ocr-only --shard 1 --num-shards 2 --env-file .env --api-key-env TYPHOON_OCR_API_KEY_B
python -X utf8 scripts/merge_ocr.py --source data/processed/normalized-v8 --ocr-dir data/processed/ocr-typhoon-reocr-v8 --out data/processed/normalized-v9
```

## normalized-v8 (2026-10-08, ถูกแทนที่ด้วย v11)

**ใช้ชุดนี้สำหรับ Track B** = `normalized-v7` + ผลตัดสินของคนเรื่องป้ายประชากร ข้อมูลส่วนบุคคล และหน้าเนื้อหาน้อย

| รายการ | ผล |
| --- | --- |
| หน้า | 68 เอกสาร / 4,009 หน้า; ค้นได้ **67 เอกสาร / 3,660 หน้า** (v7: 3,873) |
| ป้ายประชากรของหน้าที่ค้นได้ | ทั่วไป 3,533 · เด็ก 73 · ผู้สูงอายุ 19 · ตั้งครรภ์ 10 · ปนกัน 25 (ฟิลด์ `population` ทุกหน้า) |
| หน้าที่ไม่เข้า index (`index_exclusion`) | รอ OCR ใหม่ 91 · ข้อมูลส่วนบุคคล (ตัดหน้า) 46 · แท็กรายชื่อบุคคล (เก็บแต่ไม่ค้น) 20 · ปกหลัง 16 · ปก 16 · ปุ่มนำทาง 10 · หน้าคั่น 7 · เกือบว่าง 7 |
| แทนค่าในที่เดิม | ชื่อ 142, อีเมล 94, เบอร์ 5 และข้อมูลระบุตัวของเคส 4 ค่า (แท็กเช่น `[ชื่อบุคคล]`); หน้าที่แทนค่าหรือตัดจะล้างสำเนาข้อความดิบและเก็บ SHA-256 |
| เบอร์/อีเมลหน่วยงาน | เก็บไว้ค้นได้ครบ 41 ค่าที่ไม่ซ้ำ |
| ตรวจ | ค่าที่เลือกแทนค่าเหลือ 0 ในทุกฟิลด์ · schema 0 error |

**ผู้สร้างโค้ดที่ consume ต้องข้ามหน้าที่มี `index_exclusion` หรือ `status` ไม่ใช่ ok/ผ่านตรวจ** (หน้าที่ข้อความเสียตั้ง `status: garbled` ด้วย)

```powershell
python -X utf8 scripts/amend_page_tag_decisions.py --corpus data/processed/normalized-v7 --decisions data/page_tag_decisions_normalized-v7.json --out data/page_tag_decisions_normalized-v7_final.json
python -X utf8 scripts/apply_page_tags.py --source data/processed/normalized-v7 --decisions data/page_tag_decisions_normalized-v7_final.json --out data/processed/normalized-v8 --manifest data/manifests/page_tags_normalized-v8.json --allow-incomplete
python -X utf8 scripts/write_corpus_inventory.py --corpus data/processed/normalized-v8 --created-by "<ผู้สร้าง/ที่มา>" --out data/manifests/corpus_normalized-v8_inventory.json
```

`--allow-incomplete`: ผู้ตรวจยังไม่ติ๊ก "ตรวจเอกสารนี้เสร็จ" ครบ 13 เอกสาร (ป้ายประชากรมีครบแล้ว)
ไฟล์ export ของผู้ตรวจ (`data/page_tag_decisions_*.json`) มีค่าส่วนบุคคลที่เลือกลบ จึงไม่ขึ้น Git
hash/สถิติอยู่ใน [v8 inventory](../manifests/corpus_normalized-v8_inventory.json)

## normalized-v7 (2026-10-08, ถูกแทนที่ด้วย v8)

**ใช้ชุดนี้สำหรับ Track B** = `normalized-v6` + ผลตรวจหน้า OCR โดยคน (Up2mEz) จากข้อเสนอแก้ของ Codex CLI

| ขั้น | ผล |
| --- | --- |
| Audit รอบ 1 (Codex, เทียบภาพ 161 หน้า) | สุ่ม `pass_auto` 46 หน้า: ถูกต้องครบ 50%, ตัวเลข/เครื่องหมายผิด 11% → ตัดสินว่า `pass_auto` เชื่อถือไม่พอ |
| Audit รอบ 2 (Codex, 283 หน้า) | หน้า `pass_auto` ทั้งหมด + หน้าที่กู้ได้ 7 หน้า; ข้อเสนอแก้ 280 จุด, `old` พบตรง 1 ครั้งทุกจุด |
| คนตรวจ (`review.html`) | ใช้ 255 / ไม่ใช้ 28 หน้า; ยอมรับข้อแก้ 237 จาก 240 จุดบนหน้าที่ใช้ + 1 จุดตามหมายเหตุผู้ตรวจ ([decisions](../manifests/ocr_review_decisions_round2_amended.json)) |
| v7 | 68 เอกสาร / 4,009 หน้า; ใช้ค้นได้ **67 เอกสาร / 3,873 หน้า**; schema 0 error; ไม่มีหน้า `pass_auto` ค้าง |

ตัวอย่างที่แก้: เกณฑ์ "> 126" → "≥ 126" มก./ดล., Insulard → Insulatard, Glipenclamide → Glibenclamide, DDP-4 → DPP-4
หน้า OCR ที่ใช้ค้นได้แยกตามวิธีตรวจ (`human_review.review_method`): คนตรวจข้อเสนอ AI 255, AI เทียบภาพ 63, AI ตามความเสี่ยง 36

```powershell
python -X utf8 scripts/build_ocr_review_page.py --audit-dir data/agent_runs/20261007-codex-audit --pages round2_pages.json --findings round2_findings.jsonl --corpus data/processed/normalized-v6
python -X utf8 scripts/apply_review_decisions.py --source data/processed/normalized-v6 --decisions data/manifests/ocr_review_decisions_round2_amended.json --reviewer Up2mEz --proposer "Codex CLI gpt-6-astra (medium), supervised by Claude" --out data/processed/normalized-v7
```

hash อยู่ใน [v7 inventory](../manifests/corpus_normalized-v7_inventory.json)

## normalized-v6 (2026-10-07)

`normalized-v5` (49 เอกสาร) + 19 เอกสารที่สมาชิกทีมดาวน์โหลดผ่าน browser
(เว็บต้นทางตอบ 403 ต่อสคริปต์; นำเข้าด้วย `scripts/import_manual_downloads.py`)

| ขั้น | ผล |
| --- | --- |
| เลือกดาวน์โหลด | 19 จาก 25 ลิงก์; อีก 6 ทีมไม่ดาวน์โหลดเพราะคุณภาพเนื้อหาต่ำ/OCR ยาก (บันทึกใน manifest) |
| Normalize | 19 เอกสาร / 1,960 หน้า; คู่มือ dmthai 178/205 หน้า garbled |
| OCR (Typhoon, 2 keys) | 335 หน้าเลือก, 334 สำเร็จ; `dm-remission-service-2567` p7 timeout ซ้ำ จึงคงสถานะ degraded (ไม่ใช้) |
| ตรวจ OCR แบบตามความเสี่ยง | [ocr_review_20261007c.json](../manifests/ocr_review_20261007c.json): ตรวจอัตโนมัติทุกหน้า; อ่านเต็ม 51 หน้าเสี่ยง; เทียบภาพหน้าที่มีตัวเลขทางคลินิก/ตารางยา; pass_auto 276, pass_text_only 28, reject 18, fix 5, pass 3 |
| v6 | 68 เอกสาร / 4,009 หน้า; ใช้ค้นได้ **67 เอกสาร**, 3,894 หน้า; page rows ผ่าน schema 0 error |

`pass_auto` = ผ่านตัวตรวจอัตโนมัติ (อัตราคำในพจนานุกรม, ตัวเลขตรง text layer, รูปแบบข้อความที่โมเดลแต่ง, บรรทัดซ้ำ)
แต่ไม่ได้เทียบภาพ — การตรวจเทียบภาพเต็มรอบก่อนพบว่าข้อผิดพลาดร้ายแรงกระจุกในหน้าภาพถ่าย/infographic/แผนผัง
ส่วนหน้าเรียงพิมพ์ปกติตรงกับต้นฉบับ ทีมสุ่มยืนยันเพิ่มได้ก่อนอ้างผล

hash อยู่ใน [v6 inventory](../manifests/corpus_normalized-v6_inventory.json)

## normalized-v5 (2026-10-07)

`normalized-v4` (39 เอกสารเดิม) + 10 เอกสารใหม่จากการค้นเพิ่ม 2026-10-07

| ขั้น | ผล |
| --- | --- |
| v4: ตรวจหน้า OCR ของ v3 ทั้ง 77 หน้าเทียบภาพจริง | [ocr_review_20261007.json](../manifests/ocr_review_20261007.json): pass 18, fix 29, reject 22, pass_text_only 8 |
| เอกสารใหม่ 21 รายการ (scout ตรวจ landing page + PDF) | ดาวน์โหลดได้ 10; อีก 11 ตอบ 403 ต่อสคริปต์ (ต้องดาวน์โหลดด้วย browser) |
| เอกสารใหม่ 10 ไฟล์ | normalize → OCR 10 หน้า → ตรวจเทียบภาพ [ocr_review_20261007b.json](../manifests/ocr_review_20261007b.json) |
| v5 | 49 เอกสาร / 2,049 หน้า; ok 1,774 / ok_minor_issues 133 / OCR ที่ตรวจแล้ว 63 / garbled 24 / empty 55 |
| ใช้ค้นได้ | **48 เอกสาร** (แผ่นพับ CKD infographic ถูก reject); page rows ผ่าน schema 0 error |

```powershell
python -X utf8 scripts/apply_ocr_review.py --source data/processed/normalized-v3 --review data/manifests/ocr_review_20261007.json --out data/processed/normalized-v4
python scripts/normalize_thai.py --cohort data/manifests/corpus_expansion_20261007_local.csv --out-dir data/processed/normalized-add-20261007
python -X utf8 scripts/ocr_typhoon.py --pages-root data/processed/normalized-add-20261007 --out-dir data/processed/ocr-typhoon-add-20261007 --shard 0 --num-shards 2 --env-file .env --api-key-env TYPHOON_OCR_API_KEY_A
python -X utf8 scripts/merge_ocr.py --source data/processed/normalized-add-20261007 --ocr-dir data/processed/ocr-typhoon-add-20261007 --out data/processed/normalized-add-20261007-ocr
python -X utf8 scripts/apply_ocr_review.py --source data/processed/normalized-add-20261007-ocr --review data/manifests/ocr_review_20261007b.json --out data/processed/normalized-add-20261007-reviewed
# normalized-v5 = copy of normalized-v4 + normalized-add-20261007-reviewed document folders
```

**ขอบเขตการตรวจ OCR:** ตรวจโดย AI (Claude) เทียบภาพหน้าจริงทีละหน้าตามคำขอของ Up2mEz;
`human_review.review_method = ai_assisted_visual_check` และ `human_confirmation = null` จนกว่าคนในทีมจะยืนยัน
ข้อผิดพลาดที่แก้มีทั้งคำผิด และข้อความที่โมเดล OCR แต่งขึ้นเองในหน้าภาพถ่าย/infographic
ตัวอย่างสำคัญ: แผ่นพับน้ำตาลต่ำ OCR อ่าน "เครื่องตรวจอัตราการเต้นหัวใจ" แทน "เครื่องตรวจวัดระดับน้ำตาลปลายนิ้ว"

hash อยู่ใน [v5 inventory](../manifests/corpus_normalized-v5_inventory.json)

## normalized-v3 (2026-10-07)

`normalized-v2` + Typhoon OCR ของหน้าที่ติดธง (ทีมตัดสินใช้บริการภายนอกนี้ 2026-10-07; ดู rights queue)

```powershell
python -X utf8 scripts/ocr_typhoon.py --shard 0 --num-shards 2 --env-file .env --api-key-env TYPHOON_OCR_API_KEY_A
python -X utf8 scripts/ocr_typhoon.py --shard 1 --num-shards 2 --env-file .env --api-key-env TYPHOON_OCR_API_KEY_B
python -X utf8 scripts/merge_ocr.py --source data/processed/normalized-v2 --ocr-dir data/processed/ocr-typhoon-v1 --out data/processed/normalized-v3
```

- เลือกหน้า empty (เฉพาะที่มีภาพ) / garbled / degraded = 90 หน้า; ข้ามหน้าว่างจริง 40 หน้า; OCR สำเร็จ 90/90
- รวมเข้า v3: หน้า OCR เป็น `text_source: ocr`, `status: ocr_unreviewed`; ข้อความ PDF เดิมเก็บใน `pre_normalization_text`
- ตัดสิ่งที่โมเดลเขียนเองออกจาก `text`: คำบรรยายภาพ `<figure>` (เก็บแยกใน `ocr_figures`), `<page_number>`, HTML entities
  ไม่แก้ตัวเลข หน่วย เครื่องหมาย หรือคำ
- สถานะหน้า: ok 1,551 / ok_minor_issues 118 / ocr_unreviewed 77 / empty 53; page rows ผ่าน `page_input` schema 0 error
- ใช้ค้นได้ทันที 30 เอกสาร; **ครบ 39 เอกสารเมื่อคนตรวจหน้า `ocr_unreviewed` 77 หน้า**
- ตัวอย่างข้อผิดพลาด OCR ที่พบ: "นักโฆษณาการ" (ควรเป็น นักโภชนาการ), "สิรราช" (ขาดสระ) → ต้องตรวจก่อนใช้

hash อยู่ใน [v3 inventory](../manifests/corpus_normalized-v3_inventory.json)

## normalized-v2 (2026-10-06)

สร้างโดย Track B ด้วย `scripts/normalize_thai.py` (tool 1.0, pypdf 6.10.0, Python 3.12) **ไม่รัน OCR**
จาก PDF 39 ไฟล์ = 30 ไฟล์เดิม + 9 สื่อศูนย์เบาหวานศิริราช (ทีมตัดสินใช้เพื่อการศึกษา 2026-10-06; ดู rights queue)

```powershell
python scripts/fetch_documents.py --run-id <new-run-id> --local-review --links data/agent_runs/20261005-local-prep/verified_links.json --limit 55 --document-id <id> ...
python scripts/normalize_thai.py --cohort data/manifests/corpus_v2_selection.csv --out-dir data/processed/normalized-v2
```

| ตรวจ | ผล |
| --- | --- |
| Hash PDF 39 ไฟล์ เทียบ manifest | ตรง 39/39, 1,799 หน้า, 216.4 MB |
| ทำซ้ำ normalized-v1 (30 ไฟล์, ไม่ OCR) | 10 เอกสารที่ v1 ไม่มี OCR: `pages_jsonl_sha256` ตรงทุกไบต์; 20 เอกสารที่มี OCR: สถานะหน้าที่ไม่ใช่ OCR ตรงทุกหน้า |
| Page rows เทียบ `data/schemas/rag/page_input.schema.json` | 1,799 แถว, 0 error |

สถานะหน้า: ok 1,551 / ok_minor_issues 118 / degraded 30 / garbled 8 / empty 92
เอกสารที่มีหน้า ok/ok_minor_issues ใช้ค้นได้: **30 จาก 39**
9 เอกสารยังไม่มีหน้าที่ใช้ได้ (รอ OCR หรือคนตรวจ): 5 สื่อศิริราชที่เป็นภาพทั้งหน้า
(`dm-siriraj-hypoglycemia-leaflet-undated`, `dm-siriraj-know-diabetes-undated`,
`dm-siriraj-needle-disposal-leaflet-undated`, `dm-siriraj-retinopathy-leaflet-undated`, `lipid-siriraj-diabetes-fat-7`),
`ckd-treatment-leaflet-undated` (ภาพ) และ 3 บทความ sidoctor ที่ garbled
(`lipid-siriraj-stroke-nutrition-1298`, `lipid-siriraj-trans-fat-1380`, `lipid-siriraj-warning-1158`)

hash ของทุกไฟล์อยู่ใน [corpus inventory](../manifests/corpus_normalized-v2_inventory.json)
ใน Git มีเฉพาะ `normalization.json`; `pages.jsonl` อยู่ในเครื่องผู้สร้าง หรือสร้างซ้ำด้วยคำสั่งด้านบน
แล้วเทียบ `pages_jsonl_sha256` กับ inventory

## normalized-v1

ข้อความสำหรับ retrieval อยู่ที่ `normalized-v1/<document_id>/` สร้างด้วย
[normalize_thai.py](../../scripts/normalize_thai.py) จาก PDF ใน `raw/` (30 เอกสาร / 1766 หน้า)

ขึ้น GitHub เฉพาะ `normalization.json` 30 รายการ: hash ต้นทาง, จำนวนหน้า, การซ่อมฟอนต์,
จำนวนกฎที่ใช้ และสถานะรายหน้า (`ok`, `ok_minor_issues`, `degraded`, `garbled`, `ocr_unreviewed`, `empty`)
ไม่มีข้อความเอกสารในไฟล์สรุปเหล่านี้

`pages.jsonl` (ข้อความเต็มรายหน้า) ยังอยู่เฉพาะในเครื่อง รอหลักฐานสิทธิเผยแพร่ซ้ำ
ถ้า clone ใหม่ ให้ดาวน์โหลด PDF ตามช่องทางที่มีสิทธิแล้วรันคำสั่งใน
[normalization pipeline](../../docs/normalization_pipeline.md)
สถานะเป็นเกณฑ์คัดกรองสำหรับ retrieval ไม่ใช่ clinical approval หรือ accepted corpus

ผลสกัดรอบแรก (`<document_id>/extraction.json`, `pages.jsonl` และ `ocr-review-v1/`) ถูกลบเมื่อ 2026-10-06
เพราะฟอนต์ไทยเพี้ยนจนใช้ค้นไม่ได้; สรุปเดิมยังดูได้ใน git history ที่ commit `7c98d8e`
และสร้างใหม่ได้ด้วย [extract_pages.py](../../scripts/extract_pages.py)
ดู [rights queue](../manifests/rights_review_20261005.json)
