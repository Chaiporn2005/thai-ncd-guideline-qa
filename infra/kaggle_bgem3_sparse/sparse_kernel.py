"""Kaggle GPU kernel: bge-m3's own sparse (lexical weights) and ColBERT/dense/sparse pair scores (Track B). Self-contained.

Input (private dataset): children.jsonl (chunk_id, text = embedded text of the 128-token chunks), candidates.jsonl and units.jsonl
(from scripts/run_retrieval.py --export-candidates; questions + their top-30 hybrid parent candidates + parent texts).
Output (/kaggle/working):
  sparse_top100.jsonl  per question: the 100 child chunks with the highest sparse score (sum of query weight x chunk weight on shared tokens)
  pair_scores.jsonl    per (qid, parent): colbert, sparse, dense scores and the model's weighted sum, via BGEM3FlagModel.compute_score
  summary.json
Only dev questions are in the input; no test question is scored here.
"""
import glob
import json
import os
import time
from collections import defaultdict

import torch

os.system("pip install -q FlagEmbedding")
from FlagEmbedding import BGEM3FlagModel  # noqa: E402

OUT = "/kaggle/working"
find = lambda name: sorted(glob.glob(f"/kaggle/input/**/{name}", recursive=True))[0]
rd = lambda p: [json.loads(x) for x in open(p, encoding="utf-8").read().split("\n") if x.strip()]
children, cands, units = rd(find("children.jsonl")), rd(find("candidates.jsonl")), {r["chunk_id"]: r["text"] for r in rd(find("units.jsonl"))}

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, devices="cuda:0")  # one device: with two GPUs the library starts worker processes that re-run this script
t0 = time.time()
enc = model.encode([c["text"] for c in children], batch_size=64, max_length=512, return_dense=False, return_sparse=True, return_colbert_vecs=False)
inv = defaultdict(list)
for i, w in enumerate(enc["lexical_weights"]):
    for tok, val in w.items():
        inv[tok].append((i, float(val)))
qenc = model.encode([c["question"] for c in cands], batch_size=32, max_length=512, return_dense=False, return_sparse=True, return_colbert_vecs=False)
with open(f"{OUT}/sparse_top100.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for c, qw in zip(cands, qenc["lexical_weights"]):
        score = defaultdict(float)
        for tok, val in qw.items():
            for i, dv in inv.get(tok, []):
                score[i] += float(val) * dv
        top = sorted(score.items(), key=lambda kv: -kv[1])[:100]
        f.write(json.dumps({"qid": c["qid"], "hits": [{"chunk_id": children[i]["chunk_id"], "score": s} for i, s in top]}) + "\n")
t_sparse = time.time() - t0

t1 = time.time()
pairs, keys = [], []
for c in cands:
    for cand in c["candidates"]:
        pairs.append([c["question"], units[cand["chunk_id"]]])
        keys.append((c["qid"], cand["chunk_id"]))
scores = model.compute_score(pairs, batch_size=16, max_passage_length=512, weights_for_different_modes=[0.4, 0.2, 0.4])
with open(f"{OUT}/pair_scores.jsonl", "w", encoding="utf-8", newline="\n") as f:
    for k, (qid, cid) in enumerate(keys):
        f.write(json.dumps({"qid": qid, "chunk_id": cid, "colbert": float(scores["colbert"][k]), "sparse": float(scores["sparse"][k]),
                            "dense": float(scores["dense"][k]), "colbert+sparse+dense": float(scores["colbert+sparse+dense"][k])}) + "\n")
json.dump({"children": len(children), "queries": len(cands), "pairs": len(pairs), "sparse_seconds": round(t_sparse, 1),
           "pair_seconds": round(time.time() - t1, 1), "gpu": torch.cuda.get_device_name(0), "dtype": "float16",
           "weights_colbert_sparse_dense": [0.4, 0.2, 0.4]}, open(f"{OUT}/summary.json", "w"), indent=1)
print("done")
