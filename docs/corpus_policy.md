# Corpus policy

## Scope

Core: Thai adult type 2 diabetes, hypertension and dyslipidemia guidelines.
Optional: adult CKD material relevant to comorbidity/follow-up.
Clinical, service and public education sources remain separately typed.
Pediatric, pregnancy and unrelated documents are excluded unless the scope is explicitly expanded.

## Thai population requirement

The user requested information about Thai people. The current seeds are Thai guidance/service
materials, not proof of primary research on Thai participants. `thai_context` records this distinction.
Empirical research/statistics must identify a Thai sample/population from methods or source metadata.
Thai-language writing or Thai authorship alone does not qualify a study as Thai-population evidence.
International references within Thai guidelines must remain identifiable; never recast them as Thai data.
The user confirmed Thai-applicable guidance, rather than exclusively Thai-participant research.
Foreign studies can remain cited within Thai guidelines; their original population must not be misrepresented.

## Inclusion gates

1. Discover a specific document, not just a website category or search snippet.
2. Verify publisher, title, edition and audience on the issuer's landing page/document.
3. Retrieve content through a legitimate channel; record access failures without bypassing them.
4. Extract and compare reading order, numbers, units, negations, conditions and footnotes with source pages.
5. Deduplicate copies and compare uncertain edition relationships.
6. Obtain human inclusion review; seek competent domain review for clinical gold answers.
7. Set `accepted` only after content, extraction and approval gates pass.

`source_verified` only verifies source identity; it is not content or clinical approval.
Stage transitions can be rejected or sent back with reasons. Never advance records merely to reach a quota.

## Identity and counting

- `document_id`: stable record for a particular edition.
- `work_id`: underlying authored work across editions/copies.
- `edition_id`: version-specific identity.
- `alternate_urls`: mirrors/layout variants for the same record, not separate documents.
- `sha256`: actual bytes hash, only after downloading; null before then.
- Preserve differing editions. Do not automatically count historical editions toward the course minimum.
- Report unique works, accepted works, editions, file copies, pages and chunks separately.
- Instructor clarification is needed for an equivalent corpus when fewer than 50 independent documents are used.

## Rights

Public access is not redistribution permission. Record `unknown`, `restricted`, or
`permitted` with evidence; a permission decision must name the actual terms.
Metadata-only repository publishing can proceed while PDFs remain local and ignored.
Rights review for local processing and redistribution are separate decisions.
Do not remove copyright notices or upload raw sources by default, including to a private repository.

## Provenance

Record actual accessed date, tool/agent, verification depth and source URLs.
Do not substitute upload date for publication date. Unknown date stays null.
Keep page numbers, section path, table/figure names and evidence spans during extraction.
Keep retrieval-visible content separate from agent control prompts.

## Review questions

- Does this source fit the disease, adult population and intended question type?
- Does the edition conflict with another version, and is the relationship known?
- Was a full document retrieved, or only a publisher page / Drive viewer?
- Are numeric thresholds, units and exceptions faithfully extracted?
- Is the candidate a distinct work or a mirrored/layout copy?
- What use/redistribution is permitted, and what still needs review?
