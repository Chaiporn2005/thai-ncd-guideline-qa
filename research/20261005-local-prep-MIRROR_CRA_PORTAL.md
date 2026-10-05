# MIRROR_CRA_PORTAL — actual research trail

- Run: `20261005-local-prep-mirrors`; claim `prep-MIRROR_CRA_PORTAL`.
- Agent: `/root/plus10_ht`; access date 2026-10-05.
- Read latest resource/BOARD assignment; AGENTS/HANDOFF/policy/verifier/decision0004 and
  Protocol/Orchestra instructions were read in preceding local-prep task and retained.
- Scope: existing CRA3 brochures and NCD Clinic Plus update2568/Online2566/BestPractice2563/
  indicator-review2563–2566. Find existing work alternatives, not new-count substitutions.
- Output: **1** public issuer alternative facility; exact PDF edition/bytes comparison pending.
  No strong alternative established for the other6 assigned works within query budget.

## Actual search queries — 8/8

1. `"กินอย่างไรเมื่อเป็นเบาหวาน" "จุฬาภรณ์" filetype:pdf`
2. `"โซเดียม" "PR" "จุฬาภรณ์" filetype:pdf`
3. `"ภาวะไขมันในเลือดสูง" "PR67017"`
4. `"คู่มือแนวทางการดำเนินงาน NCD Clinic Plus" "3/9/2568"`
5. `"คู่มือถอดบทเรียน NCD Clinic Plus" "Best Practice" -site:ddc.moph.go.th`
6. `"ทบทวนตัวชี้วัด" "2563-2566" -site:ddc.moph.go.th`
7. `"กินอย่างไรเมื่อเป็นเบาหวาน" -site:chulabhornchannel.cra.ac.th`
8. `"โซเดียม" "จุฬาภรณ์" "แผ่นพับ"`

Search results were leads only. No PDF search result opened. Exact CRA searches did not identify
an identical issuer/partner alternative. Similar-title Bangkok/Samitivej articles, Siriraj/Bangkok
brochures, videos, AnyFlip research abstracts and unrelated annual-report hits were excluded:
different authored works or formats, not mirrors. DDC alternate page layouts and NCDstrategy
catalog search hits alone did not establish new independently hosted PDF bytes.

## Visited HTML and observed download evidence

| URL | Actual observation |
|---|---|
| https://ncdclinicplus.ddc.moph.go.th/ | Web HTML success; redirects to public home below. |
| https://ncdclinicplus.ddc.moph.go.th/pages/public/home/ | Native ordinary HTML200; public navigation advertises academic-manual catalog. |
| https://ncdclinicplus.ddc.moph.go.th/pages/public/files/view.php?id=1673855164 | Web HTML success and native HTML200. Exact manual title, PDF type, update7April2566 and actual `download.php?id=1673855164` Download anchor observed. Retained candidate. |
| https://ncdclinicplus.ddc.moph.go.th/pages/public/files/ | Web HTML success and two native HTML200 reads. Catalog is dynamically populated using its supplied public client loader; static HTML exposed no additional manual records. No login performed, no manual cookie/session reconstruction or loader POST attempted. |
| https://chulabhornchannel.cra.ac.th/media-library/brochure/69699/ | Web HTML success names dyslipidemia brochure and Download link. Ordinary native HTML request returned403; stopped CRA native route without retries. No PDF clicked. |
| https://chulabhornchannel.cra.ac.th/media-library/brochure/nutrition-brochure/69689/ | Web HTML success names diabetes-diet brochure and Download link. No alternative facility established; no native request or PDF click. |
| https://chulabhornchannel.cra.ac.th/media-library/brochure/69663/ | Web HTML success names sodium brochure and Download link. No alternative facility established; no native request or PDF click. |

The three CRA public pages still advertise their brochures, but this run did not obtain a separate
download host/facility. Their already denied PDF URLs were not reattempted. No statement that
the public HTML response proves a PDF download would succeed.

To inspect the dynamic catalog through its normal UI, attempted creating an in-app browser tab
for the already observed public catalog URL. Tool returned `Browser is not available: iab`.
Browser inventory contained no browsers/apps. These two UI calls created no usable tab and
no HTTP observation; no fallback browser/helper, credentials or permission changes attempted.

## Budget and restrictions

- Actual search queries8/8; strong candidates1/5. PDF-body requests **0**.
- Explicit HTML requests11: NCD portal7 (all successful), CRA4 (3web successes,1native403).
  No host exceeded7 explicit requests across the entire task, below10HTML/host/min;
  search-service internal traffic is not independently metered.
- Ordinary native requests used timeout30seconds, no custom UA/authentication/cookies.
- No original CRA/DDC denied PDF URL retried, no URL rewriting to bypass restrictions,
  no login/CAPTCHA/403 bypass and no inferred hidden-file download URL.
- The retained portal endpoint is directly advertised by the issuer; root must still check its
  actual response and compare edition/front matter. URL/body equivalence is not inferred.
- Rights remain in the prior MANUAL_RIGHTS queue. Public access is not redistribution permission.
- Shared manifest/status/plans unchanged. Model tokens/platform cost unknown; no new paid API.

## Validation and handoff

JSON parsed; one unique existing document ID and the seven assigned output fields verified.
Canonical validation/extraction/clinical QA were not performed or claimed. Root owns download,
curation and resource release. Remaining6 works have an alternative-source gap, not a fabricated
replacement, and remain in the blocked/local-review queue unless root verifies a legitimate source.
