# Handoff — Thai NCD Guideline Q&A

Updated: 2026-10-09 • Owner: coordinator • Stage: Track B corpus v11 merged to main; Track B L1 (chunk/embed/search) next; Track A integration pending

## ผลสุดท้ายของ Track B (retrieval) สำหรับ C และ D (2026-10-11)

ระบบที่ freeze: `configs/retrieval/frozen_v1.json` บน corpus **v12** (ถอนคู่มือ Clinic Plus; 66 เอกสาร) bge-m3, parent-child 128→512, BM25 char3, convex α 0.6, k = 10

| ระบบ | test R@1 / R@5 / R@10 / MRR@10 (52 ข้อที่ตอบได้) | หมายเหตุ |
|---|---|---|
| A dense ล้วน | 0.462 / 0.808 / 0.827 / 0.618 | ฐานเทียบ |
| **B hybrid** | 0.587 / 0.885 / 0.981 / 0.737 | **ค่าเริ่มต้นสำหรับ CPU**; ดีกว่า A แบบมีนัยสำคัญ (R@5 +0.077, CI +0.019…+0.154) |
| C B + reranker | 0.615 / 0.913 / 0.952 / 0.771 | **ใช้ถ้ามี GPU** (ผู้ใช้ตัดสิน 2026-10-11); ดีกว่า B เล็กน้อยแต่แยกจาก noise ไม่ออก; บน CPU 15–36 วินาที/คำถาม |

- ผลดิบ `results.jsonl` ตาม schema, `metrics.json`, `run_manifest.json`: `runs/frozen_v1/` (เฉพาะ metrics และ manifest ขึ้น git; `results.jsonl` ที่มีข้อความคำถามอยู่ใน `data/index/runs/final/<ชุด>-<ระบบ>-bge-m3/` ในเครื่องเจ้าของ Track B ขอไฟล์จากเขาหรือรันใหม่ด้วยคำสั่งใน docstring ของ `scripts/run_retrieval.py`)
- รันซ้ำ: `scripts/run_retrieval.py` โหมด A (ไม่ใส่อะไรเพิ่ม), B (`--hybrid ...`), C (`--rerank-scores` จาก `infra/kaggle_rerank`); `--split test` ต้องมี gold ครบและไฟล์โค้ด/ค่าตั้งที่ commit แล้ว และ **ห้ามรันซ้ำเพื่อปรับค่า**
- ต้องมีดัชนี: `data/index/dense-bge-m3-t128-v12` และ `chunks-v12-t128/512` (ไม่ขึ้น git; สร้างใหม่ด้วย `build_chunks.py` + `splice_index.py` หรือขอจากเจ้าของ Track B)
- LLM ที่ใช้ได้ในขั้นสร้างคำตอบ: **Typhoon `typhoon-v2.5-30b-a3b-instruct` เท่านั้น** (ต้องแคชทุกคำขอ: `src/ncdqa/llm/client.py`; คีย์ใน `.env` ตัวแปร `TYPHOON_API_KEY`); Gemini ฟรี (20 คำขอ/วัน) และ GLM ฟรี (ช้า ติด rate limit) ใช้ไม่ได้กับ batch; ไม่ใช้ LLM เขียนคำค้นใหม่ (แย่ลงทุกโมเดล)
- ข้อควรรู้: test มี 52 ข้อที่ตอบได้ ช่วงเชื่อมั่นกว้าง; gold ยืนยันแค่ "ตรงกับเอกสาร" ไม่ใช่ความถูกต้องทางคลินิก; รายละเอียดการทดลองทั้งหมด `docs/hybrid_retrieval_experiment.md`; บันทึก AI audit `AI_AUDIT.md`, `docs/retrieval_process_record.md`

> **Track C:** ดู `docs/handoff_track_c.md` (ฟังก์ชัน `search(query, variant, k, filters)` ใน `src/ncdqa/retrieval/search.py`, ผล freeze และกติกา) แพ็กเกจข้อมูลอยู่ที่ `data/handoff/track_c_20261012.zip` ในเครื่องเจ้าของ Track B (ไม่ขึ้น git)

## อ่านก่อนทำต่อ: Track B merge เข้า main แล้ว (2026-10-09)

