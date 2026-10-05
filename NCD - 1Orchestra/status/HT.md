# HT status

- Owner role: scout (HT assignment)
- Active session / last run: none / 20261005-ncd-plus10
- Updated: 2026-10-05
- State: source_collection_complete

## Evidence

มี hypertension candidate จากงานค้นรอบก่อนใน [manifest](../../data/manifests/documents.jsonl)
รายละเอียด publisher access restriction และ mirror อยู่ใน [notes](../../docs/research_notes.md)

## Next / dependencies

ยืนยันฉบับและความครบของ mirror ด้วยต้นทางที่เข้าถึงได้ตามปกติ
ไม่ bypass 403; แยก source verification จาก full content QA

## Resources

No active worker or claim; coordinator released `plus10-HT` after curation.

## Current assignment

Run `20261005-ncd-plus10`: หา 10 new distinct works เพิ่ม ไม่ซ้ำ seeds เดิม; claim `plus10-HT`

## Handoff — 2026-10-05T20:50:08+07:00

10 source_verified supporting candidates; accepted 0. 8 direct PDF targets + 2 manuals
(Health Station viewer; 77-province menu government short URL unresolved).
PDF target attempts 10: successful 6 (4 retained, 2 excluded), failed 4 (3 size, 1 timeout).
Actual queries 16 (8 first wave + 8 PDF/manual wave approved by coordinator).
Outputs: `data/agent_runs/20261005-ncd-plus10/HT.jsonl` and `HT_research.md`.
No canonical manifest edits; curator dedup, body/rights/clinical/adult-scope review pending.
Historical vaccination-specific protocol is context-bound, not current general HT authority.

## Curator handoff — 2026-10-05

Curator merged 10 new HT candidates: 8 direct PDF links and 2 manual viewers; accepted 0.
Final catalogue: [source_catalog_20261005.md](../../docs/source_catalog_20261005.md).
Coordinator repaired the 77-province menu link to an official NHCO e-book reader;
advertised PDF returned 404 and external CDN returned 403, so no PDF body claim.
Health Station remains a publisher-designated manual viewer.
Body extraction, rights, adult-scope and competent clinical QA remain pending.
Historical COVID vaccination protocol remains context-bound, not current general HT authority.
Final scout usage: 16 queries and 10 unique PDF target attempts; 6 retrieved including 2 excluded.
Isolated scout JSONL and research log retain the original evidence without rewriting history.
