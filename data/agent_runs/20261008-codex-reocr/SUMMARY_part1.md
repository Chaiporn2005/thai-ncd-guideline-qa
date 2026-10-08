# PART 1 — OCR image comparison

Reviewed all 30 assigned PNGs against the current normalized-v9 `text`, with 200 dpi PDF crops where needed. JSONL was split on `"\n"` only. Findings were written incrementally in assignment order.

## Verdict counts

| Verdict | Pages |
| --- | ---: |
| text_ok | 0 |
| fixed | 1 |
| content_missing | 29 |
| text_invented | 0 |
| unreadable | 0 |
| blank_ok | 0 |

## Edit counts

| Kind | Edits |
| --- | ---: |
| number | 13 |
| sign | 0 |
| unit | 0 |
| drug | 1 |
| word | 100 |
| remove | 23 |
| Total | 137 |

## Pages with number, sign, or unit edits

- `ncd-ddc-health-literacy-fight-ncds-2566:p6`: number=12
- `ncd-ddc-health-literacy-fight-ncds-2566:p54`: number=1

Numeric edits repair the contents-page number associations (PDF p6) and numbered stroke-risk items (PDF p54). No sign or unit edits were proposed.

## Unfinished pages

None. Missing assigned keys: `[]`.

## Review notes

- `content_missing` takes precedence when an otherwise corrected page still omits printed content. It includes omitted page numbers, navigation tabs, logos, figure labels, or fine print, not only missing clinical text. Each affected page also retains all identified exact edits.
- Material omissions include the endocrine-system complication on PDF p60, the chocolate-label attribution on p73, and “No sugar” plus the “จริง” stamp on p85.
- Text invented by OCR remains on several inputs despite the task background: repeated disease lists, image descriptions, and a diabetes introductory sentence. Deletions/replacements are included in the findings. `fixed` means covered by proposed edits, not applied to the corpus.
- Retained source-specific wording and numbers, including BMI 18.8–22.9 on p39 and the wording on p85. This review establishes image/text fidelity only.
- Navigation tabs were sometimes used as Markdown section headings for unrelated advice. This is recorded in notes; no general formatting or spacing cleanup was attempted.
- Partially obscured/tiny figure lettering is flagged rather than completed by guesswork (notably p51 and p69). No unreadable digits were replaced.
- Zoom used on PDF pages: 6, 9, 12, 18, 42, 51, 60, 66, 69, 79, 82, 88.
- The specified `.venv-ingest` Python lacked pypdfium2. Rendering used that same interpreter with the existing system site-packages path added for pypdfium2; no package installation, network, OCR, or API call was made.

## Validation

- Re-read the final findings and current source text; all **137 edits** have an `old` substring occurring **exactly once** in the original page text, matching `occurrences: 1`.
- Verified exactly 30 unique keys in pages_part1.json order, correct copied groups, exact result/edit key sets, valid verdicts/kinds/confidences, and required missing descriptions.
- Verified non-overlapping old spans and sequential in-memory application of all edits; empty replacements are only kind `remove`. No corpus changes were applied.
- Wrote only within data/agent_runs/20261008-codex-reocr/. No git, manifest, governance, or corpus mutations; no .env reads. No human approval was claimed.
- Final findings SHA-256: `0b44a688aa0497c37bcd0844e0baf6ce61a58d81d865a6d9c0a17e73881900aa`.
- Source pages.jsonl SHA-256 at validation: `a785ed3990b6d050907a190bfe9e463e36e6e654be3f36bd2663c7737f0d2a71`.

Validation command: `.venv-ingest/Scripts/python.exe -X utf8 -B data/agent_runs/20261008-codex-reocr/finalize_part1.py`
