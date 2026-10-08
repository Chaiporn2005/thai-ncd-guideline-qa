# Thai text normalization for retrieval review

`scripts/normalize_thai.py` re-extracts local PDFs with pypdf after deterministic in-memory font-map
repairs, normalizes Thai text, checks page layout signals and writes a separate processed root. It reads
`data/raw/<id>/source.pdf` and never modifies source PDFs or the manifest. It makes no network requests or
paid API calls and does not approve inclusion, rights or clinical content.

Current output: `data/processed/normalized-v2/` (2026-10-08). It replaces `normalized-v1` (2026-10-06),
whose summaries remain in git history at commit `624edb7`.

## Why

The 2026-10-06 data review found that the original extraction was unusable for retrieval in key documents:
the diabetes CPG had 207/282 pages of Latin-looking glyph IDs (digits such as `≥126` lost), the
hypertension CPG had a corrupted ToUnicode map (`หิมายถ้ง` for `หมายถึง`), one CKD booklet was
MacRoman-encoded TIS-620, and many documents lost SARA AM or tone marks. v1 fixed those. The sampled
[fidelity review](fidelity_review_20261007.md) of v1 then found clinical-number errors that v2 addresses.

## Commands

Run from the repository root with the packages in `requirements-ingest.txt`. OCR also needs Poppler
`pdftoppm` and Tesseract with Thai data; pass their paths if they are not on `PATH`.

```bash
python scripts/normalize_thai.py --out-dir data/processed/normalized-v2 --ocr
python scripts/normalize_thai.py --out-dir data/processed/normalized-v2 --ocr --renderer /path/to/pdftoppm --tesseract /path/to/tesseract
python tests/test_normalize_thai.py
python scripts/build_disease_catalogue.py
```

Defaults: cohort `data/manifests/private_review_selection.csv`, rights queue
`data/manifests/rights_review_20261005.json` (explicit holds are skipped), config
`configs/thai_normalization.json`. OCR is opt-in, limited to `empty`, `garbled` and `figure_review` pages,
300 dpi, `tha+eng`, at most 60 pages per document and 400 per run. Existing output folders are never
overwritten; use a new `--out-dir` for another revision.

## Repairs, in order

Font maps (per font object, before text extraction):

1. **TH Sarabun New/PSK glyph order.** Type0 fonts whose embedded TrueType keeps the original glyph IDs
   (`maxp` ≥ 301 glyphs, `CIDToGIDMap /Identity`) get a ToUnicode map rebuilt from the glyph order:
   ASCII = GID + 0x1F, ก..ฺ = GID + 0xD2B, ฿..๛ = GID + 0xD2F, positional variants 0x156..0x170 follow
   U+F700..F71A. Existing maps must agree ≥85% on the Thai range, else the font is skipped. Compact
   subsets are skipped because their glyph IDs are renumbered.
2. **SARA AA labelled SARA AM** (`ตำรำง`, `กำแฟดำ`): a font with exactly one glyph mapped to ำ, none to า,
   and an unmapped NIKHAHIT (a U+FFFD glyph or a second SPACE glyph) gets that glyph remapped to า.
3. **NIKHAHIT labelled SPACE** (`น ้าตาล`): a second SPACE glyph immediately after the THANTHAKHAT glyph
   becomes ํ.
4. **First-cluster labels** (`คื` for ค): consonant + combining-mark labels are reduced to the consonant
   when each mark also has its own glyph in the font.

CMaps with syntax the parser cannot round-trip are left untouched. Replacement CMaps keep the font's
code width (two bytes for Type0, one byte for simple fonts).

Layout signals (same pypdf pass, plus pdfplumber geometry for pages containing `<` or `>`):

- **Underlined comparison signs.** Word-processor PDFs print ≥/≤ as `>`/`<` with a thin rule as wide as
  the glyph underneath. Such signs become ≥/≤, matched by occurrence order; if the PDF text and the
  geometry disagree on the number of signs, nothing is changed and the page becomes `degraded`.
- **Citation superscripts.** Digit runs set ≥20% smaller, raised 0.15–0.8× the body size and attached to
  the preceding word or number (or continuing a citation group after a comma/dash) become Unicode
  superscripts: `ร้อยละ 25⁷⁰`, not `2570`. Whether a run is a citation or an exponent (`kg/m²`) is not
  inferred. Body numbers after a space or slash (`อายุ 35`, `1/3`) and `3.3` are left alone.
- **Image-only figures.** Pages where images cover 25–98% of the page and the text layer has fewer than
  700 characters (or ≥98% and fewer than 150) become `figure_review`: the text layer only holds a caption.

Text (every page): NFC, then the document legacy decoder (`mac_thai`, `cp1252_cp874_tokens`, applied to
runs of legacy characters even when glued to Thai text), leaked Thai glyph names (`/ToTao` → ต), observed
C1 positional codes, Microsoft Thai PUA, symbol-font PUA removal, Thai digits → Arabic digits, spaces/line
breaks before combining marks, duplicate marks, NIKHAHIT/U+FFFD (+ optional space) + SARA AA → SARA AM,
spaces before ะ/า/ำ, letter-spaced headings, tone/vowel order and whitespace. Arabic digits and units are
never changed by text rules.

