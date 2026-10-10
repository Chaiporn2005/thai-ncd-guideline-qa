# Embed on Kaggle GPU (prepared, not run)

Why: e5-base takes about an hour per chunk set on the reference CPU and bge-m3 roughly three times that; a T4 does all eight
combinations (2 models x chunk sizes 128/256/384/512) in minutes. The owner of Track B accepted sending the chunk text out of
the machine (2026-10-10, includes the Siriraj leaflets under the Decision 0008 rights conflict) but asked **not to run it yet**.

Kaggle account and token setup: `D:\KMITL\LabBS2026\docs\KAGGLE_SETUP.md` (the thai-prune repo): own account, phone verification
for GPU, `kaggle.json` in `~/.kaggle/`.

## Run (when approved)

1. Backup first: keep `data/index/chunks-v11-t*/` untouched and copy them to a second place (for example a zip on Drive).
   The vectors are only valid for the exact chunk files they were made from (the manifest stores the chunk file hash).
2. Dataset: put the four `chunks.jsonl` files in `chunks-v11-t128/`, `-t256/`, `-t384/`, `-t512/` under one folder with
   `dataset-metadata.json` (`{"title": "ncd-chunks-v11", "id": "<user>/ncd-chunks-v11", "licenses": [{"name": "other"}]}`), then
   `kaggle datasets create -p <folder>` (private by default).
3. Kernel: copy `embed_kernel.py` and `kernel-metadata.json` (fill in `<kaggle-username>`) into a folder and `kaggle kernels push -p <folder>`.
4. Watch: `kaggle kernels status <user>/ncd-embed`. A failed combination is listed in `summary.json`; the rest still finish.
5. Download at once: `kaggle kernels output <user>/ncd-embed -p data/index/kaggle/`. Kaggle may expire outputs, so do not wait.
6. Verify before use: `python -X utf8 scripts/verify_embedding_output.py --downloaded data/index/kaggle --chunks-root data/index`
   (checksums, chunk id order, chunk file hash, finite unit vectors, and CPU re-embedding of a sample agrees with the GPU vectors).
7. Only after a clean verification: move the `dense-*` folders into `data/index/`, delete the private dataset and kernel output
   on Kaggle, and record the run (GPU, dtype float16, time) in `docs/retrieval_process_record.md`.

## Rules that avoid losing or mixing data

- Never rebuild `chunks-v11-t*` after uploading: ids and offsets would no longer match the vectors (the verifier catches it).
- Float16 GPU vectors differ slightly from CPU float32 ones. Use one source per table of results, or note which one was used.
- Do not delete the CPU indexes until the verified GPU indexes reproduce the same Recall@k on dev within noise.
