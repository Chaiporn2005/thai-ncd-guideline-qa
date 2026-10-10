# สารบัญเอกสารในโฟลเดอร์ docs

อ่านตามเป้าหมาย (ชื่อไฟล์ → เนื้อหาโดยย่อ). ผลสุดท้ายและวิธีรันซ้ำอยู่ที่ `../HANDOFF.md`; บันทึก AI สำหรับส่งวิชาอยู่ที่ `../AI_AUDIT.md`

## ผลการทดลองและเหตุผล (Track B: retrieval)
| ไฟล์ | เนื้อหา |
|---|---|
| `hybrid_retrieval_experiment.md` | ผลทุกเทคนิคเทียบกัน (§0 สรุป, §0.2 ผลที่ freeze บน dev/test), ที่มาของทุกพารามิเตอร์ |
| `chunk_size_evidence.md` | วิธีตัด chunk, เหตุผลของ 128/256/384/512, ชุดคำถาม dev/test, นิยาม metric |
| `lenient_relevance.md` | เกณฑ์ "เกี่ยวข้อง" แบบ strict กับ lenient (ปัญหาเฉลยหน้าเดียว) |
| `finding_hidden_text_layer.md` | PDF ที่มีข้อความสีขาวซ่อน และการตัดสินใจ (v12) |
| `finding_unit_mismatch.md` | คำถามกับเอกสารใช้หน่วย/คำเรียกต่างกัน |
| `rag_architecture.md` | แบบออกแบบ RAG ทั้งระบบ |
| `retrieval_process_record.md` | บันทึกละเอียดของ Track B (การตัดสินใจ D, ข้อผิดพลาด E, คำสั่งที่ส่งให้ AI) ที่ใช้สร้าง `AI_AUDIT.md` |

## ชุดคำถาม
| ไฟล์ | เนื้อหา |
|---|---|
| `question_review_guide.md` | วิธีที่เพื่อนตรวจคำถามและส่งผลกลับ |
| `test_set_supplement_20261011.md` | ชุดคำถามเสริมสำหรับ test |

## Corpus (Track A และการเตรียมข้อมูล)
| ไฟล์ | เนื้อหา |
|---|---|
| `corpus_policy.md`, `security_and_ethics.md` | นโยบาย corpus, สิทธิ์, ความปลอดภัย และจริยธรรม AI |
| `corpus_process_record.md` | ใครทำอะไรกับ corpus (v2→v11) |
| `corpus_catalog.md`, `source_catalog_50.md`, `research_notes.md` | รายการและแหล่งเอกสาร |
| `download_pipeline.md`, `extraction_pipeline.md`, `normalization_pipeline.md` | ขั้นตอนดาวน์โหลด สกัดข้อความ และ normalize |
| `fidelity_review_20261007.md`, `verification.md`, `local_preparation_20261005.md` | บันทึกการตรวจและเตรียมข้อมูล |
| `page_context_evaluation.md`, `population_tag_experiment.md` | ป้ายประชากร (ผู้ใหญ่/เด็ก/ตั้งครรภ์/สูงอายุ) และผลทดลอง |

## เครื่องมือและเรื่องที่รอตัดสินใจ
| ไฟล์ | เนื้อหา |
|---|---|
| `agent_workflow.md`, `rag_tools.md` | วิธีใช้หลาย agent และเครื่องมือสร้าง RAG |
| `decisions_guardrail_harness.md` | เรื่อง guardrail/harness ที่เจ้าของงานต้องตัดสินใจ |

โครงโฟลเดอร์ข้อมูล (ส่วนใหญ่ไม่ขึ้น git): `data/processed/` corpus แต่ละเวอร์ชัน, `data/index/` chunk ดัชนี ผลรัน (`runs/`, `sweeps/`) และของ Kaggle (`_work/` เก็บของชั่วคราว, `logs/`), `data/agent_runs/` งานที่สั่ง AI ทำ, `data/manifests/` inventory และบันทึกที่ขึ้น git
