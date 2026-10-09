# Retrieval data contract (Track B)

Schemas for files exchanged between corpus (A), retrieval (B), evaluation (C) and answer/demo (D).
Status: **draft for team agreement** — change a field only after the affected owners agree.

| Schema | File | Writer | Readers |
| --- | --- | --- | --- |
| [page_input](page_input.schema.json) | `data/processed/<root>/<document_id>/pages.jsonl` | A (`scripts/normalize_thai.py`) | B |
| [chunk](chunk.schema.json) | `chunks.jsonl` | B | C, D |
| [retrieval_result](retrieval_result.schema.json) | `results.jsonl` | B | C, D |
| [run_manifest](run_manifest.schema.json) | `run_manifest.json` | B | C |
| [question](question.schema.json) | `questions.jsonl` | C (silver drafted by agent, gold reviewed by a person) | B, C, D |

Validate any file:

```powershell
python scripts/validate_rag_jsonl.py chunk path/to/chunks.jsonl
python tests/test_rag_schemas.py
```

## Rules that the schemas cannot enforce alone

**Corpus version.** `corpus_version` names the processed root (for example `normalized-v1`) plus the
document manifest that lists accepted documents. A retrieval run only uses documents whose manifest
`status` is `accepted`. A changed processed root or manifest is a new corpus version.

**Which pages may be indexed** (B's intake check):

| Page `status` | Indexed when |
| --- | --- |
| `ok`, `ok_minor_issues` | always (if the document is accepted) |
| `degraded`, `ocr_unreviewed` | only with `human_review.outcome` = `pass` or `fix` |
| `garbled` | never |
| `empty` | never (page number is still kept) |

**Edition.** Page rows do not carry `edition_id`; B joins it from `data/manifests/documents.jsonl`
by `document_id`.

**Chunk text is verbatim.** `text` is an exact span of the page `text` from `char_start` (start page) to
`char_end` (end page). `header_text` is stored separately and only prepended at embedding time.

**Relevance rule** (proposal D-RAG-008, needs C's agreement): a retrieved chunk is relevant to a
question when its `edition_id` equals an evidence `edition_id`, the evidence `pdf_page` lies within
`pdf_page_start..pdf_page_end`, and at least half of the evidence `quote` (after collapsing whitespace)
appears in the chunk `text`. Questions with `answerable: false` are excluded from Recall@k.

**Gold evidence is page/quote based**, not chunk based, so gold stays valid when chunking changes.

**Test split.** Rows with `split: test` must be `gold` (or `rejected`). Tuning uses `dev` only; a test
run happens once per frozen configuration and its manifest must have `git_dirty: false`.
