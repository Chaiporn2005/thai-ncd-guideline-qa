# Public retrieval benchmarks on a Kaggle GPU (Track C)

Runs `scripts/eval_public_benchmarks.py` (frozen bge-m3 dense + Thai BM25 + convex hybrid) on 10 Thai and 4 English medical retrieval sets. Public data only.
On a T4 all 14 tasks took 28 minutes (about 3 hours or more on CPU). Results: `runs/frozen_gen_v1/public_benchmarks/`.

1. Make a private dataset `<user>/ncd-retrieval-code` holding `scripts/eval_public_benchmarks.py` and `src/ncdqa/{__init__,retrieval/{__init__,embed,bm25,fusion,thai_tokens}}.py`
   (`kaggle datasets create -p <folder> --dir-mode zip`; without `--dir-mode zip` Kaggle skips sub-folders).
2. Put your username in `kernel/kernel-metadata.json` (two places) and `kaggle kernels push -p kernel`. GPU and internet must be on (phone-verified account).
3. `kaggle kernels output <user>/ncd-public-benchmarks -p <folder>` as soon as it finishes (outputs can expire), then
   `python -X utf8 scripts/summarize_public_benchmarks.py --run <folder>/results --out table.md`.
