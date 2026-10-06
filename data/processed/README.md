# Normalized text summaries

## normalized-v2 (2026-10-06, current for retrieval)

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
