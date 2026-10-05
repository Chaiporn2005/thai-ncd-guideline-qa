# 0004 — Local retrieval and extraction preparation

- Date: 2026-10-05
- Status: accepted within existing user authorization
- User request: ทำต่อให้หน่อย, following the 55-source collection handoff
- Interpretation: next documented step is legitimate local retrieval, hash/page provenance,
  extraction triage and review queues, not automatic clinical acceptance.

Public issuer download links can be used to retrieve local review copies. This does not
establish permission to publish PDFs, redistribute extracted text, or deploy a public RAG.
Keep copies/text/OCR/images local and ignored; keep actual restrictions in a separate rights queue.
Explicitly restricted reuse is held from RAG until reviewed. Unknown redistribution remains unknown.
No login/CAPTCHA/403 bypass, altered user-agent impersonation, credential use or stealth fallback.
Known blocked issuer URL may be replaced only with an already verified legitimate public mirror;
its identity/edition relationship remains a review item.

Implement explicit foreground CLI tools for bounded download and extraction, with cache integrity,
safe local paths, PDF validation, failure accounting and resumable outputs. No watcher or autonomous
agent dispatcher. Maximum30 full-download attempts per registered batch; request timeout30seconds;
maximum10 requests/host/minute. Batch01/02 process the selected55 work IDs, with batch03 reserved
for actual public PDF links resolved by scouts. No paid API, LLM generation or embedding run.

Root is sole canonical curator. Two verifier scouts inspect rights/viewer links without PDF-body
downloads; a third extractor worker proposes local extraction code/tests in an isolated output folder.
Root combines outputs and runs tools. Actual extraction is not layout/numeric/clinical QA.
Human acceptance and competent clinical review remain required by corpus policy.
