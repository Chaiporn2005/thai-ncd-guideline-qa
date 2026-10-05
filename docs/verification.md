# Verification record

Date: 2026-10-05

## Checks completed

- Seed manifest parses and satisfies the repository schema subset checked by the validator.
- 13 candidate records; core 3, supporting 5, requires scope expansion 5.
- Human-approved / accepted records: **0**.
- All local Markdown link targets exist.
- Git staged whitespace check passed; initial research scaffold committed and pushed to `main`.
- Validator rejects the following synthetic negative cases, without modifying real source records:
  1. Accepted status without actual human approval and content QA.
  2. Invalid calendar date.
  3. Non-HTTP(S) source URL.
  4. Malformed URL.
  5. Invalid SHA-256 format.
  6. Empty human reviewer identity.
  7. QA-passed status while only a viewer was accessed.
  8. Duplicate document/edition IDs.

Command:

```powershell
python scripts/validate_manifest.py
```

The targeted negative scenarios were exercised in memory through the validator's `inspect`
function. They are validation probes, not claims of actual corpus approval or clinical testing.

## Not verified

- Complete source-content/clinical accuracy, all-page extraction fidelity or download permissions.
- Source completeness and ambiguous revision/derivative identities noted in research notes.
- 50-document/equivalent course acceptance.
- Autonomous agents, RAG demo, retrieval quality, clinical gold answers or evaluation scores.

This is a research/planning scaffold; no application benchmark results are fabricated.
