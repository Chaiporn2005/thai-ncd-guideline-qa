# เครื่องมือสำหรับสร้าง RAG

อัปเดต: 5 ตุลาคม 2569 • เป็นแผนเครื่องมือ ยังไม่ได้ติดตั้ง environment ของโปรเจกต์

ใช้ Python กับไลบรารีเพื่ออ่าน PDF, แบ่งข้อความ, สร้าง embeddings, ค้นหลักฐาน
และส่งหลักฐานให้โมเดลตอบคำถาม ระบบค้นเริ่มบน CPU ตามข้อกำหนดวิชา

## สถานะที่ตรวจจริง

ตรวจใน bundled Python runtime ที่ใช้งานผ่าน Codex บนเครื่องนี้:

| เครื่องมือ | หน้าที่ | สถานะ |
| --- | --- | --- |
| Python 3.12.14 | รันโปรแกรมและตัวตรวจ metadata | มีแล้ว |
| pypdf | อ่าน PDF ที่มี text layer | มีแล้วใน runtime |
| sentence-transformers | สร้าง embeddings และค้นข้อความตามความหมาย | ยังไม่มีใน runtime ที่ตรวจ |
| PyTorch | รันโมเดล embeddings | ยังไม่มีใน runtime ที่ตรวจ |
| LLM สำหรับตอบคำถาม | สร้างคำตอบจากหลักฐานพร้อม citation | ยังไม่เลือก API หรือโมเดลในเครื่อง |
| OCR | อ่าน PDF สแกน/ภาพและซ่อมข้อความที่มีปัญหา | ยังไม่เลือก pipeline ของโปรเจกต์ |

การมี Python/pypdf ใน runtime ไม่ได้แปลว่ามี `.venv`, dependencies,
retrieval pipeline หรือ Q&A demo ของโปรเจกต์แล้ว

## เมื่อเริ่ม implementation

1. สร้าง `.venv` แยกใน root ของโปรเจกต์และติดตั้ง dependencies ที่เลือกจริง
2. กำหนดเวอร์ชัน packages และ embeddings model เพื่อให้ทำซ้ำได้
3. อ่านเฉพาะเอกสารที่ผ่านสิทธิ/QA/inclusion gates แล้วเก็บ provenance ของข้อความ
4. เริ่ม SentenceTransformers dense retrieval บน CPU ก่อน variant ที่สอง
5. เลือก LLM, วิธีเก็บ keys และงบจริงก่อนเชื่อม API; ยังไม่มี paid API allocation

เริ่ม baseline ด้วย semantic search ใน Python ได้ ก่อนเลือกบริการ vector database แยก
การเลือก software ไม่แทนงาน corpus, chunking, evaluation และ ablation ตามวิชา

## ตำแหน่งข้อมูล

PDF ที่ดาวน์โหลดเก็บจริงจะอยู่ `data/raw/<document_id>/source.pdf`
ข้อความ/chunks อยู่ `data/processed/`; index อยู่ `data/indexes/`
ส่วน metadata/URLs ที่ขึ้น GitHub อยู่ `data/manifests/`
รายละเอียด: [data layout](../data/README.md)

ปัจจุบันมี manifest 43 candidates, accepted 0 และยังไม่มี raw PDFs ที่บันทึกใน `data/raw/`
รายการใหม่โรคละ 10: [source catalogue](source_catalog_20261005.md)

## เอกสารทางการที่ใช้อ้างอิง

- [Sentence Transformers installation](https://www.sbert.net/docs/installation.html)
- [Sentence Transformers semantic search](https://sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [pypdf installation](https://pypdf.readthedocs.io/en/stable/user/installation.html)
