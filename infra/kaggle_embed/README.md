# Embed on Kaggle GPU (optional; CPU works but bge-m3 takes hours)

Why: e5-base takes about 40 min per chunk set on the reference CPU and bge-m3 roughly three times that. A T4 does all four
combinations in minutes. **What leaves the machine:** the text of every chunk (including the Siriraj leaflets under the
Decision 0008 rights conflict) goes into a *private* Kaggle dataset. Do this only after the owner of Track B says yes, and
delete the dataset when the vectors are back.

Kaggle account and token setup: follow `D:\KMITL\LabBS2026\docs\KAGGLE_SETUP.md` (thai-prune repo): own account, phone
verification for GPU, `kaggle.json` in `~/.kaggle/`.

1. Dataset: copy `data/index/chunks-v11-t256` and `chunks-v11-t512` (only the `chunks.jsonl` files) into a new folder, add
   `dataset-metadata.json` (`{"title": "ncd-chunks-v11", "id": "<user>/ncd-chunks-v11", "licenses": [{"name": "other"}]}`) and run
   `kaggle datasets create -p <folder>` (private by default).
2. Kernel: copy `embed_kernel.py` and `kernel-metadata.json` (fill in `<user>`) into a folder, then `kaggle kernels push -p <folder>`.
3. Wait: `kaggle kernels status <user>/ncd-embed`; fetch: `kaggle kernels output <user>/ncd-embed -p data/index/kaggle/`.
4. Move the four `dense-*` folders into `data/index/`; the manifests say `device: cuda`, `dtype: float16`. Float16 vectors differ
   slightly from the CPU float32 ones, so compare Recall on a few queries before mixing CPU and GPU indexes in one table.
5. Delete the private dataset on Kaggle and note the run in `docs/retrieval_process_record.md`.
