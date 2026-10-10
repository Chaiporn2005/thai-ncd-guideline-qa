"""Kaggle GPU kernel: run small open LLMs over prepared prompts with greedy decoding (Track B query rewriting). Self-contained.

Input : a private dataset with requests.jsonl rows {id, mode, messages} written by scripts/export_llm_requests.py (the prompts come
        from src/ncdqa/retrieval/query_rewrite.py, so there is one source of prompt text).
Output: /kaggle/working/llm_outputs.jsonl rows {id, mode, model, repeat, batch_size, text, new_tokens} and summary.json.
Decoding: greedy (do_sample=False, no temperature), the model's own chat template, thinking switched off where the template has a
switch, repetition_penalty 1.0. Every request is generated twice with different batch sizes (16 then 4): in float16 on a GPU the
batch composition can change the last digits and therefore, rarely, the text; the difference between the two repeats is the
drift measured for the report.
A model that fails is recorded and the others still run; rows are appended as they finish.
"""
import glob
import json
import os
import time
import traceback

import subprocess
import sys

import transformers

if tuple(int(x) for x in transformers.__version__.split(".")[:2]) < (4, 51):  # Qwen3 and Gemma3 need a recent transformers
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.51"])
    import importlib
    importlib.reload(transformers)


import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODELS = ["typhoon-ai/typhoon2.5-qwen3-4b", "Qwen/Qwen3-4B-Instruct-2507", "typhoon-ai/typhoon2.1-gemma3-4b"]
MAX_NEW = {"rewrite": 120, "hyde": 200, "q2d": 180}
BATCHES = [16, 4]
OUT = "/kaggle/working"

req_file = sorted(glob.glob("/kaggle/input/**/requests.jsonl", recursive=True))[0]
requests = [json.loads(x) for x in open(req_file, encoding="utf-8").read().split("\n") if x.strip()]
out_path = f"{OUT}/llm_outputs.jsonl"
done = set()
if os.path.exists(out_path):
    for line in open(out_path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            done.add((r["model"], r["repeat"], r["id"]))

summary = []
for model_id in MODELS:
    entry = {"model": model_id}
    try:
        tok = AutoTokenizer.from_pretrained(model_id)
        tok.padding_side = "left"
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="cuda")
        model.eval()
        start, produced = time.time(), 0
        for repeat, bs in enumerate(BATCHES):
            todo = [r for r in requests if (model_id, repeat, r["id"]) not in done]
            for mode in MAX_NEW:
                rows = sorted([r for r in todo if r["mode"] == mode], key=lambda r: len(json.dumps(r["messages"], ensure_ascii=False)))
                for i in range(0, len(rows), bs):
                    batch = rows[i:i + bs]
                    prompts = [tok.apply_chat_template(r["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
                               for r in batch]
                    enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
                    with torch.no_grad():
                        gen = model.generate(**enc, max_new_tokens=MAX_NEW[mode], do_sample=False, temperature=None, top_p=None,
                                             top_k=None, repetition_penalty=1.0, pad_token_id=tok.pad_token_id)
                    texts = tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
                    with open(out_path, "a", encoding="utf-8", newline="\n") as f:
                        for r, text, ids in zip(batch, texts, gen[:, enc["input_ids"].shape[1]:]):
                            n_new = int((ids != tok.pad_token_id).sum())
                            f.write(json.dumps({"id": r["id"], "mode": mode, "model": model_id, "repeat": repeat, "batch_size": bs,
                                                "text": text, "new_tokens": n_new}, ensure_ascii=False) + "\n")
                            produced += 1
        entry.update(status="done", seconds=round(time.time() - start, 1), generations=produced, gpu=torch.cuda.get_device_name(0),
                     dtype="float16", torch=torch.__version__)
        del model
        torch.cuda.empty_cache()
    except Exception:
        entry.update(status="failed", error=traceback.format_exc()[-800:])
    summary.append(entry)
    print(json.dumps(entry), flush=True)
json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
