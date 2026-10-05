# LIPID scout research — 20261005-ncd-plus10

Access date: 2026-10-05 (Asia/Bangkok). Claim: plus10-LIPID.
Scope: NEW independent Thai PDF/manual works supporting adult dyslipidemia education and Thai practice.
This output contains 10 source_verified candidates, 0 accepted, 0 human approved.
Patient education remains supporting; none is presented as a new national clinical guideline.
HTML pages are evidence for linked PDFs, not corpus documents in this PDF-only run.

## Assignment and resource changes

Read AGENTS.md, HANDOFF.md, plan.md, docs/corpus_policy.md, agents/scout.md, schema,
Protocol and Orchestra GOVERNANCE/PLAN/RESOURCES/BOARD/LIPID status before work.
Initial allocation: 8 queries + 4 full-PDF attempts. Coordinator authorized second wave
of 8 queries after user clarified PDF/manual only, then increased PDF allocation to
8 attempts and finally 10 attempts for two ordinary large-file reads.
No paid API, permission bypass, login/CAPTCHA workaround, background worker or raw PDF persistence.

Actual usage: 16 search queries, 10 full-PDF retrieval attempts = 8 successful + 2 tool size failures.
One successful file was rejected (Trat-hosted RCPT nutrition leaflet mirror).
Seven included PDFs retrieved; three remaining sources verified via issuer page/PDF link/format.
Two screenshot attempts returned timeout; no successful visual render/clinical QA.
System Python lacked pypdf before any network read; bundled runtime succeeded.
Actual model token/API cost meter unavailable. No raw bytes hashes computed.

## Actual search queries

Wave 1 (4 + 4 queries, before PDF-only clarification):

1. ไขมันในเลือดสูง site.si.mahidol.ac.th ความรู้
2. ไขมันในเลือดสูง site.rama.mahidol.ac.th บทความ
3. ไขมันในเลือดสูง site.chulalongkornhospital.go.th
4. ไขมันในเลือดสูง site.med.cmu.ac.th
5. site.chulalongkornhospital.go.th/kcmh "ไขมัน" "เลือด"
6. site.rama.mahidol.ac.th/ramachannel/article "ไขมัน"
7. site.si.mahidol.ac.th "ไขมันในเลือดสูง" "นพ."
8. site.srinagarind.md.kku.ac.th ไขมันในเลือดสูง

Wave 2 (4 + 4 queries, PDF/manual-only scope):

9. "ไขมันในเลือดสูง" "เอกสาร" filetype:pdf site.go.th
10. "ไขมันในเลือดสูง" "คู่มือ" site.ac.th
11. "ไขมันในเลือดสูง" "แผ่นพับ" site.go.th
12. "ไขมันในเลือดสูง" "ดาวน์โหลด" site.si.mahidol.ac.th
13. "ไขมันในเลือดสูง" "แผ่นพับ" pdf โรงพยาบาล
14. "ไขมันในเลือดสูง" "คู่มือ" filetype:pdf site.moph.go.th
15. "อาหารสำหรับผู้ที่มีภาวะไขมันในเลือดสูง" pdf
16. "ไขมันในเลือดสูง" "เอกสารประกอบ" site.rama.mahidol.ac.th

Queries executed through web search. Follow-up issuer/catalogue link inspection did not add search queries.
Source titles/snippets were leads; status based on subsequent issuer page or full body checks.

## Candidate evidence and exact URLs

