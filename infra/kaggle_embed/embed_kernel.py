"""Kaggle GPU kernel: embed chunk sets with e5-base and bge-m3 (Track B). Self-contained; no repo clone needed.

Input : a private Kaggle dataset mounted at /kaggle/input/<dataset>/ holding folders chunks-v11-t256/ and chunks-v11-t512/
        (each with chunks.jsonl, produced by scripts/build_chunks.py).
Output: /kaggle/working/dense-<model>-<chunkset>/{vectors.npy, chunk_ids.json, index_manifest.json}
Vectors are computed exactly as scripts/build_index.py does on CPU (header_text + text, passage prefix, L2-normalized),
only in float16 on the GPU, so the manifest records device=cuda and dtype for the audit.
"""
import glob
import hashlib
import json
import os
import platform
import time

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

MODELS = {
    "e5-base": ("intfloat/multilingual-e5-base", "passage: "),
    "bge-m3": ("BAAI/bge-m3", ""),
}
MAX_SEQ = 512
OUT = "/kaggle/working"

for chunk_file in sorted(glob.glob("/kaggle/input/*/chunks-*/chunks.jsonl")):
    name = os.path.basename(os.path.dirname(chunk_file)).replace("chunks-", "")
    rows = [json.loads(x) for x in open(chunk_file, encoding="utf-8").read().split("\n") if x.strip()]
    texts = [(r["header_text"] + "\n" if r["header_text"] else "") + r["text"] for r in rows]
    for key, (hf_id, prefix) in MODELS.items():
        model = SentenceTransformer(hf_id, device="cuda")
        model.half()
        model.max_seq_length = MAX_SEQ
        start = time.time()
        vectors = model.encode([prefix + t for t in texts], batch_size=64, normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
        elapsed = time.time() - start
        folder = f"{OUT}/dense-{key}-{name}"
        os.makedirs(folder, exist_ok=True)
        np.save(f"{folder}/vectors.npy", vectors)
        json.dump([r["chunk_id"] for r in rows], open(f"{folder}/chunk_ids.json", "w", encoding="utf-8"))
        manifest = {"model": key, "hf_id": hf_id, "passage_prefix": prefix, "max_seq_length": MAX_SEQ,
                    "dimension": int(vectors.shape[1]), "chunks": len(rows),
                    "chunks_sha256": hashlib.sha256(open(chunk_file, "rb").read()).hexdigest(),
                    "vectors_sha256": hashlib.sha256(open(f"{folder}/vectors.npy", "rb").read()).hexdigest(),
                    "embed_seconds": round(elapsed, 1), "device": "cuda", "gpu": torch.cuda.get_device_name(0),
                    "dtype": "float16", "python": platform.python_version(), "torch": torch.__version__,
                    "header_text_embedded": True}
        json.dump(manifest, open(f"{folder}/index_manifest.json", "w"), indent=1)
        print(json.dumps(manifest), flush=True)
        del model
        torch.cuda.empty_cache()
