"""Kaggle GPU kernel: re-score retrieval candidates with a cross-encoder reranker (Track B). Self-contained.

Input : a private dataset with candidates.jsonl (qid, question, candidates[{chunk_id,...}]) and units.jsonl (chunk_id, text)
        written by scripts/export_candidates.py.
Output: /kaggle/working/rerank_scores_<model>.jsonl (qid, chunk_id, score) and summary.json. A model that fails is recorded and
        the others still run; finished files are skipped on a re-run.
Model : BAAI/bge-reranker-v2-m3 (Apache-2.0, 568M parameters, multilingual cross-encoder; checked on the Hugging Face Hub).
"""
import glob
import json
import os
import time
import traceback

import numpy as np
import torch
from sentence_transformers import CrossEncoder

MODELS = {"bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3"}
MAX_LEN = 512
OUT = "/kaggle/working"

cand_file = sorted(glob.glob("/kaggle/input/**/candidates.jsonl", recursive=True))[0]
unit_file = sorted(glob.glob("/kaggle/input/**/units.jsonl", recursive=True))[0]
questions = [json.loads(x) for x in open(cand_file, encoding="utf-8").read().split("\n") if x.strip()]
units = {r["chunk_id"]: r["text"] for r in (json.loads(x) for x in open(unit_file, encoding="utf-8").read().split("\n") if x.strip())}
pairs = [(q["qid"], c["chunk_id"], q["question"], units[c["chunk_id"]]) for q in questions for c in q["candidates"]]

summary = []
for key, hf_id in MODELS.items():
    target = f"{OUT}/rerank_scores_{key}.jsonl"
    entry = {"model": key, "pairs": len(pairs)}
    try:
        if os.path.exists(target):
            entry["status"] = "skipped_already_done"
        else:
            model = CrossEncoder(hf_id, max_length=MAX_LEN, device="cuda", automodel_args={"torch_dtype": torch.float16})
            start = time.time()
            scores = model.predict([(q, t) for _, _, q, t in pairs], batch_size=32, show_progress_bar=False)
            elapsed = time.time() - start
            scores = np.asarray(scores, dtype=np.float32).reshape(-1)
            assert len(scores) == len(pairs) and np.isfinite(scores).all(), "score count or NaN problem"
            with open(target + ".tmp", "w", encoding="utf-8", newline="\n") as f:
                for (qid, cid, _, _), s in zip(pairs, scores):
                    f.write(json.dumps({"qid": qid, "chunk_id": cid, "score": float(s)}) + "\n")
            os.replace(target + ".tmp", target)  # the final name appears only when the file is complete
            entry.update(status="done", seconds=round(elapsed, 1), pairs_per_second=round(len(pairs) / elapsed, 1),
                         gpu=torch.cuda.get_device_name(0), dtype="float16", max_length=MAX_LEN, hf_id=hf_id)
            del model
            torch.cuda.empty_cache()
    except Exception:
        entry.update(status="failed", error=traceback.format_exc()[-600:])
    summary.append(entry)
    print(json.dumps(entry), flush=True)
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
