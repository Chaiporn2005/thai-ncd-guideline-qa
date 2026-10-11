"""Kaggle GPU kernel: our frozen retrieval stack (bge-m3 dense, Thai char-3gram BM25, convex hybrid) on public Thai and English medical retrieval sets (Track C).

Input : the private dataset <user>/ncd-retrieval-code (our retrieval modules and scripts/eval_public_benchmarks.py; no project documents, no private data).
        The public benchmark sets are downloaded from the Hugging Face hub inside the kernel (internet on).
Output: /kaggle/working/results/<task>.json (metrics only) and run_info.json. Embeddings and downloads go to /kaggle/temp and are not saved.
Every finished task is written at once and a finished task is skipped, so a re-run resumes.
"""
import glob
import json
import os
import platform
import subprocess
import sys
import time

import torch

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pythainlp", "bm25s", "pandas", "pyarrow", "huggingface_hub"], check=True)
code = glob.glob("/kaggle/input/**/eval_public_benchmarks.py", recursive=True)[0]
root = os.path.dirname(os.path.dirname(code))
os.makedirs("/kaggle/working/results", exist_ok=True)
TASKS = ["belebele_tha_thai_tha_thai", "xqu_ad_th", "NITI", "belebele_eng_latn_tha_thai", "belebele_tha_thai_eng_latn", "mkqa_th", "web_faq_tha", "mr_tidy_thai", "miracl_th",
         "multi_long_doc_th", "scifact", "nfcorpus", "cure_dermatology", "cure_pulmonology"]
t0 = time.time()
subprocess.run([sys.executable, code, "--ext", "/kaggle/temp/ext", "--download", "--device", "cuda", "--fp16", "--batch", "32", "--out", "/kaggle/working/results", "--tasks", *TASKS],
               check=False, cwd=root, env={**os.environ, "PYTHONPATH": os.path.join(root, "src")})
json.dump({"gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "torch": torch.__version__, "python": platform.python_version(), "seconds": round(time.time() - t0),
           "finished": sorted(os.path.basename(p) for p in glob.glob("/kaggle/working/results/*.json"))}, open("/kaggle/working/run_info.json", "w"), indent=1)
