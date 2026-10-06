# RAG status

- Owner role: rag_engineer
- Active session / last run: none / 20261006-rag-design (design complete; implementation not started)
- Updated: 2026-10-06
- State: design_ready_implementation_not_started

## Evidence

มี [architecture design](../../docs/rag_architecture.md) และแผนใน [plan.md](../../plan.md);
ยังไม่มี retrieval implementation, index, LLM/provider หรือ Q&A demo; accepted corpus0

## Next / dependencies

เมื่อมี accepted corpusและสิทธิใช้ RAGชัดเจน: token-aware chunking → SentenceTransformers CPU dense baseline
→ BM25/RRF variant → citation-aware demo; กำหนด provider/model/tool ที่ทีมเลือกจริง
บันทึก corpus/config version และคำสั่ง reproduce ทุก experiment

## Resources

เครื่อง/โมเดลยังไม่กำหนด; ไม่มี active claim หรือ paid API allocation
