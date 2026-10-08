# PART 3 OCR image review

Completed all 30 assigned pages in pages_part3.json order. No unfinished or missing keys.

## Verdict counts

| Verdict | Pages |
| --- | ---: |
| text_ok | 1 |
| fixed | 0 |
| content_missing | 28 |
| text_invented | 1 |
| unreadable | 0 |
| blank_ok | 0 |

## Edits by kind

| Kind | Edits |
| --- | ---: |
| number | 7 |
| sign | 1 |
| unit | 0 |
| drug | 2 |
| word | 104 |
| remove | 25 |

Total: 139 exact edits. Each is a proposal for supervisor and human review; none was applied to the corpus.

## Pages with number, sign or unit edits

- `ncd-ddc-health-literacy-fight-ncds-2566:p5` (number, 5 edit(s)): The contents image pairs the section heading with the first page number and each following title with the next number; OCR shifted all pairings by one row.
- `ncd-ddc-health-literacy-fight-ncds-2566:p8` (sign, 1 edit(s)): Green waist-size wedge shows division sign ÷ 2, not equals.
- `ncd-ddc-health-literacy-fight-ncds-2566:p20` (number, 1 edit(s)): BMI last row prints 30 ขึ้นไป.
- `ncd-ddc-health-literacy-fight-ncds-2566:p59` (number, 1 edit(s)): Formula shows superscript 2 on height in metres, omitted in OCR.

No unit edits were proposed.

## Material findings and limitations

- PDF p5: contents-page numbers were associated with the wrong titles in all five sections.
- PDF p8: height divided by 2 was transcribed as equals 2; both zero labels for alcohol/smoking are missing.
- PDF p29: all six central hypertension-prevention captions are absent.
- PDF p38: omitted งด in เจาะเลือดหลังงดอาหาร changes the fasting condition; exact word correction proposed.
- PDF p56: five written warnings were invented from pictures. PDF p84 still contains five model-written picture descriptions, despite the TASK background saying such descriptions had been removed.
- PDF p59: the height-squared exponent in the BMI formula was omitted.
- PDF p65: two ingredient names are paired with the wrong sodium quantities; oyster sauce 1 tablespoon / 518 mg is missing.
- Repeated sidebar, logo and footer omissions are included in content_missing. This verdict does not imply every page is missing central clinical prose; the missing field distinguishes what is absent.
- Some pages combine sidebars and central content into false hierarchies or table associations (p26, p44, p72, p93). These are described for reconstruction; HTML/Markdown styling itself was not treated as an error.
- Small illustration labels/digits that could not be read confidently have no guessed replacements. p56 coat caption is partly occluded; p62 device display remains uncertain. All assigned pages were reviewed, but these small regions remain for human review.
- Source clinical/statistical claims were compared with the image only; this is not clinical approval or independent validation.

## Validation

- Re-checked every old substring against the current normalized-v9 text: **139 / 139 edits occur exactly once**; each occurrences field is 1.
- Confirmed 30 unique keys, exact input order/group, exact result/edit field sets, valid verdict/kind/confidence values, and nonempty missing descriptions for content_missing.
- Confirmed edits do not overlap and can be applied sequentially in memory without losing later old substrings. In-memory validation did not write revised corpus text.
- JSONL was split only on "\n", not splitlines().
- Source pages.jsonl SHA-256 at validation: `a785ed3990b6d050907a190bfe9e463e36e6e654be3f36bd2663c7737f0d2a71`.
- All 30 supplied PNGs were opened with the image-viewing tool. Selected 200 dpi PDF crops were additionally rendered and viewed; zoom_used records those pages.
- The instructed .venv-ingest Python lacks pypdfium2 (ModuleNotFoundError). Used its Python for JSON processing and validation; used the already-installed system Python/pypdfium2 for local rendering. No installation, network, OCR or API request was made.
- Writes are confined to data/agent_runs/20261008-codex-reocr/: findings, this summary, part3 batch/validation scripts and zoom/part3-* crops. No git command, .env read, manifest or corpus edit.
- Reproduce validation: `.venv-ingest/Scripts/python.exe -X utf8 data/agent_runs/20261008-codex-reocr/validate_part3.py`.

## Unfinished pages

None. Missing keys: none.
