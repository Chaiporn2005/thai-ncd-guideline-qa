# Text fidelity review — 2026-10-07

Run `20261007-fidelity-review`. Reviewer: Calvin's session (AI-assisted sampling, not human approval).
Scope: the 30 local review PDFs from `20261006-recheck-download01`, compared page by page against
the retrieval text produced by `scripts/normalize_thai.py` (re-run into the local, ignored folder
`data/processed/normalized-recheck-20261006/`; no OCR because tesseract was not installed).

This review checks whether the extracted text says what the printed page says. It does not approve
rights, clinical currency, or inclusion. Per-page findings are in the local, ignored files
`data/agent_runs/20261007-fidelity-review/review_{DM,HT_LIPID,CKD_NCD}.json`.

## Method

- 91 sampled pages across 30 documents, each rendered with `pdftoppm` and compared with its
  extracted text. Sampling covered every `degraded`/`garbled` page (capped), some `ok_minor_issues`
  and `empty` pages, `ok` pages with tables or numeric thresholds, and random prose pages.
- The HT/LIPID reviewer also scanned all pages of its 14 documents for replacement characters and
  citation-number merges.
- Three critical findings were re-checked directly in the text (CKD p29, LIPID p32, stroke
  nutrition p2); all three were confirmed.
- Reproducibility: the normalization re-run matched the committed `normalized-v1` summaries
  (same source hashes and page counts). Status counts differ only on the 11 pages the earlier
  run OCRed, and on 4 pages of `lipid-inmu-food-knowledge-all-ages` (`ok_minor_issues` → `ok`,
  probably pypdf 6.14.2 vs 6.10.0).

## Results

11 usable, 14 usable with fixes, 5 need OCR or rework.

| Document | Verdict | Worst issue |
| --- | --- | --- |
| dm-cpg-2566-revised-2567 | usable with fixes | Flowcharts on pdf 102, 104, 120, 145, 170, 191, 204, 205, 257 are images; only captions extracted although marked `ok` (p145 loses "≤ 70 มก./ดล." and glucagon doses). p144 "½" → U+FFFD |
| dm-clinic-standards-2567 | usable with fixes | p44 food-portion table header order wrong; row values correct |
| dm-educator-standards-2567 | usable | Stray intra-word spaces only |
| dm-remission-implementation-lessons-undated | needs OCR/rework | Broken font map document-wide (613 U+FFFD); p36 outcome tables interleaved |
| dm-siriraj-geriatric-diabetes-diet-verified-20261005 | usable | Dropped SARA AM in some headings |
| dm-siriraj-nursing-foot-ulcer-prevention-2559 | usable with fixes | **Critical:** p47 ABI formula extracted inverted (brachial over ankle) |
| ht-guideline-2567 | usable | Copyright watermark leaks into text (~154 times) |
| ht-siriraj-hypertension-public-1587-verified-20261005 | usable | None found |
| ht-siriraj-uncontrolled-opd-2564 | usable with fixes | **Critical:** citation superscripts merge into values ("ร้อยละ 10⁹" → "ร้อยละ 109", p21); BP comparison table loses blank cells and shifts columns |
| lipid-guideline-2567 | usable with fixes | **Critical:** "ร้อยละ 25⁷⁰" → "2570" (p32); Table 1.2 columns interleaved; flowcharts pdf 37–40 lost box text but marked `ok` |
| lipid-dms-stroke-public-manual | usable with fixes | Missing heading glyphs; p5 opens with Latin-1 mojibake but marked `ok` |
| lipid-inmu-food-knowledge-all-ages | usable with fixes | Broken SARA AM on ~30 pages ("น�้าหนัก") |
| lipid-rama-education-2562 | usable with fixes | p2 infographic labels (HDL/LDL/TG/TC) detached from their thresholds |
| lipid-siriraj-cardiovascular-diet-brochure-verified-20261005 | usable with fixes | Italic text swaps า→ำ (21 hits); panel order scrambled |
| lipid-siriraj-food-cholesterol-2564-review | usable | Stray spaces |
| lipid-siriraj-metabolic-763 | usable | None found |
| lipid-siriraj-thai-food-86 | usable | Missing spaces |
| lipid-siriraj-stroke-nutrition-1298 | needs OCR/rework | **Critical:** digits become NUL ("วันละ 300 มิลลิกรัม" → "วันละ \x00\x00\x00 มิลลิกรัม"); tone marks lost |
| lipid-siriraj-trans-fat-1380 | needs OCR/rework | **Critical:** "0% TRANSFAT" → " % TRANSFAT" |
| lipid-siriraj-warning-1158 | needs OCR/rework | **Critical:** "20-30 นาที" → "20 - นาที" |
| ckd-guideline-2565-revised | usable with fixes | **Critical:** underlined ≥/≤ extracted as >/< (p29 BP "≥140/≥90", p32 CrCl, p34 SBP/eGFR/K); p13 risk heat-map meaning is colour-only; p20 CKD-EPI exponents flattened |
| ckd-adult-glomerular-guideline-2561 | usable | Reference numbers merged with years; running headers |
| ckd-adult-renal-nutrition-guideline-2561 | usable | Table header order scrambled; row values correct |
| ckd-anemia-guideline-2564 | usable with fixes | p36 iron/ESA flowchart loses branch structure |
| ckd-hemodialysis-plasma-manual-2561 | usable with fixes | **Critical:** p37 AKI staging "≥0.3 mg/dL" → ">0.3"; no ≥/≤ anywhere in the extracted text |
| ckd-out-of-unit-hemodialysis-standards | usable | "ﬂ" ligature, stray spaces |
| ckd-palliative-2566 | usable | None found; p32 dose table correct |
| ckd-public-kidney-prevention-tips | usable with fixes | Residual MacRoman on ~10 pages (8, 14, 23, 57, 67, 77, 79, 81, 91, 112), e.g. potassium-table vegetable names lost on p79 |
| ckd-treatment-leaflet-undated | needs OCR/rework | Image-only, no text layer; comparison table uses ✓/↑ icons and needs manual transcription |
| DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566 | usable with fixes | Hidden duplicate text layers on pages 7–33 (up to 4 copies per page); would create duplicate chunks |

