# DM scout — 20261005-ncd-plus10

Access date: 2026-10-05 • Handoff logged 2026-10-05T20:50:23+07:00
Owner: plus10_dm • Claim: plus10-DM • No paid API/clinical acceptance

## Scope and result

ผู้ใช้ยืนยันระหว่างค้นว่า **เฉพาะ PDF/คู่มือ** จึงตัด HTML articles ออกจาก final output
พบ 10 new candidate works: 8 patient-education PDFs, 1 professional nursing manual,
1 implementation-lessons report in a Drive PDF viewer. All source_verified; accepted 0.
8 สื่อศูนย์เบาหวานศิริราชระบุข้อจำกัดการใช้/ดัดแปลง ต้องขอสิทธิก่อนนำไปประมวลผลหรือเผยแพร่
บันทึก metadata เป็น discovery queue ไม่ใช่อนุมัติให้ใช้เอกสาร
แหล่งเป็นแนวทาง/ความรู้ไทย ไม่ใช่ข้อมูลวิจัยประชากรไทยที่ยืนยัน methods แล้ว

Final output: [DM.jsonl](DM.jsonl). Canonical manifest was not edited by scout.

## Actual search queries

Wave 1 (8/8 queries; before PDF-only clarification):

1. `site.si.mahidol.ac.th เบาหวาน อาหาร การดูแล`
2. `site.rama.mahidol.ac.th เบาหวาน สุขภาพ บทความ`
3. `site.rama.mahidol.ac.th/ramachannel/article เบาหวาน`
4. `site.chulalongkornhospital.go.th เบาหวาน การดูแล`
5. `site.dmthai.org/new เบาหวาน หนังสือ คู่มือ`
6. `site.dmthai.org "สมุดบันทึกการดูแลตนเอง"`
7. `site.si.mahidol.ac.th/sirirajdoctor เบาหวาน เท้า ออกกำลังกาย น้ำตาล`
8. `site.dmthai.org/new สมุดบันทึก เบาหวานสงบ 2026`

Wave 2 (2/8 authorized queries; PDF-only):

1. `เบาหวาน คู่มือ ดูแลตนเอง filetype:pdf site.moph.go.th`
2. `โรคเบาหวาน คู่มือ อาหาร filetype:pdf site.dms.go.th`

Tools: web search/open/click; urllib read-only HTTP GET of publisher HTML/PDF;
pypdf on PDF bytes in memory for pages/title, hashlib for actual hashes. No raw files saved.
BeautifulSoup import unavailable; standard-library HTML regex used. No library install.

## Verification evidence

Siriraj official catalogue pages opened with web tool:

- [General diabetes education](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledges.asp)
- [Insulin/self-monitoring education](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesinsulin.asp)
- [Nutrition catalogue](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesposter.asp)

The catalogue provides a warning prohibiting use/adaptation before permission.
Exact detail-page links were read from public HTML; no script or source instruction executed.
Web tool could not fetch several detail URLs; urllib fetched the same public URLs with HTTP200.
This was a tool access failure, not a publisher login/403 bypass.