1. **ไขมันสูงในเลือด** (lipid-rama-education-2562)
   - Issuer evidence: [landing](https://www.rama.mahidol.ac.th/cme/sites/default/files/public/Journal_CME_No60_Sub_01.pdf); [PDF](https://www.rama.mahidol.ac.th/cme/sites/default/files/public/Journal_CME_No60_Sub_01.pdf)
   - Population: Adult public/patient education; PDF labels adult lipid categories
   - Edition: ปรับปรุง มกราคม 2562; exact day unknown
   - Access: full_document; PDF pages 6; encoding_issue.
   - Evidence/limits: Full 6-page independent education PDF; compiled by แขมณี จันทร์เทวี. Contains lipid types, adult lab categories, lifestyle and screening. Old recommendations require competent review; not RCPT guideline. Thai marks duplicate in extraction.

2. **ระวัง! ปัญหาไขมันในเลือดสูง** (lipid-siriraj-warning-1158)
   - Issuer evidence: [landing](https://www.si.mahidol.ac.th/th/healthdetail.asp?aid=1158); [PDF](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/1158_1.pdf)
   - Population: General/adult health-check patient education; not explicit age-specific treatment
   - Edition: Undated PDF; issuer landing dated 17 February 2558
   - Access: full_document; PDF pages 1; encoding_issue.
   - Evidence/limits: Full 1-page authored education PDF names อ.นพ.พรพจน์ เปรมโยธิน and issuer. Explains cholesterol/TG causes, HDL/LDL, complications and prevention. Missing Thai tone marks/spaces need image QA. HTML encoding error was overcome by reading ordinary issuer HTML, not access bypass.

3. **คุณค่าอาหารไทยกับไขมันในเลือด** (lipid-siriraj-thai-food-86)
   - Issuer evidence: [landing](https://www.si.mahidol.ac.th/Th/department/preventive/article_detail.asp?id=86); [PDF](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/86_1.pdf)
   - Population: Mixed public education includes child calorie examples; only adult lipid/diet sections in scope
   - Edition: Undated PDF; issuer landing dated 5 October 2553
   - Access: full_document; PDF pages 2; encoding_issue.
   - Evidence/limits: Issuer landing identifies รศ.พญ.ปรียานุช แย้มวงษ์ and PDF link. Full 2-page PDF text has severe font-map mojibake; title/body must be compared visually before ingestion. Distinct authored Thai-food/lipoprotein education, not CPG edition.

4. **ไขมันทรานส์** (lipid-siriraj-trans-fat-1380)
   - Issuer evidence: [landing](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/article_detail.aspx?ID=1380); [PDF](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/1380_1.pdf)
   - Population: Public/adult nutrition education about lipid risk
   - Edition: Undated PDF; issuer landing dated 24 May 2562
   - Access: full_document; PDF pages 1; encoding_issue.
   - Evidence/limits: Full 1-page authored education PDF names นันทกร ทองแตง and issuer. Explains trans-fat sources, cholesterol/TG effects and avoidance. Landing academic rank differs from old PDF; preserve actual PDF provenance. Missing tone marks need QA. Historical regulatory statement is not current legal advice.

5. **ไขมัน** (lipid-siriraj-diabetes-fat-7)
   - Issuer evidence: [landing](https://www.si.mahidol.ac.th/Th/division/diabetes/ct_knowledgesdetail.asp?kl_id=7); [PDF](https://www.si.mahidol.ac.th/Th/division/diabetes/admin/knowledges_files/7_44_1oAgf1K.pdf)
   - Population: Public and diabetes nutrition education; select adult lipid prevention portions
   - Edition: Undated PDF; landing updated 20 June 2568
   - Access: full_document; PDF pages 2; needs_ocr.
   - Evidence/limits: Issuer landing explains dietary fat types, LDL/TG effects and selection; linked PDF retrieved has 2 pages and no text layer. PDF visual/body QA pending; image-only does not verify wording. Copyright reserved on issuer landing; no reuse permission found. Do not count older fat brochures as additional versions of this work without comparison.

6. **แผ่นพับ ลดมัน ลด NCDs** (lipid-doh-reduce-fat-ncd)
   - Issuer evidence: [landing](https://multimedia.anamai.moph.go.th/associates/asc_ncds_2/); direct PDF URL not identified; issuer labels source .pdf and requires form
   - Population: General Thai public/adult prevention nutrition education
   - Edition: Undated PDF; issuer page dated 25 October 2567
   - Access: link_verified_only; PDF pages unknown; not_started.
   - Evidence/limits: Ordinary issuer HTML read via urllib after web timeout; title, .pdf 126.39 KB and A4 leaflet format verified. Page body explicitly links dietary fats to dyslipidemia/CVD and describes lower-fat cooking. Full PDF requires a form; not submitted with invented personal details. Exact direct download URL unknown. This is PDF-catalogue verification, not HTML corpus inclusion.

7. **โภชนาการสำหรับผู้ป่วยโรคหลอดเลือดสมอง** (lipid-siriraj-stroke-nutrition-1298)
   - Issuer evidence: [landing](https://si.mahidol.ac.th/th/healthdetail.asp?aid=1298); [PDF](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/1298_1.pdf)
   - Population: Adult stroke secondary prevention with dyslipidemia; only relevant lipid nutrition sections
   - Edition: Undated PDF; issuer landing dated 6 September 2560
   - Access: link_verified_only; PDF pages unknown; not_started.
   - Evidence/limits: Issuer authored body verified; section ผู้ที่มีภาวะไขมันในเลือดสูง contains substantial fat/cholesterol/fibre/TG diet guidance. Exact PDF attachment href inspected in issuer HTML; PDF not fetched. Record whole authored education work once, not individual subsections. Other stroke/DM/HT answers outside lipid purpose require respective sources.

8. **เมตะบอลิค ซินโดรม กับอาการอ้วนลงพุง** (lipid-siriraj-metabolic-763)
   - Issuer evidence: [landing](https://www.si.mahidol.ac.th/Th/department/preventive/article_detail.asp?id=763); [PDF](https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/763_1.pdf)
   - Population: Mixed public education, adult metabolic risk; only lipid/TG/HDL and prevention portions
   - Edition: Undated PDF; issuer landing dated 11 November 2553
   - Access: link_verified_only; PDF pages unknown; not_started.
   - Evidence/limits: Ordinary issuer HTML read after web fetch failure; authored by ผศ.ดร.พญ.มยุรี หอมสนิท, title and exact PDF href verified. Body explicitly discusses TG/HDL abnormalities and lowering cholesterol/TG through diet/exercise. PDF not fetched; old criteria need clinical QA. Supporting comorbidity education, not new lipid CPG.

9. **องค์ความรู้ด้านอาหารและโภชนาการ สำหรับทุกช่วงวัย** (lipid-inmu-food-knowledge-all-ages)
   - Issuer evidence: [landing](https://inmu.mahidol.ac.th/th/freebook/); [PDF](https://inmu.mahidol.ac.th/uploads_file/freebook/freebook_01.pdf)
   - Population: Mixed all-age nutrition handbook; adult dyslipidemia chapter only, wider ages/topics excluded
   - Edition: พิมพ์ครั้งที่ 1 มกราคม 2559; exact day unknown
   - Access: full_document; PDF pages 170; encoding_issue.
   - Evidence/limits: Full 33,716,649-byte PDF retrieved normally in memory with bundled pypdf after web tool size ceiling; 170 pages. Front matter verifies ISBN978-974-244-374-0, first printing January2559, actual FDA publisher and INMU contribution. TOC/body confirms chapter8 อาหารสำหรับผู้ป่วยโรคไขมันในเลือดสูง (printed111-122), authored by ทิวาพร มณีรัตนศุภร, dietary fat/cholesterol/fibre guidance. Whole handbook is one work even when used by DM/HT scouts. Only adult lipid chapter and relevant adult context in scope; pregnancy/children excluded. Thai sara-am/font marks require QA; no raw bytes persisted; no hash computed. PDF creation metadata is not publication date.

10. **คู่มือโรคหลอดเลือดสมอง (อัมพาต อัมพฤกษ์) สำหรับประชาชน** (lipid-dms-stroke-public-manual)
   - Issuer evidence: [landing](https://www.dms.go.th/backend/Content/Content_File/Old_Content/dmsweb/publish/publish28062019100655.pdf); [PDF](https://www.dms.go.th/backend/Content/Content_File/Old_Content/dmsweb/publish/publish28062019100655.pdf)
   - Population: Thai adult stroke patients/carers; only dyslipidemia risk control and secondary ASCVD nutrition sections
   - Edition: Publication edition/date not verified; PDF front matter partly image-only; do not use upload/creation dates as publication
   - Access: full_document; PDF pages 84; encoding_issue.
   - Evidence/limits: Full 35,547,182-byte PDF read normally in memory with bundled pypdf after web tool size ceiling. 84 pages. Preface/title identifies public stroke manual and Prasat Neurological Institute contact. Printed13/PDF19 explicitly covers cholesterol/LDL/TG risk control; printed47-51/PDF53-57 contains substantial nutrition guidance for high cholesterol/TG. Supporting comorbidity education only; no general stroke Q&A scope expansion. Some image-only front pages and garbled font headers need visual/OCR QA. No exact publication day; no raw bytes saved or hash computed; old targets require review against current CPG.

## Full PDF attempt ledger

| Attempt | Exact URL | Outcome |
| --- | --- | --- |
| 1 | https://www.rama.mahidol.ac.th/cme/sites/default/files/public/Journal_CME_No60_Sub_01.pdf | Success; 6 pages |
| 2 | https://hed.trathospital.go.th/Hed/TG/TG.pdf | Success; 2 pages, rejected mirror |
| 3 | https://www.si.mahidol.ac.th/Th/division/diabetes/admin/knowledges_files/7_44_1oAgf1K.pdf | Success; 2 image-only pages |
| 4 | https://inmu.mahidol.ac.th/uploads_file/freebook/freebook_01.pdf | Web tool size failure: 33,716,649 bytes |
| 5 | https://www.dms.go.th/backend/Content/Content_File/Old_Content/dmsweb/publish/publish28062019100655.pdf | Web tool size failure: 35,547,182 bytes |
| 6 | https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/1158_1.pdf | Success; 1 page |
| 7 | https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/86_1.pdf | Success; 2 pages, font encoding issues |
| 8 | https://www.si.mahidol.ac.th/sidoctor/sirirajonline2021/Article_files/1380_1.pdf | Success; 1 page |
| 9 | https://inmu.mahidol.ac.th/uploads_file/freebook/freebook_01.pdf | Normal urllib in-memory success; pypdf 170 pages |
| 10 | https://www.dms.go.th/backend/Content/Content_File/Old_Content/dmsweb/publish/publish28062019100655.pdf | Normal urllib in-memory success; pypdf 84 pages |

Full body checks are research verification, not ingestion QA. Native fetches handled tool size limits only.
No request was made to bypass a 403. PDF skill read for in-memory extraction and dependency discovery.

## Other visited evidence and exclusions

- https://www.cmu.ac.th/th/article/3beb28f7-bc70-4536-b0d1-48d69719c684
  — authored Thai lipid education body read, but HTML-only; excluded after PDF-only clarification.
- https://sriphat.med.cmu.ac.th/th/knowledge-516
  — hospital dietary dyslipidemia article; HTML-only, excluded.
- https://pharmacy.mahidol.ac.th/th/knowledge/article/411/article.php
  and https://pharmacy.mahidol.ac.th/th/knowledge/article/151/article_staff.php
  — leads only; normal native reads returned 403, stopped. Not included.
- https://hed.trathospital.go.th/links/index12.html
  links "แผ่นพับโรคไขมันในเลือดสูง" to TG.pdf. PDF actually says dietary-fat selection,
  credits เครือข่ายคนไทยไร้พุง ราชวิทยาลัยอายุรแพทย์ and references Siriraj.
  Host is distributor, not issuing author; excluded under primary issuer-only scope.
- https://webportal.bangkok.go.th/public/phpd/page/sub/29717
  — official catalogue titles for 2566 and 2568 lipid leaflets found.
  Linked detail routes /phpd/page/sub/29717/-/0/info/2429 and /3272 returned empty;
  no actual PDF verified; cannot assume independent editions/works. Not included.
- https://ddc.moph.go.th/dncd/journal_detail.php?deptcode=dncd&publish=11224
  — title/date verified but relevant body image, no lipid PDF link; other-page download links
  belong to unrelated publications, not this work. Excluded.
- https://ir.stou.ac.th/bitstream/123456789/11201/1/fulltext.pdf
  — thesis appendix manual lead, no separate authored standalone PDF verified; not fetched/included.
- https://archive.lib.cmu.ac.th/full/T/2548/hp0948ps_ch2.pdf and
  https://archive.lib.cmu.ac.th/full/T/2555/phma30555ts_ch2.pdf
  — thesis chapters, excluded as chapters rather than new standalone works.
- Existing RCPT dyslipidemia CPG/mirrors/revised editions are excluded as seed work.
- https://inmu.mahidol.ac.th/th/freebook/ catalogue reached through actual homepage link;
  whole handbook counted once, not lipid chapter as a separate document.
- https://nutrition2.anamai.moph.go.th/th/download-08 was inspected as a catalogue lead;
  reached unrelated old annual indicators, not verified lipid manual. No record.
- DOH leaflet PDF format and substantial fat/lipid-risk message checked on ordinary issuer page;
  form not filled with fabricated personal information.

## Curator handoff

1. Deduplicate food-nutrition-knowledge-all-ages and stroke-public-manual across DM/HT outputs.
   Assign one authored-work record even if several disease tags are added.
2. Preserve null exact publication dates for month-only printings or page dates.
3. Review rights separately for local processing versus redistribution; PDFs remain absent from repository.
4. Retrieve the three link-only PDFs through legitimate issuer access, then compare body to title.
5. Perform OCR/font repairs, visual checks and competent review of historical numeric recommendations.
6. Limit mixed nutrition/metabolic/stroke manuals to adult lipid/secondary ASCVD content.
7. No accepted counts or course equivalence claim until human inclusion/QA gates pass.