Per-document options in the config (each records its evidence): `dropped_sara_am` (consonant(+tone) +
space + SARA AA → SARA AM, only where every case was checked), `dedupe_layered_text` (drop lines whose
content already appeared on the page; DDC manual pages 7–33 carry stacked copies) and
`review_hold_pages` (page → note; known problems that need a person, e.g. an inverted ABI formula).

Running headers/footers and bare page numbers at page edges, and short lines repeated anywhere on at least
half of the pages (the HT guideline's `สงวนลิขสิทธิ์` watermark), are removed from `text` and kept in
`removed_edge_lines`.

## Output contract

`data/processed/normalized-v2/<id>/pages.jsonl` (local only, ignored like other page text):
one row per PDF page with `text` (retrieval text), `text_source` (`pdf_text_repaired` or `ocr`),
`status`, `pdf_text_status`, `review_note`, `quality`, `layout_checks`, `normalization_counts`,
`removed_edge_lines`, `pre_normalization_text`, `ocr_text`, `ocr_quality`, `printed_page_number: null`
and `human_review: null`. `normalization.json` summarizes font actions, rule totals, layout totals, review
holds, status counts and page lists; it contains no page text and is the only file from this folder
tracked in git.

Statuses: `ok`, `ok_minor_issues` (a few defects), `degraded` (1–5% defects or unverified comparison
signs; PDF text kept, review needed), `garbled` (>5% defects or NUL characters), `figure_review`
(image-only figure; OCR text, if run, is stored beside it), `review_hold` (config note from a human or
fidelity review), `empty`, and `ocr_unreviewed` (OCR filled a page without PDF text). Only `ok` and
`ok_minor_issues` should be indexed without a person checking the page. Statuses are retrieval heuristics,
not fidelity or clinical approval.

## Fixes for the 2026-10-07 fidelity review

| Finding | v2 handling |
| --- | --- |
| Underlined ≥/≤ read as >/< (CKD 2565, hemodialysis) | Converted from geometry: 26 signs on 11 pages; checked against images (CKD 2565 p29 table, anemia p57) |
| Citation superscripts merged into values (`2570`, `109`) | 720 superscript runs; `ร้อยละ 25⁷⁰`, `ร้อยละ 10⁹`, `2557⁴` |
| Image-only flowcharts marked `ok` | 45 `figure_review` pages, including all 9 DM CPG flowcharts the review listed |
| Vector flowcharts, interleaved tables, inverted ABI formula, colour-only heat map | 13 `review_hold` pages from the review's page list |
| Hidden duplicate text (DDC manual) | `dedupe_layered_text`; repeated lines removed on pages 7–33 |
| HT watermark leaking into text | Removed (watermark rule) |
| SARA AM `น�้าหนัก` (INMU), italic า→ำ (Siriraj cardiovascular), DMS p5 mojibake, CKD booklet MacRoman residue | Text rule, font rule and run-level legacy decoding; one booklet page (p23) still has residue and is no longer `ok` |
| Status missed mojibake / flagged accented names | Mojibake counted only in letter-free tokens with ≥2 accented characters |
| NUL digits and tone marks in three Siriraj leaflets | Not repairable from text (NUL replaces digits as well as tone marks); pages stay `garbled` |

## Verification

2026-10-08 (v2, 30 documents, 1766 pages): ok 1528, ok_minor_issues 73, degraded 16, garbled 7,
figure_review 45, review_hold 13, ocr_unreviewed 9, empty 75; 0 document failures.

- Every page where numbers changed between v1 and v2 was attributed: superscripts 173 pages, underlined
  signs 8, layered dedupe 27, OCR source change 2, removed running header 2 (CKD anemia).
- Pages with more defects than v1: one (CKD booklet p23, a real MacRoman residue now detected).
- Dictionary hit rate (PyThaiNLP, scratch install only): 99.2% (v1) → 99.3% (v2).
- Rendered pages compared: CKD 2565 p29 (all ten underlined `>` are ≥, including ≥120/≥70), anemia p57
  (`TSAT ≤ 20` underlined, `ferritin < 30` plain); superscript contexts sampled in five documents.
- 27 unit/integration tests, including a synthetic PDF with an underlined `>`, a raised citation group, a
  far-raised body number, an image-only page and a review hold.

v1 (2026-10-06): 0 pages worse than the first extraction, 584 improved; dictionary hit rate 92.5% → 99.2%.

## Known limits

- Superscripts made with text rise (`Ts`) are not detected; word-processor exports in this corpus raise
  them by position instead.
- `dm-remission-implementation-lessons-undated`: U+FFFD stands for several different vowels (ิ, ี, ู).
- Vector flowcharts are not detected automatically; known ones are held through the config.
- Tables are flattened text; header order can still be wrong outside the held pages.
- Tesseract Thai OCR has word/unit errors; every OCR page is `ocr_unreviewed`.
- Scope (adult/paediatric/pregnancy sections), rights and clinical review are unchanged.
