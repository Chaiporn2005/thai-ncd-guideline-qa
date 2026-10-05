# MANUAL_RIGHTS — actual verification trail

- Run: `20261005-local-prep`; agent `/root/plus10_ht`; claim `prep-MANUAL_RIGHTS`.
- Access date: 2026-10-05. Read AGENTS, HANDOFF, plan, corpus policy, verifier prompt,
  Protocol/Orchestra instructions, resources/BOARD and decision 0004 before network work.
- Assigned scope: two manual viewers; DDC and Nephro terms; Online-manual public-link check.
  No canonical/shared/status files changed. No PDF-body downloads or document approval.
- Output `MANUAL_RIGHTS.json`: 25 document-scoped queue observations (14 DDC, 11 Nephro).
  Publisher-wide observations are mapped to existing IDs, not 25 separate terms verifications.
  Preserved records outside selected55 are included; coordinator must filter the selected cohort.

## Findings and decision boundaries

### DDC policy, observed source terms

Evidence: https://www.ddc.moph.go.th/policy_website.php . Successful web-tool HTML response
on 2026-10-05, full text 133 lines; section references below. This was **not** a native HTTP200
observation. A native request to a different DDC landing later returned403 and was stopped.

- §2.2 conditions modification, transfer/sale and derivative works on express owner permission.
- §3.3 relevant original excerpt:
  > รวมถึงการใช้ วิธีการอัตโนมัติ (การใช้สคริปต์) นอกจากช่องทางที่ กรมควบคุมโรค จัดเตรียมไว้ให้
  The sentence's final clause provides an express-permission exception. Source lines77–78.
- §3.5 separately conditions copying/reproducing the **service** on permission (lines81–82).
- §4.2 imposes written-consent conditions on inward/deep links (lines90–91).

Observed Download links establish provided public access channels. These clauses do not establish
a blanket right to automate bulk processing, create a RAG derivative or redistribute PDFs/text.
The supplied-channel qualification also does not, by itself, prove a ban on every ordinary GET of
the exact issuer-provided download. JSON `restricted_pending_review` is a conservative reuse
queue disposition; it is not a legal finding or permission granted/refused by this agent.
Local review through actual supplied links remains distinct from later reuse; coordinator decides
the concrete route under decision0004 and preserves any document-specific restrictions found.

### Health Station manual

DDC landing https://www.ddc.moph.go.th/dncd/publish_detail.php?deptcode=dncd&publish=16814
publicly links the manual at https://online.fliphtml5.com/bcbgj/swdq/ . Ordinary HTML returned200.
The public reader's advertised script
https://online.fliphtml5.com/bcbgj/swdq/javascript/config.js?1787896267 returned200 and shows
`downloadconfig.pdf: null`, `downloadConfig: null`. Generic Download translation strings do not
prove a configured download. No PDF URL was constructed or requested.

Search found https://ncdstrategy.ddc.moph.go.th/media_list/2 . Public HTML/embedded data maps
the same title to item27, `type: link`, `file_type: null`, pointing back to
https://ddc.moph.go.th/dncd/journal_detail.php?publish=16814 . It supplies no new PDF route.
Result: retain `viewer_only`; no resolved downloadable PDF.

### 77-province reduced-sodium menu manual

DDC source https://www.ddc.moph.go.th/dncd/publishinfodetail.php?deptcode=dncd&publish=16356
names the book and advertises https://shorturl-ddc.moph.go.th/ixreZ . That short URL was unresolved
in prior work and was not requested again here.

NHCO https://www.nationalhealth.or.th/public/ebook/2 names the same book and links the public reader:
https://www.nationalhealth.or.th/public/storage/ebook/ec8c368a-7c7d-4370-87ed-41e010973421/ .
Web tool initially timed out; one normal HTML retry returned200. Public advertised script
`javascript/config.js` returned200 and still points to
https://main.healthstation.in.th/assets/healthpdf/77-Province_Low_Sodium.pdf . That endpoint was404
in the prior curator run. This run **did not request it**. Prior menu CDN403 target was not retried.
No new usable PDF route resolved: `download_candidate_url` is null, retain `viewer_only`.
Reader hosting is access evidence and does not establish a content-owner reuse license.

