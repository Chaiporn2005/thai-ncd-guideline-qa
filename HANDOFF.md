# Handoff — Thai NCD Guideline Q&A

Updated: 2026-10-06 • Owner: coordinator • Stage: RAG design ready; corpus gates pending

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
27 direct PDF URLs,1 Drive PDF viewer,2 manual e-books; ดู [catalogue](docs/source_catalog_20261005.md)
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

ไม่มี worker หรือ resource claim ที่ลงทะเบียน active; ไม่มี watcher/scheduler
ไม่มี autonomous runner, accepted corpus, Q&A implementation หรือ saved evaluation metrics

## งานถัดไป

1. อ่าน [local preparation](docs/local_preparation_20261005.md) และ [review queue](data/manifests/local_preparation_20261005.csv)
   ให้ผู้ตรวจบันทึกrights/edition/adult scope/clinicalcurrencyและตรวจThai glyphs/tables/units/conditionsกับภาพ
2. จัดหาช่องทางถูกต้องหรือสำเนาที่ทีมมีสิทธิใช้สำหรับ14blocked/2manualviewers;ไม่retry/bypass403
   9prior-permission holdsต้องบันทึกหลักฐานอนุญาตก่อนautomaticextraction/RAG
3. แก้OCR/readingorderจากภาพจริง,finalcontentdedup,ให้คนapprove inclusionตามgates
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
