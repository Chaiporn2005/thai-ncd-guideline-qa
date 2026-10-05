# LIPID status

- Owner role: scout (LIPID assignment)
- Active worker: none; last run: assigned LIPID scout / 20261005-ncd-plus10
- Updated: 2026-10-05
- State: source_collection_complete

## Evidence

มี dyslipidemia candidate จากงานค้นรอบก่อนใน [manifest](../../data/manifests/documents.jsonl)
รายละเอียด alternate URL/ฉบับอยู่ใน [notes](../../docs/research_notes.md)

## Next / dependencies

Source collection and curator merge are complete. Rights, extraction/font/OCR/image QA and
human inclusion review remain; source_verified does not mean accepted.

## Resources

Claim `plus10-LIPID`: scout work complete, no active worker; coordinator release planned.

## Current assignment

Run `20261005-ncd-plus10`: หา 10 new distinct works เพิ่ม ไม่ซ้ำ seeds เดิม; claim `plus10-LIPID`

## 2026-10-05 — run handoff

- Outputs: [10 PDF/manual candidates](../../data/agent_runs/20261005-ncd-plus10/LIPID.jsonl) and
  [actual search/access log](../../data/agent_runs/20261005-ncd-plus10/LIPID_research.md).
- Schema check passed: 10 records / 10 candidate work IDs / 10 source_verified / 0 accepted.
- Usage: 16 actual search queries; 10 full-PDF attempts, 8 successful and 2 web-tool size failures.
  One successful PDF rejected as distributor mirror; 7 included full-document candidates,
  3 issuer-page/link-verified candidates. Two screenshot attempts timed out.
- All 10 are supporting patient education / nutrition / comorbidity manuals, not new national CPGs.
- In-memory full PDF checks verify INMU/FDA nutrition handbook 170 pages (first print Jan2559)
  and Prasat/DMS public stroke manual 84 pages, with adult lipid portions; no raw PDFs saved.
- Curator must deduplicate `food-nutrition-knowledge-all-ages` and `stroke-public-manual` across streams.
- Next: rights, extraction/font/OCR/image QA and human inclusion review; null exact dates/hashes/reviews.
- No paid API spend or new background worker; coordinator curates and releases resource claim.

## 2026-10-05 — curator merge complete

- Final collection: 10 supporting PDF/manual works merged, comprising 9 scout candidates
  and 1 curator replacement; accepted: 0. See [source catalogue](../../docs/source_catalog_20261005.md).
- Curator replaced the DOH form-gated leaflet with the distinct 2-page Siriraj brochure
  ปริมาณคอเลสเตอรอลในอาหาร (SIPI PD1005164; last review 2564), PDF path
  `Brochure_files/1_1JX2jI.pdf`. Final retained full-document count: 8, including this replacement.
- Trat leaflet remains excluded because its relationship to Siriraj kl7 is unresolved.
- Isolated scout JSONL/research outputs remain immutable as the original research handoff.
- Original scout usage: 16 queries; 10 full-PDF attempts; 8 successes, of which 1 excluded;
  2 web-tool size failures. No queries, fetches or tests added for this status update.
- Source collection complete; no active worker. Coordinator release of resource claim planned.