## Cross-document problems to fix in the pipeline

1. **Underlined ≥/≤ become >/<.** Confirmed in `ckd-guideline-2565-revised` and
   `ckd-hemodialysis-plasma-manual-2561`. Every page in those documents with ">" or "<" before a number
   needs checking against the image (CKD 2565: pages 12, 13, 19, 20, 27, 29–34, 46–49, 53, 56, 91, 93, 94);
   not every instance is wrong.
2. **Citation superscripts merge into numbers.** Confirmed in the OPD manual and the lipid guideline.
   Search for "ร้อยละ" followed by three or more digits to find candidates.
3. **Image-only flowcharts are marked `ok`.** The page has caption text, so the status heuristic
   passes it. DM CPG and lipid guideline flowcharts carry key thresholds and need OCR or manual text.
4. **Status labels miss real defects.** `ok` pages with mojibake (DMS p5) or lost flowchart content
   exist; `ok_minor_issues` also fires on correct accented names in reference lists (CKD 2565 p90,
   nutrition p58). Status alone is not a safe ingestion gate.
5. **Table reading order.** Several tables keep correct values per row but scramble headers or
   interleave columns; a chunk can attach a value to the wrong label.
6. **SARA AM / tone-mark damage** in Siriraj brochures, INMU book and Rama leaflet hurts keyword (BM25)
   matching even where meaning is readable.
7. **Duplicate hidden text** (DDC manual) and watermark leakage (HT guideline) should be removed before
   chunking.

## Preparation for human reviewers (not decisions)

Non-adult sections found:

- `dm-cpg-2566-revised-2567`: children/adolescents ch.16–17 (pdf 203–234), pregnancy ch.18 (pdf 235–244),
  adult type 1 flowchart pdf 104. Printed page = pdf page − 18 in the main body.
- `ht-guideline-2567`: pregnancy ≈ pdf 96–100; young adult and elderly chapters ≈ pdf 105–114.
- `lipid-inmu-food-knowledge-all-ages`: pregnancy pdf 10–23, infants 24–37, school age 38–51,
  adolescents 52–67; lipid chapter pdf 112–123.
- `ckd-anemia-guideline-2564`: paediatric chapter 5 (pdf 51–72).
- `ckd-public-kidney-prevention-tips`: children (p16, 19, 99), pregnancy (p61, 100).
- Smaller mentions: CKD 2565 p44 (pregnancy planning), hemodialysis manual p37 (&lt;18 y criteria),
  palliative appendix p35, 37.
- `lipid-guideline-2567`: adults only.

Edition or date notes that differ from the `document_id`:

- `dm-cpg-2566-revised-2567`: prints "พิมพ์ครั้งที่ 2 กุมภาพันธ์ 2567"; no "ฉบับปรับปรุง" wording found in the
  front matter, so the reviewers should confirm whether the content was revised or only reprinted.
- `dm-remission-implementation-lessons-undated`: printed January 2569.
- `ckd-adult-renal-nutrition-guideline-2561`: states revision March 2563.
- `ckd-adult-glomerular-guideline-2561`: printed 2562.
- `ckd-public-kidney-prevention-tips`: 6th printing, prefaces from 2548.
- `ckd-out-of-unit-hemodialysis-standards`: dated 28 Oct 2568.
- `DDC-NCD-CLINIC-PLUS-ONLINE-USER-MANUAL-2566`: no printed year; text refers to 2565 dates.
- `lipid-inmu-food-knowledge-all-ages`: printed January 2559.
- `ht-guideline-2567`: the table of contents lists an English section and references that are not in
  the 153-page PDF.

Currency flags for clinical reviewers:

- `dm-siriraj-nursing-foot-ulcer-prevention-2559` says HbA1c is not recommended for diagnosis in Thailand,
  which conflicts with DM CPG 2566.
- `ht-siriraj-uncontrolled-opd-2564` cites Thai HT 2019; `lipid-rama-education-2562` cites RCPT 2558.
- `dm-remission-implementation-lessons-undated` is a case-study report from five community hospitals,
  not a guideline.

## Limits

- Sampled review: 91 of 1,766 pages. A clean sample does not prove a document is clean.
- No OCR was run; OCR output from the earlier `normalized-v1` run was not re-checked.
- Findings come from AI comparison of page images with text. Clinical numbers flagged as critical should
  be confirmed by a team member before the text is corrected or excluded.
