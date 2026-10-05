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
# Workflow organization — 2026-10-05

ปรับรูปแบบจาก local kaggle-team โดยเพิ่ม Protocol/Orchestra, ownership,
6 workstreams, proposals/decisions, HANDOFF/PROGRESS/run log และ read-only CLI
คง canonical manifest และข้อกำหนด Thai guidance/course เดิม

ตรวจบน bundled Python ใน workspace:

- `python scripts/orchestra.py check`: ผ่าน registry, required files และ local inline Markdown links
- `python scripts/orchestra.py status`: อ่าน manifest จริง 13 source_verified; accepted 0;
  core 3, supporting 5, requires_scope_expansion 5; ไม่ dispatch agents
- Registry negative checks แบบ in-memory ผ่าน 8 กรณี: duplicate IDs, dependency cycle,
  unknown dependency, path escape, missing prompt, role/prompt mismatch, shared status และ non-object registry
- `python scripts/validate_manifest.py`: ผ่าน 13 records; ไม่มี accepted record
- `git diff --check` และ `git diff --cached --check`: ผ่านทั้งก่อนและหลัง stage
- `git diff --exit-code HEAD -- data/manifests/documents.jsonl`: ผ่าน; seed manifest ไม่เปลี่ยน

ตรวจเฉพาะ file-based workflow/config/link destinations ไม่ตรวจ Markdown anchors,
remote source content, clinical accuracy, actual resource telemetry หรือ runtime enforcement
ไม่มี retrieval/evaluation experiment, paid API runner, watcher หรือ worker ใหม่ถูกรันในรอบนี้
