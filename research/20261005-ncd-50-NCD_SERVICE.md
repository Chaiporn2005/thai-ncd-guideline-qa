# NCD_SERVICE research trail — 20261005-ncd-50

- Agent: `/root/plus10_ht`, assigned role `NCD_SERVICE`.
- Access date: 2026-10-05. Claim: `ncd50-NCD`; coordinator owns release and canonical merge.
- Scope: 3 new distinct official Thai PDF/manual works about NCD Clinic Plus/service quality. Supporting scope only. Annual editions, mirrors, chapter extracts, Health Station and NCD รพ.สต. are excluded from new-work counts.
- Read repository instructions, HANDOFF, plan, corpus policy, scout prompt, protocol, Orchestra governance/plan/resource ledger/board, status, schema and decision 0003. Compared leads against all 43 existing manifest entries.
- Outputs: 3 source-verified candidates; accepted/human-approved 0. Two have verified PDF links without body retrieval; one has a retrieved PDF with encoding problems. No source files redistributed or committed.

## Actual search queries

Five queries issued using the normal web search tool; no new search after resume. Query budget: 5/8.

1. `site.ddc.moph.go.th "คู่มือถอดบทเรียน NCD Clinic Plus" "Best"`
2. `site.ddc.moph.go.th "คู่มือการใช้งานแบบประเมินคุณภาพ NCD Clinic Online"`
3. `site.ddc.moph.go.th "ถอดบทเรียนรูปแบบการให้บริการสำหรับผู้ป่วย"`
4. `site.ddc.moph.go.th "ทบทวนตัวชี้วัด" "2563-2566"`
5. `site.ddc.moph.go.th "คู่มือชุดเครื่องมือในการป้องกันควบคุมโรคไม่ติดต่อ"`

## Visited issuer pages and identity evidence

All URLs below were visited on 2026-10-05. Issuer HTML is provenance evidence, not a counted corpus work.

| URL | Observed evidence / disposition |
|---|---|
| https://ddc.moph.go.th/dncd/journal_detail.php?publish=9879 | DDC title names hospital Best Practice lessons manual; posting 27 February 2563; Download links to PDF target below. Retained as an independent service work. |
| https://ncdclinicplus.ddc.moph.go.th/pages/public/files/view.php?id=1673855164 | First open failed internally, later open succeeded. Portal names Online assessment user manual, file type PDF, update 7 April 2566. Retained; update date is not PDF publication date. |
| https://www.ddc.moph.go.th/dncd/publish_detail.php?deptcode=dncd&publish=13770 | Official alternate landing for Online manual; catalog gives shortened title and PDF link. Same work, not another document. |
| https://ddc.moph.go.th/dncd/journal_detail.php?publish=13771 | DDC title and download for indicator-review manual 2563–2566; posting 27 January 2566. Retained. |
| https://ncdclinicplus.ddc.moph.go.th/pages/public/files/view.php?id=1698826364 | Portal calls it ถอดบทเรียน Best Practice; detail title describes DM/HT service models; updated 13 February 2568, PDF type. Its relationship to retained 2563 lessons manual remains unresolved. Excluded from count pending work-identity comparison. |
| https://www.ddc.moph.go.th/dncd/journal_detail.php?publish=12586 | Broad local-leader prevention toolkit; further catalogue corroborated title/posting 5 April 2565. Not counted: programme-specific relevance not established. |
| https://www.ddc.moph.go.th/dncd/publication.php | Official catalog corroborates titles, posting dates and Download links. Catalog itself is not a document. Followed independent service-related backup leads without issuing extra queries. |
| https://www.ddc.moph.go.th/dncd/publish_detail.php?deptcode=dncd&publish=12648 | District NCD data-system study/quality-award proposal; catalog posting 20 April 2565. Backup lead only, not emitted after coordinator requested three records. |
| https://www.ddc.moph.go.th/dncd/publish_detail.php?deptcode=dncd&publish=11888 | VDO Clip service-quality report; catalog posting 15 October 2564. Retrieved PDF confirms DDC authorship and service-education content. Strong backup, not emitted after coordinator requested three records. |

