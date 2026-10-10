"""Build a dense index for a new chunk set by reusing the vectors of unchanged chunks and embedding only the rest (Track B).

When one document of the corpus changes, most chunks (same id, same embedded text: header + text) are identical to the old set. For
those the old vector is copied; for new or changed chunks the model embeds them now. The result is a new immutable index folder in the
order of the new chunk file, with a manifest that says how many vectors were reused and how many were computed. A reused vector is
only taken when the embedded text hashes equal, so a changed chunk can never keep a stale vector.

Usage:
    python -X utf8 scripts/splice_index.py --old-chunks data/index/chunks-v11-t128 --old-index data/index/kaggle/dense-bge-m3-t128 \
        --new-chunks data/index/chunks-v12-t128 --model bge-m3 --out data/index/dense-bge-m3-t128-v12
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import embed  # noqa: E402
from ncdqa.retrieval.dense import DenseIndex  # noqa: E402


def embedded_text(c: dict) -> str:
    return (c["header_text"] + "\n" if c["header_text"] else "") + c["text"]


def read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--old-chunks", type=Path, required=True)
    ap.add_argument("--old-index", type=Path, required=True)
    ap.add_argument("--new-chunks", type=Path, required=True)
    ap.add_argument("--model", choices=sorted(embed.MODELS), required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: indexes are immutable")

    model = embed.MODELS[args.model]
    old_rows, new_rows = read(args.old_chunks / "chunks.jsonl"), read(args.new_chunks / "chunks.jsonl")
    old_index = DenseIndex.load(args.old_index)
    if old_index.chunk_ids != [r["chunk_id"] for r in old_rows]:
        sys.exit("old index and old chunk file do not line up")
    old_pos = {r["chunk_id"]: (i, hashlib.sha256(embedded_text(r).encode("utf-8")).hexdigest()) for i, r in enumerate(old_rows)}
    vectors = np.zeros((len(new_rows), old_index.vectors.shape[1]), dtype=np.float32)
    todo = []
    for i, r in enumerate(new_rows):
        hit = old_pos.get(r["chunk_id"])
        if hit and hit[1] == hashlib.sha256(embedded_text(r).encode("utf-8")).hexdigest():
            vectors[i] = old_index.vectors[hit[0]]
        else:
            todo.append(i)
    started = time.time()
    if todo:
        vectors[todo] = embed.encode(embed.load(model), [embedded_text(new_rows[i]) for i in todo], model.passage_prefix, batch_size=16)
    index = DenseIndex(vectors, [r["chunk_id"] for r in new_rows])
    index.save(args.out)
    old_manifest = json.loads((args.old_index / "index_manifest.json").read_text(encoding="utf-8"))
    chunk_file = (args.new_chunks / "chunks.jsonl").resolve()
    manifest = {**{k: old_manifest[k] for k in ("model", "hf_id", "query_prefix", "passage_prefix", "max_seq_length", "dimension") if k in old_manifest},
                "chunks": len(new_rows), "chunks_file": str(chunk_file.relative_to(ROOT)),
                "chunks_sha256": hashlib.sha256(chunk_file.read_bytes()).hexdigest(),
                "vectors_sha256": hashlib.sha256((args.out / "vectors.npy").read_bytes()).hexdigest(),
                "spliced_from": {"old_index": str(args.old_index), "old_device": old_manifest.get("device"), "old_dtype": old_manifest.get("dtype"),
                                 "vectors_reused": len(new_rows) - len(todo), "vectors_computed_now": len(todo),
                                 "computed_device": "cpu float32", "computed_seconds": round(time.time() - started, 1)},
                "device": "mixed (reused: " + str(old_manifest.get("device")) + " " + str(old_manifest.get("dtype", "float32")) + "; new: cpu float32)",
                "header_text_embedded": True}
    (args.out / "index_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(manifest["spliced_from"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
