"""Kaggle GPU kernel: embed chunk sets with e5-base and bge-m3 (Track B). Self-contained; no repo clone needed.

Input : a private Kaggle dataset mounted under /kaggle/input/ holding folders chunks-v11-t<N>/chunks.jsonl
        (produced by scripts/build_chunks.py; sizes 128, 256, 384, 512).
Output: /kaggle/working/dense-<model>-t<N>/{vectors.npy, chunk_ids.json, index_manifest.json}, SHA256SUMS and summary.json.

Safety against losing work: every finished combination is written to disk at once and checked (row count, no NaN, unit
norm); a failure in one combination is recorded in summary.json and the others still run; a finished folder is skipped,
so re-running resumes. Download /kaggle/working immediately after the run and verify it with
scripts/verify_embedding_output.py before deleting anything on Kaggle or locally.
"""
import glob
import hashlib
import json
import os
import platform
import time
import traceback

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODELS = {
    "e5-base": ("intfloat/multilingual-e5-base", "passage: "),
    "bge-m3": ("BAAI/bge-m3", ""),
}
MAX_SEQ = 512
OUT = "/kaggle/working"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


summary = []
for chunk_file in sorted(glob.glob("/kaggle/input/**/chunks-*/chunks.jsonl", recursive=True)):
    name = os.path.basename(os.path.dirname(chunk_file)).replace("chunks-v11-", "")
    rows = [json.loads(x) for x in open(chunk_file, encoding="utf-8").read().split("\n") if x.strip()]
    texts = [(r["header_text"] + "\n" if r["header_text"] else "") + r["text"] for r in rows]
    for key, (hf_id, prefix) in MODELS.items():
        folder = f"{OUT}/dense-{key}-{name}"
        entry = {"combination": f"{key}-{name}", "chunks": len(rows)}
        try:
            if os.path.exists(f"{folder}/index_manifest.json"):
                entry["status"] = "skipped_already_done"
                summary.append(entry)
                continue
            model = SentenceTransformer(hf_id, device="cuda")
            model.half()
            model.max_seq_length = MAX_SEQ
            start = time.time()
            vectors = model.encode([prefix + t for t in texts], batch_size=64, normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
            elapsed = time.time() - start
            assert vectors.shape[0] == len(rows), "row count differs from chunk count"
            assert np.isfinite(vectors).all(), "NaN or inf in vectors"
            norms = np.linalg.norm(vectors, axis=1)
            assert np.allclose(norms, 1.0, atol=1e-2), f"vectors not unit length (min {norms.min()}, max {norms.max()})"
            os.makedirs(folder, exist_ok=True)
            np.save(f"{folder}/vectors.npy", vectors)
            json.dump([r["chunk_id"] for r in rows], open(f"{folder}/chunk_ids.json", "w", encoding="utf-8"))
            manifest = {"model": key, "hf_id": hf_id, "passage_prefix": prefix, "max_seq_length": MAX_SEQ,
                        "dimension": int(vectors.shape[1]), "chunks": len(rows), "chunks_sha256": sha256(chunk_file),
                        "vectors_sha256": sha256(f"{folder}/vectors.npy"), "embed_seconds": round(elapsed, 1),
                        "device": "cuda", "gpu": torch.cuda.get_device_name(0), "dtype": "float16",
                        "python": platform.python_version(), "torch": torch.__version__, "header_text_embedded": True}
            json.dump(manifest, open(f"{folder}/index_manifest.json", "w"), indent=1)  # written last: marks the folder complete
            entry.update(status="done", embed_seconds=manifest["embed_seconds"])
            del model
            torch.cuda.empty_cache()
        except Exception:
            entry.update(status="failed", error=traceback.format_exc()[-600:])
        summary.append(entry)
        print(json.dumps(entry), flush=True)

json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
with open(f"{OUT}/SHA256SUMS", "w") as f:
    for path in sorted(glob.glob(f"{OUT}/dense-*/*")):
        f.write(f"{sha256(path)}  {os.path.relpath(path, OUT).replace(os.sep, '/')}\n")
print("finished", json.dumps([e["status"] for e in summary]))