## Actual full-PDF retrieval attempts

Eight retrieval attempts, including failures and repeated retrieval of an already seen PDF; no further fetches. Three successful PDF responses, five failures. Seven unique target routes (the portal Online download route did not expose its resolved URL in the error response). Search-result PDF snippets are not counted as retrievals. Normal publisher Download links were used; no restriction bypass.

| Attempt | Actual target / originating click | Result |
|---|---|---|
| 1 | https://ddc.moph.go.th/uploads/publish/987920200228035119.pdf ; Download on publish=9879 | Failed: tool content-size limit, 11,211,478 bytes reported. Retained link only; page count unknown. |
| 2 | https://ddc.moph.go.th/uploads/publish/1377120230127075220.pdf ; Download on publish=13771 | Success: application/pdf, 132 pages. Thai text has extensive font-encoding corruption. Retained; extraction QA pending. |
| 3 | Download link on https://ncdclinicplus.ddc.moph.go.th/pages/public/files/view.php?id=1673855164 | Internal Error with no resolved URL/body. No page-count inference. |
| 4 | https://ncdclinicplus.ddc.moph.go.th/pages/public/files/download.php?id=1698826364 | Success: application/pdf response reports 50 pages; no substantive body lines exposed in returned response. Identity relative to older lessons work not settled; not counted. |
| 5 | Same PDF URL as attempt 4, reopened to inspect front matter | Failed: timeout fetching. Counts as an additional attempt; stopped this route. |
| 6 | https://www.ddc.moph.go.th/uploads/publish/1377020230127075118.pdf ; Download from DDC catalog | Failed: tool content-size limit, 16,014,475 bytes reported. Online manual retained link only. |
| 7 | https://www.ddc.moph.go.th/uploads/publish/1264820220420024109.pdf ; Download on publish=12648 | Failed: tool content-size limit, 11,285,117 bytes reported. Backup only. |
| 8 | https://www.ddc.moph.go.th/uploads/publish/1188820211015084413.pdf ; Download on publish=11888 | Success: application/pdf, 65 pages. Title, DDC quality-service authorship, education/service audience and October 2564 front matter observed; exact publication day unknown. Backup only. |

## Exclusions and remaining review

- Existing NCD Clinic Plus update 3/9/2568, Health Station and NCD รพ.สต. were excluded. Earlier annual NCD Clinic Plus editions (2563/2564/2565/2566) do not add distinct works.
- Existing DM remission implementation lessons were not counted again; retained lessons title concerns the separate NCD Clinic Plus hospital programme.
- Alternate publish=9873 search lead repeats the hospital Best Practice title; not visited or counted separately. Older Online-manual PDF search lead and external basic-HTML ebook layouts were not visited or counted as new works.
- Newer DM/HT Best Practice PDF was not counted because independence from the older lessons work is unresolved. A successful file-type/page-count response alone does not establish content identity.
- Toolkit, district-data study and VDO report are logged above but not emitted in JSONL. Final output is exactly the three required works.
- No publication day invented from posting/update dates. Indicator manual front matter provides month/year only; dates remain null. No hash calculated and no unsupported page count supplied for unretrieved documents.
- Public download access does not establish redistribution rights. All three rights fields unknown and human review null. Link identity verification is not content QA or clinical inclusion approval.
- The two link-only manuals need legitimate body retrieval and work/edition QA before extraction; indicator PDF needs Thai encoding repair or OCR verification. These documents support service questions and must not be represented as three disease-treatment guidelines.
- Used 5/8 queries and 8/8 PDF attempts; no paid API allocation used. Session token/cost telemetry unavailable. No background worker or automation started.

## Validation

- `scripts/validate_manifest.py data/agent_runs/20261005-ncd-50/NCD_SERVICE.jsonl` passed:
  3 records / 3 candidate work IDs / 3 source_verified / accepted 0 / metadata_valid true.
- `scripts/orchestra.py check` passed with `ok: true`, no errors.
- These checks do not verify clinical content, redistribution rights, work-body quality or course corpus equivalence.
