"""Verify embeddings computed elsewhere (Kaggle GPU) before they replace or join the local indexes.

Checks per `dense-<model>-t<N>` folder: files present; SHA256SUMS match; chunk_ids equal the local chunks.jsonl in order;
the chunk-file hash in the manifest equals the local file; vectors are finite, unit length and one per chunk; and a random
sample of chunks re-embedded on the CPU agrees with the GPU vectors (cosine >= 0.98; float16 usually gives about 0.999).

Usage:
    python -X utf8 scripts/verify_embedding_output.py --downloaded data/index/kaggle --chunks-root data/index --sample 40
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import embed  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--downloaded", type=Path, required=True)
    ap.add_argument("--chunks-root", type=Path, required=True, help="folder holding chunks-v11-t<N> sets")
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--min-cosine", type=float, default=0.98)
    args = ap.parse_args(argv)

    problems: list[str] = []
    sums: dict[str, str] = {}
    sums_file = args.downloaded / "SHA256SUMS"
    if sums_file.exists():
        for line in sums_file.read_text().splitlines():
            digest, rel = line.split("  ", 1)
            sums[rel.replace("\\", "/")] = digest
    else:
        problems.append("SHA256SUMS missing")
    models: dict[str, object] = {}
    report = []
    for folder in sorted(args.downloaded.glob("dense-*")):
        stem = folder.name[len("dense-"):]
        model_key, size = stem.rsplit("-t", 1)
        chunk_file = args.chunks_root / f"chunks-v11-t{size}" / "chunks.jsonl"
        result = {"folder": folder.name, "ok": True}
        for need in ("vectors.npy", "chunk_ids.json", "index_manifest.json"):
            if not (folder / need).exists():
                problems.append(f"{folder.name}: {need} missing")
                result["ok"] = False
        if not result["ok"]:
            report.append(result)
            continue
        for rel, digest in sums.items():
            if rel.startswith(folder.name + "/") and sha256(args.downloaded / rel) != digest:
                problems.append(f"{folder.name}: checksum mismatch for {rel}")
        manifest = json.loads((folder / "index_manifest.json").read_text())
        rows = [json.loads(x) for x in chunk_file.read_text(encoding="utf-8").split("\n") if x.strip()]
        ids = json.loads((folder / "chunk_ids.json").read_text(encoding="utf-8"))
        vectors = np.load(folder / "vectors.npy")
        if ids != [r["chunk_id"] for r in rows]:
            problems.append(f"{folder.name}: chunk ids differ from {chunk_file}")
        if manifest["chunks_sha256"] != sha256(chunk_file):
            problems.append(f"{folder.name}: chunk file hash differs from the local one (chunks were rebuilt?)")
        if vectors.shape[0] != len(rows) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-2):
            problems.append(f"{folder.name}: vectors wrong shape, non-finite or not unit length")
            report.append({**result, "ok": False})
            continue
        model = embed.MODELS[model_key]
        st = models.setdefault(model_key, embed.load(model))
        picks = random.Random(7).sample(range(len(rows)), min(args.sample, len(rows)))
        texts = [(rows[i]["header_text"] + "\n" if rows[i]["header_text"] else "") + rows[i]["text"] for i in picks]
        cosine = (embed.encode(st, texts, model.passage_prefix) * vectors[picks]).sum(axis=1)
        result.update(chunks=len(rows), min_cosine_vs_cpu=round(float(cosine.min()), 4), mean_cosine_vs_cpu=round(float(cosine.mean()), 4))
        if cosine.min() < args.min_cosine:
            problems.append(f"{folder.name}: GPU and CPU vectors disagree (min cosine {cosine.min():.4f})")
        report.append(result)
    print(json.dumps({"folders": report, "problems": problems}, ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
