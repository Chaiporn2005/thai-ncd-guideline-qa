# Proposal 0002 — Verify 30 PDF/manual candidates

- Author: coordinator
- Date: 2026-10-05
- Workstream/run: DM, HT, LIPID / 20261005-ncd-plus10
- State: closed
- Authorization: ผู้ใช้ขอเพิ่มโรคละ 10 เอกสารและยืนยันเฉพาะ PDF/คู่มือ
- Requested change: เพิ่ม full document verification cap จาก 10 เป็น 30 ต่อ run
  โดยใช้เครื่องมือ session เดิม ไม่มี paid API runner
- Evidence: HT issuer landing pages มี download button ที่ web tool ต้อง click เพื่อเห็น PDF URL;
  direct request อีกช่องทางได้รับ 403 และหยุดช่องทางนั้นแล้ว
- Allocation: DM <=8, HT <=14, LIPID <=8 full PDF fetches across both waves (รวม <=30)
- Limits unchanged: <=3 workers, no paid API allocation, human review/rights/access gates
- Acceptance criteria: actual PDF identity/links and access-depth notes; ไม่ยกระดับเป็น accepted
- Decision: [0002](../decisions/0002-pdf-source-verification.md)
