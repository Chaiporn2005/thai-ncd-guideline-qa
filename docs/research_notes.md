# ผลค้นแหล่งข้อมูลรอบแรก

วันที่ตรวจ: 2026-10-05 (Asia/Bangkok)
ผู้ใช้ยืนยัน scope: แนวทางไทยสำหรับคนไทย

## งาน agents ที่ทำจริง

- `diabetes_sources`: ค้นเอกสารเบาหวานจากสมาคมโรคเบาหวานฯ และกรมควบคุมโรค
- `cardiometabolic_sources`: ค้นความดัน ไขมัน และ CKD จากสมาคม/ราชวิทยาลัย/แหล่งรัฐบาล
- `agent_design_review`: ตรวจการแบ่งบทบาทและ gates กับ instruction รายวิชา
- Parent: ตรวจ NCD Clinic Plus, รวม metadata, เขียน plan/prompts/policy/board และ validator

ไม่ได้สร้าง autonomous agent runner หรือเริ่ม recurring searches
บทบาท prompts พร้อมใช้ในการ dispatch รอบถัดไปผ่านเครื่องมือที่รองรับ subagents

## Seed inventory

รวม **13 candidate records** ใน `data/manifests/documents.jsonl`
ยังไม่มีการ human-approve/accept เอกสารใด (accepted = 0)
ID/work identity ยังเป็น provisional สำหรับบางเอกสารสรุป ไม่ใช่หลักฐานว่ามี 13 independent works ที่นับได้

| กลุ่ม | รายการ | การตรวจในรอบนี้ |
|---|---:|---|
| เบาหวาน | 5 | publisher landing/viewer หรือ PDF ใน web tool |
| ความดัน | 1 | identity/front matter ของ government mirror; publisher 403 |
| ไขมัน | 1 | publisher landing, Drive link และ issuer-hosted revised PDF |
| CKD (optional scope) | 5 | landing/link หรือโครงสร้าง PDF; ระดับการตรวจต่างกัน |
| NCD Clinic Plus | 1 | landing/update และ linked PDF |

Scope fit: core 3 (DM/HT/lipid guideline), supporting 5 (DM remission/clinic/education/NCD service),
requires_scope_expansion 5 (CKD). ตารางนี้ใช้จัดงาน ไม่ใช่จำนวนเอกสารที่ผ่านเกณฑ์วิชา

## ข้อจำกัดที่พบ

1. **Drive viewer ไม่ใช่ PDF ที่อ่านแล้ว:** DM CPG, clinic standards, educator standards และ CKD primary-care
   บางรายการเปิด publisher/viewer ได้ แต่ body ยังไม่ได้อ่าน; ไม่สรุปว่าไฟล์ private หรือเสียจาก Loading/Sign in
2. **Encoding/OCR:** DM remission principles 198 หน้า และ service manual 32 หน้า มี Thai text corruption;
   HT mirror มีสัญลักษณ์ซ้ำ/เพี้ยน ต้องเทียบภาพ ไม่แก้ตัวเลขโดยคาดเดา
3. **HT mirror completeness:** สำเนารัฐบาลที่ agent ตรวจมี 153 หน้าและอาจไม่มี English/reference sections ทั้งเล่ม
   ให้ตรวจ completeness ก่อนใช้ และไม่ใช้ page count นี้กับ publisher full file ที่ยังอ่านไม่ได้
4. **Lipid revision:** publisher page links Drive; issuer-hosted 48-page filename ระบุปรับปรุง
   ยังไม่ได้ diff กับ Drive; อย่าเดาความสัมพันธ์ amendment/supersession
5. **CKD identity:** March/June2023 PDFs ระบุ revised2565 และ 106 หน้าเท่ากัน แต่ยังไม่เทียบ hash/content;
   one-page poster กับ primary-care handout อาจเป็น derivative จึงไม่เพิ่ม corpus count อัตโนมัติ
6. **Rights:** เอกสาร DM remission บางเล่มสงวนลิขสิทธิ์หรือระบุว่าทำซ้ำต้องขออนุญาต;
   เอกสารอื่นยังไม่ยืนยัน open licence เก็บแค่ metadata/URLs ใน repo
7. **Population:** ไม่รวมเอกสารเด็ก/T1DM เพื่อให้ครบจำนวน; clinic service material ที่ครอบคลุมเด็กต้องเลือก section ผู้ใหญ่
8. **ไทย:** Thai guidance กับ Thai-participant research เป็นคนละประเภท; ไม่อ้างว่า guideline ใช้เฉพาะข้อมูลวิจัยคนไทย

## Sources และ provenance

Exact landing/download URLs และระดับตรวจแต่ละรายการอยู่ใน manifest
Primary discovery hubs:

- https://dmthai.org/new/index.php/sara-khwam-ru/sahrab-bukhkhl-thawpi/diabetes-book
- https://www2.rcpt.org/web/content/1022
- https://www.nephrothai.org/ckd-2/
- https://www.ddc.moph.go.th/dncd/
- https://cpg.dms.go.th/

รายการนี้ไม่อ้างว่าเป็น latest editions ทุกหัวข้อ และไม่ได้ตรวจความถูกต้องทางคลินิกของทุกหน้า
ไม่บันทึก query log ที่แต่งย้อนหลัง; รอบถัดไปต้องเก็บ actual query/tool/time log ตั้งแต่เริ่มตาม workflow

## Next actions

1. เลือก source ที่อยู่ core scope และหาวิธีเข้าถึง PDF ที่ถูกต้อง
2. ตรวจสิทธิ ดาวน์โหลด local และสร้าง hash จริง
3. ตรวจ OCR/layout กับหน้าที่จะใช้ทำ gold evidence
4. Resolve revision/derivation และ population metadata
5. ให้คนตรวจ inclusion ก่อน accepted แล้วนับ corpus ที่ใช้จริง
