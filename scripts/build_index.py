"""Embed a chunk set with one model and save an exact dense index (Track B, L1).

Usage:
    python -X utf8 scripts/build_index.py --chunks data/index/chunks-v11-t256 --model e5-base --out data/index/dense-e5-base-t256
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import embed  # noqa: E402
from ncdqa.retrieval.dense import DenseIndex  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--model", choices=sorted(embed.MODELS), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--limit", type=int, help="embed only the first N chunks (smoke test)")
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: indexes are immutable, choose a new --out")

    model = embed.MODELS[args.model]
    chunk_file = (args.chunks / "chunks.jsonl").resolve()
    chunks = [json.loads(x) for x in chunk_file.read_text(encoding="utf-8").split("\n") if x.strip()][:args.limit]
    texts = [(c["header_text"] + "\n" if c["header_text"] else "") + c["text"] for c in chunks]

    import torch
    import sentence_transformers
    st = embed.load(model)
    started = time.time()
    vectors = embed.encode(st, texts, model.passage_prefix, batch_size=args.batch_size, show_progress=True)
    elapsed = time.time() - started
    index = DenseIndex(vectors, [c["chunk_id"] for c in chunks])
    index.save(args.out)
    manifest = {"model": model.key, "hf_id": model.hf_id, "query_prefix": model.query_prefix,
                "passage_prefix": model.passage_prefix, "max_seq_length": model.max_seq_length,
                "dimension": int(vectors.shape[1]), "chunks": len(chunks), "chunks_file": str(chunk_file.relative_to(ROOT)),
                "chunks_sha256": hashlib.sha256(chunk_file.read_bytes()).hexdigest(),
                "vectors_sha256": hashlib.sha256((args.out / "vectors.npy").read_bytes()).hexdigest(),
                "embed_seconds": round(elapsed, 1), "chunks_per_second": round(len(chunks) / elapsed, 2), "device": "cpu",
                "machine": platform.processor() or platform.machine(), "python": platform.python_version(),
                "torch": torch.__version__, "sentence_transformers": sentence_transformers.__version__,
                "header_text_embedded": True}
    (args.out / "index_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
