# 0007 — NCD RAG architecture design

- Date: 2026-10-06
- Owner: coordinator
- Run: 20261006-rag-design
- User request: design a RAG system based on the attached sketch and show how it fits this project

Record the proposed project architecture in docs/rag_architecture.md:
multi-agent source collection, human/corpus gates, page-grounded chunking,
CPU dense baseline, Thai BM25/RRF variant, metadata eligibility checks,
evidence citations, clarification/abstention, and comparable evaluation.

Adapt the sketch by keeping rights and answer rules as deterministic
metadata/code/config, not as retrieved clinical content in the vector database.
Keep the lexical index separate from vector retrieval. A reranker remains optional
after comparative experiments. Do not name an unselected vector backend,
LLM/provider, or answer model as chosen.

This is a design artifact, not working software or clinical approval. The corpus
currently has zero accepted documents, and all55selected candidates remain under
RAG-use rights/content review. Keep source body files ignored and unindexed until
required permissions and human/content approval are recorded.