| Candidate | Exact publisher detail URL | Verification depth / actual PDF pages |
| --- | --- | --- |
| รู้จักเบาหวาน ... กันดีรึยัง | [kl_id=21](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=21) | HTML title/PDF link + bytes, 1 page, first-page text empty; needs OCR |
| ภาวะน้ำตาลในเลือดต่ำ | [kl_id=23](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=23) | HTML title/PDF link + bytes, 1 page, first-page text empty; needs OCR |
| คู่มือการดูแลเท้าในผู้เป็นเบาหวาน (มาดูแลเท้ากันเถอะ) | [kl_id=22](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=22) | HTML + 20-page PDF; cover names SIPI.25 patient education project and rehabilitation/nursing units |
| ภาวะแทรกซ้อนเรื้อรังที่หลอดเลือดขนาดเล็ก | [kl_id=4](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=4) | HTML + 2-page PDF, Thai extraction marks need QA |
| ภาวะแทรกซ้อนเรื้อรังที่หลอดเลือดขนาดใหญ่ | [kl_id=16](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=16) | HTML + 2-page PDF, Thai extraction marks need QA |
| ภาวะเบาหวานขึ้นจอตา (Diabetic Retinopathy) | [kl_id=24](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=24) | HTML + 2-page PDF, first-page text empty; needs OCR |
| การทิ้งเข็ม อุปกรณ์ฉีดยา และแผ่นตรวจน้ำตาลปลายนิ้ว | [kl_id=25](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=25) | HTTP200 HTML title and exact PDF link only |
| การตรวจเลือดที่ปลายนิ้วด้วยตนเองสำคัญอย่างไร | [kl_id=1](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=1) | HTTP200 HTML title and exact PDF link only |
| คู่มือการพยาบาล: การดูแลเท้าเพื่อป้องกันการเกิดแผลในผู้เป็นเบาหวาน | [Publisher PDF](https://www2.si.mahidol.ac.th/division/nursing/sins/attachments/article/251/sins_nursing_manual_2560_11.pdf) | web PDF 116 pages; cover author อัจฉรา สุวรรณนาคินทร์ and 2559, preface August2559 |
| ถอดบทเรียน รูปแบบการดำเนินงาน พัฒนาการจัดการโรคเบาหวาน DM remission | [Society landing](https://dmthai.org/new/index.php/sara-khwam-ru/sahrab-bukhkhl-thawpi/diabetes-book/thxd-bth-reiyn-rup-baeb-kar-danein-ngan-phathnakar-cadkar-rokh-bea-hwan-dm-remission) | clicked [Drive PDF](https://drive.google.com/file/d/1ZjtVdO9AANnL5NbJcG5hDAtgxu7CY-er/view), filename/title verified; PDF body unread |

PDF links/page counts/hashes reside in JSONL. Leaflet update timestamps are not publication dates.
Nursing manual filename `2560` does not supersede cover/preface year2559. Contents lists
appendices beyond retrieved extent116 pages, requiring completeness check. Its professional
purpose/author differs from SIPI.25 patient booklet; they are not counted as two editions of one work.
General diabetes leaflets may cover T1 and T2; adult T2 relevant sections require clinical review.
DM remission lessons is independently catalogued; compare its body against existing remission
service/principles books before final acceptance of work identity.

## Retrieval accounting

Successfully retrieved **8 distinct PDF bodies total** under the amended8PDF allocation:

- 1 rejected lead: [อาหารสุขภาพของผู้ป่วยเบาหวาน, 4 pages](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/1477_1.pdf).
- 1 final professional nursing manual,116 pages.
- 6 final leaflet/patient-manual PDFs; exact bytes hashes computed in memory.

Other PDF open attempts failed in web tool: self-care remission journal with/without trailing `?`,
and Siriraj kl21/23/22 PDF links. No document body returned by those failures; the same
Siriraj PDF URLs later returned HTTP200 with urllib. Distinguish successful document count
from failed tool calls. No automated clinical QA, visual page review or human approval.
Token meter/API cost unknown; no new paid API invoked. Search queries actual10total.

## Exclusions and visited leads

- Existing DM CPG, remission principles/service, clinic standards, educator standards and NCD ClinicPlus are excluded as seeds.
- [DM society book catalogue](https://dmthai.org/new/index.php/sara-khwam-ru/sahrab-bukhkhl-thawpi/diabetes-book) opened and links followed.
- [Carb-counting book](https://dmthai.org/new/index.php/sara-khwam-ru/sahrab-bukhkhl-thawpi/diabetes-book/601-2018-03-07-10-38-18): issuer explicitly links T1/pediatric programme; excluded from adult T2 shortlist.
- [Injection-technique book](https://dmthai.org/new/index.php/sara-khwam-ru/sahrab-bukhkhl-thawpi/diabetes-book/20250626-1-book): sales listing, no verified freely available PDF; excluded.
- [Older remission book](https://dmthai.org/new/index.php/sara-khwam-ru/sahrab-bukhkhl-thawpi/diabetes-book/ibook002): edition/work relationship with existing remission books unresolved; not counted.
- [External self-care-journal announcement](https://cimjournal.com/dia-conferpr/diabet/) was a search lead only; issuer PDF `https://www.dmthai.org/new/attactment/2026/20260302_aw_DM_remission.pdf` open failed, no issuer body verified; excluded.
- [Siriraj nutrition article1477](https://www.si.mahidol.ac.th/sirirajdoctor/article_detail.aspx?ID=1477), [remission article1471](https://www.si.mahidol.ac.th/sirirajdoctor/article_detail.aspx?ID=1471), [hypoglycemia article1101](https://www.si.mahidol.ac.th/sirirajdoctor/article_detail.aspx?ID=1101), [COVID article1423](https://www.si.mahidol.ac.th/sirirajdoctor/article_detail.aspx?ID=1423): read HTML, excluded after PDF/manual-only clarification. Article1477 accompanying PDF was fetched but retained as excluded lead because final preference is standalone manuals/leaflets.
- [Siriraj disease category](https://www.si.mahidol.ac.th/sirirajdoctor/article.aspx?ID=5) read; linked foot article1499 fetch failed; exercise video137 read but no textual PDF; neither counted.
- [Siriraj old foot leaflet kl18](https://si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?div_id=44&kl_id=18): HTML/PDF link read, relationship to newpatient manual unresolved; not counted.
- [Chula four post-meal tips](https://kcmh.chulalongkornhospital.go.th/line/4-%E0%B8%A7%E0%B8%B4%E0%B8%98%E0%B8%B5%E0%B8%A5%E0%B8%94%E0%B8%99%E0%B9%89%E0%B8%B3%E0%B8%95%E0%B8%B2%E0%B8%A5%E0%B9%83%E0%B8%99%E0%B9%80%E0%B8%A5%E0%B8%B7%E0%B8%AD%E0%B8%94%E0%B8%AB%E0%B8%A5%E0%B8%B1/): HTML read, no PDF; excluded. Another Chula prevention result failed open; not counted.
- [DMS older CPG catalogue](https://www.dms.go.th/Content/Select_Content_Grid_PDF?contentCategoryId=29&grid-page=3): web and raw HTML read; historical DM complication entries lacked verified unique document links for this run; not counted.
- [DMS e-Library endocrine category](https://cpg.dms.go.th/categories/%E0%B9%82%E0%B8%A3%E0%B8%84%E0%B8%82%E0%B8%AD%E0%B8%87%E0%B8%95%E0%B9%88%E0%B8%AD%E0%B8%A1%E0%B9%84%E0%B8%A3%E0%B9%89%E0%B8%97%E0%B9%88%E0%B8%AD%20%E0%B9%82%E0%B8%A0%E0%B8%8A%E0%B8%99%E0%B8%B2%E0%B8%81%E0%B8%B2%E0%B8%A3%20%E0%B9%81%E0%B8%A5%E0%B8%B0%E0%B9%80%E0%B8%A1%E0%B8%95%E0%B8%B0%E0%B8%9A%E0%B8%AD%E0%B8%A5%E0%B8%B4%E0%B8%8B%E0%B8%B6%E0%B8%A1/ebooks?sort=latest&viewMode=list): read; new-style DM/HT clinic manual detail click timed out; not counted and potential cross-stream overlap avoided.

## Next gates

Rights permission for restricted educational PDFs; adult scope filtering; OCR and image/number QA;
completeness check for116-page nursing manual; report body/work-identity verification;
human inclusion review. Metadata10 does not equal10 accepted documents or course corpus compliance.