### NCD Clinic Plus Online user manual

https://ncdclinicplus.ddc.moph.go.th/pages/public/files/view.php?id=1673855164 confirms the exact
title, PDF file type, public Download link and all-rights-reserved footer. No download clicked here.
The earlier issuer-catalog verified candidate
https://www.ddc.moph.go.th/uploads/publish/1377020230127075118.pdf is preserved for coordinator
review. Current native HTML recheck of alternate landing publish=13770 returned403 and stopped;
it does not prove the separate PDF URL succeeds or fails. Rights remain subject to DDC review.

### Nephro issuer terms

https://www.nephrothai.org/ web-tool request timed out. One ordinary retry returned403; stopped.
Three actual targeted terms/copyright queries did not yield usable primary-source terms.
`observed_terms: null`, reuse unknown. No issuer license inferred from previous public PDF access.
Individual book-front-matter rights were not inspected in this zero-PDF-body task; an inaccessible
website or absent search hit is not evidence that restrictions do not exist.

## Actual search queries — 7/8

1. `site.nephrothai.org "ลิขสิทธิ์" "เว็บไซต์"`
2. `site.ddc.moph.go.th "นโยบายเว็บไซต์" "ลิขสิทธิ์"`
3. `"แนวทางการดำเนินงานสถานีสุขภาพ" "pdf"`
4. `site.nephrothai.org "สงวนลิขสิทธิ์"`
5. `"เล่มเมนูอาหารท้องถิ่นลดโซเดียม 77 จังหวัด" "ดาวน์โหลด"`
6. `"nephrothai.org" "copyright"` with domain filter `nephrothai.org`
7. `"แนวทางการดำเนินงานสถานีสุขภาพ" "Health Station" "ดาวน์โหลด"`
   with domain filter `ddc.moph.go.th`

Unrelated search results, other organizations' policies and PDF search snippets were not reused
as these issuers' terms. No PDF search result opened; no license extrapolated between publishers.

## Actual HTML/JS requests — 20 explicit attempts

| Route | Requests / result |
|---|---|
| DDC Health Station publish_detail=16814 | 1 web HTML success |
| FlipHTML5 reader bcbgj/swdq | 1 web HTML success; 1 native HTML200 |
| NHCO reader ec8c368a… | 1 web timeout; 1 ordinary native HTML200 retry |
| Nephro home | 1 web timeout; 1 ordinary native403 retry, then stopped |
| NCD Clinic Plus Online manual view id1673855164 | 1 web HTML success |
| DDC policy_website.php | 1 web click from issuer footer; 2 subsequent web text reads, all successful |
| FlipHTML5 advertised javascript/config.js?1787896267 | 1 native JS200 |
| NHCO advertised javascript/config.js | 1 native JS200 |
| Official NCDstrategy media_list/2 | 1 web HTML success; 3 native HTML200 reads to inspect title, public popup function and embedded item27 data |
| NHCO public/ebook/2 | 1 web HTML success |
| DDC menu publishinfodetail=16356 | 1 web HTML success |
| DDC Online alternate publish_detail=13770 | 1 native403, then stopped |

Totals: 16 successful HTML/JS responses; 4 failures (2 tool timeouts, 2 native403).
Explicit per-host totals: www.ddc.moph.go.th6; online.fliphtml5.com3; www.nationalhealth.or.th4;
www.nephrothai.org2; ncdclinicplus.ddc.moph.go.th1; ncdstrategy.ddc.moph.go.th4.
No host had more than6 explicit requests across the entire run; internal web-service traffic is
not independently metered. Ordinary requests used timeout30s and at most1 failure retry per route.
PDF-body attempts: **0/0**. No authentication, CAPTCHA, UA impersonation or restriction bypass.
No source images/text page assets, blocked PDF CDN, or inferred hidden file endpoint fetched.
No paid API allocation, background worker or automation; token/platform cost telemetry unknown.

## Validation

JSON parsed successfully: 25 unique existing document IDs, seven requested fields on every row.
This queue has no document-manifest schema or clinical approval effect. No manifest/workflow edits
were made, so their validators were not rerun by this verifier.