**ต้อง `git pull origin main` ก่อนทำงานต่อ** (PR #2 และ #3 merge แล้ว) corpus ที่ใช้เป็นหลักตอนนี้คือ **`normalized-v11` ของ Track B**
(68 เอกสาร / 4,009 หน้า; ค้นได้ 3,749 หน้า) ตามที่เจ้าของโครงการตัดสินใจให้ใช้ของ Track B เป็นฐานหลัก

- อ่านภาพรวม/ตัวเลข/ข้อผิดพลาดที่จับได้: [docs/corpus_process_record.md](docs/corpus_process_record.md); คำสั่งสร้างแต่ละ version: [data/processed/README.md](data/processed/README.md)
- **`normalized-v2` ใน Git ยังเป็นของ Track A** (ตัวสกัด v2 หลัง fidelity review) ส่วน Track B สร้าง v3–v11 ต่อจาก v2 รุ่นก่อนแก้ จึงยังไม่มีการแก้ของ Track A (≥/≤ ขีดเส้นใต้, เลขอ้างอิงยกกำลัง, หน้าแผนภาพ) ใน**หน้าข้อความ PDF ปกติ**: วัดแล้ว 511/1,799 หน้าต่างกัน, 11 หน้าเป็นเครื่องหมาย ≥ ≤ (ข้อ 4.16) — ถ้าจะทำต่อ Track A นี่คืองานค้างสำคัญที่สุด (overlay หน้าที่ Track B ไม่เคยแก้ + ให้คนดูหน้าที่ชน)
- **ไม่แก้/ไม่ลบ version เดิม** (corpus version ไม่ถูกเขียนทับ ใช้ `--out` ใหม่เสมอ); เครื่องมือ Track B ที่ใช้ซ้ำได้อยู่ใน `scripts/` (`apply_page_tags.py`, `clean_booklet_pages.py`, `ocr_typhoon.py`, `merge_ocr.py`, `validate_ocr_proposals.py` ฯลฯ)
- **หน้าที่มี `index_exclusion` หรือสถานะไม่ใช่ ok/ผ่านตรวจ ห้ามเข้า index**; `pages.jsonl`, PDF, OCR, ภาพหน้าไม่อยู่ใน Git ต้องสร้างใหม่ในเครื่อง
- **ค้างให้ทีมตัดสิน:** (1) สิทธิ์สื่อศิริราช 9 รายการ: บันทึกขัดกัน ดู `rights_conflict_to_resolve` ใน `data/manifests/rights_review_20261005.json`; (2) `rag_ingestion_hold: false` ของ 68 เอกสาร; (3) guardrail/harness [docs/decisions_guardrail_harness.md](docs/decisions_guardrail_harness.md); (4) ป้ายประชากร ถ่วงน้ำหนักหรือกรอง [docs/population_tag_experiment.md](docs/population_tag_experiment.md)
- ความลับ: คีย์ Typhoon อยู่ใน `.env` ในเครื่องเท่านั้น (ดู `.env.example`); `accepted` ยัง 0 ไม่มีการอนุมัติทางคลินิก

## เป้าหมายและข้อกำหนดที่ยืนยัน

- Repository: `Chaiporn2005/thai-ncd-guideline-qa`, Private
- เนื้อหา: แนวทางไทยสำหรับคนไทย; core DM/HT/LIPID ผู้ใหญ่; CKD optional
- ใช้หลาย agents ค้นและตรวจข้อมูล โดยยังต้องทำ RAG/evaluation ตามวิชา
- ผู้ใช้ขอจัด workflow ตาม kaggle-team; อ่าน [Protocol](NCD%20-%200Protocol/PROTOCOL.md)
  และ [Orchestra](NCD%20-%201Orchestra/README.md) ก่อนรับงานต่อ

## ทำแล้วและหลักฐาน

มีแผน/role prompts/policy/schema, manifest58 records:30extracted/28source_verified (accepted0),
metadata validator และโครง orchestration แบบ file-based
รอบเตรียมล่าสุดขึ้นGitHubแล้วในcommit9751d50;ตรวจremote mainตรงกับlocalHEADหลังpushจริง
รอบค้น55แหล่งอยู่7c4f1cb;รอบเพิ่มโรคละ10เดิมอยู่19652cf
สถานะเครื่องมือและ environment อยู่ใน [RAG tools](docs/rag_tools.md)
ดู [board](board.md), [research notes](docs/research_notes.md) และ [run log](runs/LOG.md)
รอบก่อนเพิ่ม30รายการ DM10/HT10/LIPID10 ตามข้อกำหนด PDF/คู่มือ:
27 direct PDF URLs,1 Drive PDF viewer,2 manual e-books; ดู [catalogue](docs/source_catalog_50.md)
ดึงเนื้อหาPDFได้19รายการใหม่ แต่ไม่มีrawPDFsเก็บในrepoหรือhumanapproval
รอบค้น `20261005-ncd-50` เพิ่ม15งาน: CKD6, NCD_SERVICE3 และ CORE6
เลือก55 PDF/คู่มือหลังกันJPG/possible excerpt/historicalCOVID-specific guidanceออก3รายการ
หมวดนับหนึ่งงานต่อหมวด: DM17/HT10/LIPID13/CKD9/NCD_SERVICE6
ดู [catalogue ล่าสุด](docs/source_catalog_50.md), [CSV](data/manifests/corpus_50_candidates.csv)
และ [actual queries/attempts](research/20261005-ncd-50.md)
รอบล่าสุด `20261005-local-prep`:โหลด39PDF/39hashไม่ซ้ำ/1799หน้าเก็บในdata/raw/
สกัดเพื่อprivate fidelity review30เอกสาร/1766หน้า;15needs_ocr/12encoding_issue/3extracted_unreviewed
OCRไทย+อังกฤษ6หน้าจาก3เอกสารในdata/processed/ocr-review-v1/;พบword/unit/spacing/reading-order errors จึงไม่ผ่านQA
9สื่อศูนย์เบาหวานศิริราชพักautomaticextractionก่อนpermission;14แหล่งยัง403และ2คู่มือไม่มีworkingPDF
เพิ่มforeground download/extract CLI และrights gate;ไม่มีraw/text/imagesขึ้นGit
หลักฐาน:[ผลเตรียมล่าสุด](docs/local_preparation_20261005.md),[review CSV](data/manifests/local_preparation_20261005.csv),[rights queue](data/manifests/rights_review_20261005.json)
ไฟล์ต้นแบบ Kaggle ใช้เป็น reference สำหรับการจัดระบบ ไม่ใช่คำสั่งให้ใช้บัญชี/งบ/ข้อมูลของต้นแบบ

## งานกำลังรัน

ผู้ใช้ขอให้ลองออกแบบ RAG ตามภาพสำหรับโครงการ:ดู [docs/rag_architecture.md](docs/rag_architecture.md)
และ [decision 0007](NCD%20-%201Orchestra/decisions/0007-ncd-rag-architecture.md)
มี Mermaid diagrams แยก multi-agent ingestion/index, query/answer safeguards และ A/B evaluation
RAG status: design พร้อมทบทวน; implementation ยังไม่เริ่ม;ไม่มี accepted corpus/index/LLM/model/gold QA/metrics
ขั้นถัดไปยังเป็น rights/content/human gates สำหรับ55 selected candidates ก่อนเริ่ม embedding
Design อยู่ใน [GitHub commit f63010a](https://github.com/Chaiporn2005/thai-ncd-guideline-qa/commit/f63010ac13fb41ee8ec32032d9306ea3ba074a89);remote main ตรงกับ commit หลัง push

รอบ `20261006-disease-folders`:จัด `data/by_disease/` ตามคำขอผู้ใช้
มี5หมวด DM17/HT10/LIPID13/CKD9/NCD_SERVICE6 และ99_excluded3รายการพร้อมเหตุผล
แต่ละdocument_idมีREADME/document.jsonบอกข้อมูลเอกสารและเชื่อมraw/processed records
สร้างจากcanonical manifest/cohortด้วย `scripts/build_disease_catalogue.py`;รัน `--check` หลังอัปเดตmetadata
ตำแหน่งraw/processedใช้document_idตามเดิมสำหรับpipeline;by_diseaseเป็นสารบัญmetadata
ไม่มีการเปลี่ยนrights/clinicalapproval/acceptedหรือเผยแพร่PDF/ข้อความเต็มเพิ่ม
เผยแพร่แล้ว:commitfadf5b7e9db2033b202eeb58119c36e5992ad094;ตรวจremote mainตรงกับlocalHEADหลังpush
ตรวจ58document folders/55selected/3excluded,124generated files,335internal linksและmetadataตรงcanonicalผ่าน

รอบ `20261006-data-github`:ผู้ใช้ขออัปโฟลเดอร์dataและถามเรื่องใช้เพื่อการศึกษา
เพิ่มโครงสร้างraw/processed/indexes/agent_runsพร้อมREADMEและallowlists
publication scope:55retrieval records/33extraction summaries/39reviewed agent outputs
รวมmanifest/schemaเดิม;ดู[data README](data/README.md)และ[inventory](data/manifests/github_data_inventory_20261006.json)
Pushแล้วในcommit0182f05369c65ca769a691b8cf0be663b287b2c1;remote mainตรงกับlocalHEADหลังpushจริง
dataมี149tracked filesรวมmetadataเดิม/README/allowlist/inventory;ตรวจJSON/JSONLและsource-body exclusionผ่าน
PDF39ไฟล์/ข้อความรายหน้า/OCR/ภาพยังlocal-only;ไม่มีหลักฐานอนุญาตเผยแพร่ซ้ำเพิ่มเติม
สถานะrights/humanapproval/acceptedไม่เปลี่ยน;การศึกษาไม่ถูกบันทึกเป็นpublisher permission

รอบ `20261006-thai-normalization`:ผู้ใช้ขอreview dataสำหรับretrievalแล้วให้ทำใหม่และreviewซ้ำ
พบDM CPGเป็นอักษรไทยเพียง4%(ตัวเลขเป็นglyph IDs),HT CPG font mapเสีย,CKD booklet เป็นMacRoman TIS-620
เพิ่ม `scripts/normalize_thai.py` +config/tests;ผลlocal `data/processed/normalized-v1/` 1766หน้า:
ok+minor1658/degraded18/garbled7/OCR11/empty72;dictionary hit92.5%->99.2%;regression0หน้าแย่ลง
ดู [normalization pipeline](docs/normalization_pipeline.md);manifest/rights/acceptedไม่เปลี่ยน;ขึ้นGitแล้วf28eb5b
ผู้ใช้ขอลบผลสกัดรอบแรก:ลบpages.jsonl/extraction.json/ocr-review-v1;ขึ้นGitเฉพาะnormalization.json30ไฟล์(ไม่มีข้อความ)
ผู้ใช้ขอนำ9สื่อศิริราชที่ต้องขออนุญาตออก:ลบretrieval.jsonจากGitHub(เก็บในเครื่อง)และลบPDFในเครื่อง;เหลือlocalPDF30;ดาวน์โหลดใหม่ได้หลังได้อนุญาตเท่านั้น
2026-10-08:mergeแล้วcalvin-check(fidelity review91หน้า) และแก้ปัญหาที่พบในnormalize_thai.py v2
ผลlocal `data/processed/normalized-v2/`:ok+minor1601/degraded16/garbled7/figure_review45/review_hold13/OCR9/empty72+3;v1ลบแล้ว
indexเฉพาะok/ok_minorก่อน;หน้าfigure_review/review_hold/degraded/garbledต้องให้คนตรวจกับภาพ;ดู[normalization pipeline](docs/normalization_pipeline.md)
2026-10-08:ผู้ใช้ตัดสินใช้9สื่อศิริราชเพื่อการศึกษาเท่านั้น([decision 0008](NCD%20-%201Orchestra/decisions/0008-siriraj-educational-use.md));ดาวน์โหลดใหม่(hashตรง)และnormalizeในเครื่อง;ไม่ขึ้นGitHub
normalized-v2ตอนนี้39เอกสาร/1799หน้า;ยังไม่ได้รับอนุญาตจากเจ้าของสื่อ แนะนำส่งคำขออนุญาต
branch review/data-engineering ยังไม่merge:ส่วนการใช้เพื่อการศึกษาของproposal0006ถูกรับเป็นdecision0008แล้ว;ส่วนdata engineering rulesยังรอทีม

รอบ `20261006-recheck-download01` (Calvin, macOS, Python 3.9.6/pypdf 6.14.2):clone repo ใหม่แล้วตรวจ data/raw และดาวน์โหลดซ้ำตาม download pipeline
- Cross-check metadata:46retrieval.json ตรงกับ `documents.jsonl` ทั้ง URL/sha256/pdf_pages;30normalization.json ตรง source_sha256/pdf_pages;validate_manifest ผ่าน
- ดาวน์โหลดด้วย `scripts/fetch_documents.py --local-review --links data/agent_runs/20261005-local-prep/verified_links.json` เฉพาะ30รายการที่เคยdownloaded:30network attempts/30downloaded
- 30PDF/1766หน้า/208.6MB;sha256บนดิสก์ตรงmanifestและreceiptเดิมทุกไฟล์,จำนวนหน้าและbytesตรงทุกไฟล์ (ไม่มีการเปลี่ยนฉบับที่ต้นทาง)
- ไม่ได้ลอง14แหล่ง403(ไม่retry),2manual viewers และ9Siriraj permission holds
- PDF/run log อยู่เฉพาะในเครื่องและถูกignore;retrieval.jsonที่สคริปต์เขียนทับถูกคืนเป็นฉบับcommitเดิม;rights/accepted ไม่เปลี่ยน

ไม่มี worker หรือ resource claim ที่ลงทะเบียน active; ไม่มี watcher/scheduler
ไม่มี autonomous runner, accepted corpus, Q&A implementation หรือ saved evaluation metrics

## งานถัดไป

1. อ่าน [local preparation](docs/local_preparation_20261005.md) และ [review queue](data/manifests/local_preparation_20261005.csv)
   ให้ผู้ตรวจบันทึกrights/edition/adult scope/clinicalcurrencyและตรวจThai glyphs/tables/units/conditionsกับภาพ
2. จัดหาช่องทางถูกต้องหรือสำเนาที่ทีมมีสิทธิใช้สำหรับ14blocked/2manualviewers;ไม่retry/bypass403
   14แหล่ง403เป็นddc.moph.go.th/chulabhornchannel/dmthai.org อาจบล็อกคำขออัตโนมัติหรือIPต่างประเทศ:
   ให้คนในทีมดาวน์โหลดเองด้วยbrowserปกติบนเครือข่ายไทย แล้วบันทึกเป็นแหล่ง/ช่องทางใหม่พร้อมhash ไม่ใช่retryด้วยheaders/cookies
   9prior-permission holdsต้องบันทึกหลักฐานอนุญาตก่อนautomaticextraction/RAG
3. ใช้ `data/processed/normalized-v2` สำหรับretrieval;คนตรวจหน้าdegraded/garbled/ocr_unreviewed,
   ติดป้ายsectionผู้ใหญ่/เด็ก/ตั้งครรภ์(DM CPG90/282หน้า),จัดตาราง/เลขอ้างอิงsuperscript,finalcontentdedup,ให้คนapprove inclusionตามgates
4. Curatorตั้งacceptedเมื่อครบหลักฐาน แล้วเริ่มtoken-awarechunking/STCPUbaselineและvariantที่สอง

ทำส่วนค้น/จัด metadata ที่ได้รับมอบหมายได้; ห้ามอ้างว่าทีมเลือก provider/budget/reviewer แล้ว

## ข้อจำกัดที่ต้องส่งต่อ

55 candidate works ไม่ใช่ accepted corpus; หาก finalreview เหลือไม่ถึง50 documents ต้องยืนยัน equivalent
Drive viewer, blocked issuer, PDF encoding/layout และ alternate editions ยังต้องตรวจต่อ
Raw source PDFs ถูก ignore;retrieval.json และextraction.json summariesขึ้นGitได้;การเข้าถึงสาธารณะไม่รับรองสิทธิเผยแพร่
Git cloneไม่มี39PDF/ข้อความ/OCRที่อยู่เฉพาะในเครื่องนี้;ต้องดาวน์โหลดตามสิทธิ/ช่องทางจริง
Source `content_access` บางรายการเป็นหลักฐานwebเดิม ไม่ได้แปลว่ามีlocalfile;ใช้local preparation reportตรวจไฟล์จริง
ยังไม่มี reviewer assignment, วัน deadline จริง หรือ API budget ที่อนุมัติ
PDF/manual-only เป็นความต้องการล่าสุด; ไม่รวม HTML articles แทนเพื่อให้ครบยอด
HTHealthStationและ77provinceเมนูยังเป็นmanual viewers ไม่มีdirectPDFที่ยืนยันว่าดึงได้

## ตรวจงาน

```powershell
python scripts/validate_manifest.py
python scripts/orchestra.py check
python scripts/orchestra.py status
```

ตัวตรวจเหล่านี้ไม่รับรองความถูกต้องทางคลินิก อ่านผลและ warnings ก่อนส่งต่องาน


## Demo บน Mac ด้วย Typhoon — 2026-10-20 (Track C/D; เพื่อนทำบนสาขา `demoUpdate` แล้วรวมเข้า `rag/track-b-l1`)

สถานะ: `demo.py` รันได้บน Mac (Apple Silicon, Python 3.12 + uv) กับ Typhoon API จริง ที่ทดสอบคือ **CLI** (โค้ดรุ่นก่อนมีเว็บ) **ตอนนี้มีเว็บแอปแล้วในสาขา `rag/track-b-l1` (`demo.py --web`) แต่ยังไม่ได้ทดสอบบน Mac** วิธีตั้งค่า: [docs/SETUP_GUIDE_MAC_TH.md](docs/SETUP_GUIDE_MAC_TH.md)
ข้อมูลที่ต้องมี (ไม่อยู่ใน git, ส่งต่อภายในทีมเท่านั้น): บันเดิล `ncd_demo_bundle` = `data/index/chunks-v12-t128`, `chunks-v12-t512`, `dense-bge-m3-t128-v12` (+ แคชคำตอบ `llm_cache/demo/typhoon_api.jsonl` วางเป็น `data/index/llm_cache/typhoon_api.jsonl`) ต้องมี `.env` (TYPHOON_API_KEY) และ `configs/llm/providers.yaml` (คัดจาก `.example`) ทั้งสองถูก ignore
ตรวจแล้ว: checksum บันเดิลตรง manifest, เวกเตอร์/chunk/id สอดคล้อง, Typhoon ตอบ, เทสต์ 66 ตัวผ่าน, demo โหมด B / `--graph` / `--variant A --show-evidence` / โต้ตอบ ตอบพร้อม citation
ยังไม่ได้ทำ/ไม่ได้ตรวจ: `--variant C` บน Mac, ความถูกต้องทางคลินิกของคำตอบ, **หน้าเว็บ `--web` บน Mac (ทำต่อข้อ 0)**
ทำต่อ (เรียงตามลำดับ):
0. **เพื่อน (Mac): `git pull` สาขา `rag/track-b-l1` แล้วทำตาม `docs/SETUP_GUIDE_MAC_TH.md` ใหม่ (bundle ชุด 2026-10-19 มีแคชครบ 11 ข้อ) รัน `demo.py --web` ลองคำถามตัวอย่างและพิมพ์คำถามเอง แล้วกรอกตารางผลท้ายคู่มือ**
1. **เจ้าของคีย์ Typhoon: rotate คีย์** (เคยหลุดในผลลัพธ์ของเซสชัน) แล้วใส่ใน `.env` เท่านั้น; `.env.example` ต้องว่างเสมอ
2. (เว็บแอปทำแล้วและเปิดเฉพาะ 127.0.0.1 เครื่องตัวเอง) ถ้าจะให้คนอื่นเข้าจากเครื่องอื่น ต้องตัดสินใจก่อนว่าจะเปิดหรือไม่ (จะใช้ quota/คีย์ของเจ้าของ และบันเดิลมีข้อความเอกสารห้ามเผยแพร่สาธารณะ จึงไม่ควรโฮสต์สาธารณะ); วิธีเร็วสุดคือห่อ `demo.py` ด้วย Streamlit/Gradio ในไฟล์ใหม่ โหลดโมเดลครั้งเดียว, แสดง disclaimer + แหล่งอ้างอิง, เก็บ guard G1/G3/O2 และไม่ log ข้อความคำถาม (G2 = B); อย่าแก้ค่า freeze
3. ทดสอบ `--variant C` บน Mac (ช้า 15-36 วินาที/คำถามบน CPU) หรือรันบน GPU ตาม `infra/`
4. ให้คนที่มีความสามารถทางคลินิกตรวจคำตอบตัวอย่างก่อนอ้างว่าคำตอบถูกต้อง (AGENTS.md: gold/คำตอบคลินิกต้องมีผู้ตรวจ)
5. ถ้าเจอปัญหาตอนตั้งค่าบนเครื่องอื่น ให้แก้ SETUP_GUIDE_MAC_TH.md และบันทึกใน AI_AUDIT.md (Error Catch เฉพาะที่เกิดจริง)
