# Decision 0002 — Increase document verification allocation

- Decision maker: coordinator
- Date: 2026-10-05
- Proposal: [0002](../proposals/0002-pdf-source-verification.md)
- Outcome: accept
- Authorization basis: การค้นและตรวจ PDF เป็นงานจำเป็นในคำขอโรคละ 10 และ PDF/manual-only
- Rationale: cap เริ่มต้น 10 เสนอสำหรับ pilot; ไม่พอสำหรับการตรวจเอกสาร 30 candidates ตามคำขอใหม่
- Change: config max_full_documents_per_run = 30; per-stream allocation DM8 / HT14 / LIPID8
- No new paid API budget or runner; ใช้ web tools ที่ session มีอยู่
- Conditions: บันทึก actual fetch counts รวม rejected leads; ไม่ bypass 403/login;
  copyright/clinical inclusion ยังต้องคนตรวจ และไม่ publish raw PDFs
