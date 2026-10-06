# Thai text normalization for retrieval review

`scripts/normalize_thai.py` re-extracts local PDFs with pypdf after deterministic in-memory font-map
repairs, normalizes Thai text and writes a separate processed root. It reads `data/raw/<id>/source.pdf`
and never modifies source PDFs or the manifest. The first-round extraction outputs it replaced were removed on
2026-10-06 (see git history at commit `7c98d8e`); `scripts/extract_pages.py` can regenerate them.
It makes no network requests or paid API calls and does not approve inclusion, rights or clinical content.

## Why

The 2026-10-06 data review found that the original extraction was unusable for retrieval in key documents:
the diabetes CPG had 207/282 pages of Latin-looking glyph IDs (digits such as `≥126` lost), the
hypertension CPG had a corrupted ToUnicode map (`หิมายถ้ง` for `หมายถึง`), one CKD booklet was
MacRoman-encoded TIS-620, and many documents lost SARA AM or tone marks. The original triage flags
missed some of these (for example the CKD booklet was reported with one encoding page).

## Commands

```powershell
$taskPython = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$pdftoppm = 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
& $taskPython 'scripts/normalize_thai.py' --out-dir 'data/processed/normalized-v1' --ocr --renderer $pdftoppm --tesseract tesseract
& $taskPython 'tests/test_normalize_thai.py'
```

Defaults: cohort `data/manifests/private_review_selection.csv`, rights queue
`data/manifests/rights_review_20261005.json` (explicit holds are skipped), config
`configs/thai_normalization.json`. OCR is opt-in, limited to `empty`/`garbled` pages, 300 dpi,
`tha+eng`, at most 60 pages per document and 400 per run. Existing output folders are never overwritten;
use a new `--out-dir` for another revision.

## Repairs, in order

Font maps (per font object, before text extraction):

1. **TH Sarabun New/PSK glyph order.** Type0 fonts whose embedded TrueType keeps the original glyph IDs
   (`maxp` ≥ 301 glyphs, `CIDToGIDMap /Identity`) get a ToUnicode map rebuilt from the glyph order:
   ASCII = GID + 0x1F, ก..ฺ = GID + 0xD2B, ฿..๛ = GID + 0xD2F, positional variants 0x156..0x170 follow
   U+F700..F71A. Existing maps must agree ≥85% on the Thai range, else the font is skipped. Compact
   subsets are skipped because their glyph IDs are renumbered.
2. **SARA AA labelled SARA AM** (`ตำรำง`): a font with exactly one glyph mapped to ำ, none to า and an
   unmapped glyph gets that glyph remapped to า.
3. **NIKHAHIT labelled SPACE** (`น ้าตาล`): a second SPACE glyph immediately after the THANTHAKHAT glyph
   becomes ํ.
4. **First-cluster labels** (`คื` for ค): consonant + combining-mark labels are reduced to the consonant
   when each mark also has its own glyph in the font.

CMaps with syntax the parser cannot round-trip are left untouched. Replacement CMaps keep the font's
code width (two bytes for Type0, one byte for simple fonts).

Text (every page): document legacy decoder (`mac_thai`, `cp1252_cp874_tokens`, from the config),
leaked Thai glyph names (`/ToTao` → ต), observed C1 positional codes, Microsoft Thai PUA, symbol-font
PUA removal, Thai digits → Arabic digits, spaces/line breaks before combining marks, duplicate marks,
NIKHAHIT/U+FFFD + SARA AA → SARA AM, spaces before ะ/า/ำ, letter-spaced headings, tone/vowel order,
NFC and whitespace. Arabic digits, units and operators are never changed. `dropped_sara_am` (config only)
turns consonant(+tone)+space+SARA AA into SARA AM for documents where every case was checked.
Running headers/footers and bare page numbers at page edges are removed and kept in `removed_edge_lines`.

## Output contract

`data/processed/normalized-v1/<id>/pages.jsonl` (local only, ignored like other page text):
one row per PDF page with `text` (retrieval text), `text_source` (`pdf_text_repaired` or `ocr`),
`status`, `quality`, `normalization_counts`, `removed_edge_lines`, `pre_normalization_text`,
`ocr_text`, `ocr_quality`, `printed_page_number: null` and `human_review: null`.
`normalization.json` summarizes font actions, rule totals, status counts and page lists; it contains no
page text and is the only file from this folder tracked in git.

Statuses: `ok`, `ok_minor_issues` (a few defects), `degraded` (1–5% defects; PDF text kept, review
needed), `garbled` (>5% defects or NUL tone marks), `empty`, and `ocr_unreviewed` (OCR replaced
unusable PDF text). Statuses are retrieval heuristics, not fidelity or clinical approval.

## Verification on 2026-10-06 (30 documents, 1766 pages)

- Rendered pages compared by eye: DM CPG p.40 (criteria ≥126/≥200/≥6.5%, Table 2), HT guideline p.30,
  CKD anemia p.20 (iron tables), CKD booklet p.20, geriatric diet p.4.
- Per-page regression check (original vs repaired text through the same text rules): 0 pages worse,
  584 pages with fewer defects.
- 17 unit tests: font repairs, decoders, text rules, quality gate, CLI rights hold and no-overwrite.
- Result: ok 1542, ok_minor_issues 116, degraded 18, ocr_unreviewed 46, empty 44; 0 document failures.

## Known limits

- `dm-remission-implementation-lessons-undated`: U+FFFD stands for several different vowels (ิ, ี, ู);
  18 pages remain `degraded`.
- `lipid-rama-education-2562`: U+FFFD stands for ำ in one Type1 font; kept as minor issues.
- pypdf still inserts occasional spaces inside words (`นั้ น`), and tables are flattened text.
- Tesseract Thai OCR has word/unit errors; every OCR page is `ocr_unreviewed`.
- Scope (adult/paediatric/pregnancy sections), rights and clinical review are unchanged.
