"""Rankings of variant D (BM25 only) in the same file format as Track B's saved runs, so run_generation.py can answer from them (Track C).

    python -X utf8 scripts/bm25_rankings.py --questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl \
        --chunks data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl --out data/index/runs/bm25_only

Same index as variant B's lexical half (frozen_v1): Thai BM25 over the 512-token parent chunks with their headers, character 3-grams for Thai text and whole words for Latin,
k1 2.18, b 0.86. No dense vector and no fusion, so D isolates what lexical matching alone gives. Writes <out>/{dev,test}-D/results.jsonl, one row per gold question with
the top 10 chunks (rank, chunk_id, score, document_id, edition_id, pdf_page_start, pdf_page_end), like data/handoff/.../results/*-A|B|C/results.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.retrieval.bm25 import BM25Index, tokenize_units  # noqa: E402
from ncdqa.retrieval.thai_tokens import tokenize  # noqa: E402

K1, B, K = 2.18, 0.86, 10


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        sys.exit(f"{args.out} exists, choose a new --out")
    units = [json.loads(x) for x in args.chunks.read_text(encoding="utf-8").split(chr(10)) if x.strip()]
    index = BM25Index([u["chunk_id"] for u in units], tokenize_units(units, "char3", (), True), K1, B)
    by_id = {u["chunk_id"]: u for u in units}
    questions = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split(chr(10)) if x.strip()]
    questions = [q for q in questions if q["status"] == "gold" and q["split"] in ("dev", "test")]
    for split in ("dev", "test"):
        rows = []
        for q in (q for q in questions if q["split"] == split):
            hits = index.top(tokenize(q["question"], "char3", ()), K)
            rows.append({"run_id": f"{split}-D-bm25", "qid": q["qid"], "variant": "D", "k": K, "query": q["question"],
                         "hits": [{"rank": i, "chunk_id": cid, "score": round(s, 5), "document_id": by_id[cid]["document_id"], "edition_id": by_id[cid]["edition_id"],
                                   "pdf_page_start": by_id[cid]["pdf_page_start"], "pdf_page_end": by_id[cid]["pdf_page_end"]} for i, (cid, s) in enumerate(hits, 1)]})
        dest = args.out / f"{split}-D"
        dest.mkdir(parents=True)
        (dest / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in rows), encoding="utf-8", newline=chr(10))
        empty = sum(1 for r in rows if not r["hits"])
        print(split, len(rows), "questions,", empty, "with no BM25 hit at all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
