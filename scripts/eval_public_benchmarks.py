"""Run our frozen retrieval stack on public Thai retrieval benchmarks (Track C, external check of the Track B result).

    python -X utf8 scripts/eval_public_benchmarks.py --out data/index/runs/public_benchmarks/run1

What is tested (the same settings as configs/retrieval/frozen_v1.json, nothing tuned on these sets):
  dense   bge-m3, no prefix, max length 512, cosine            (variant A of the project)
  bm25    Thai BM25 on character 3-grams, k1 2.18, b 0.86
  hybrid  convex fusion of min-max scores, alpha 0.6, pool 100  (variant B of the project; the project's CPU default)
Benchmarks (public, downloaded to data/external, not in git):
  NanoMTEB-Thai (hakari-bench, 9 tasks x 200 queries): belebele (3), xquad, mkqa, WebFAQ, Mr.TyDi, MIRACL, MultiLongDoc  [ids as published on its card]
  English medical (domain-shift check, same frozen settings): BEIR NFCorpus and SciFact (mteb/*), CURE v1 dermatology (mteb/CUREv1, CC-BY-NC-4.0, clinician questions);
    a word-level BM25 column (newmm_latin) is added there because character 3-grams are the Thai choice
  NitiBench-CCL (VISAI-AI, MIT): 3,729 Thai legal questions, each with one relevant statute section, searched in the 5,127 sections of nitibench-statute
Metrics: nDCG@10, Recall@10, Recall@100, MRR@10 (binary relevance), and a paired bootstrap interval for hybrid minus dense on nDCG@10.
The question is external validity: does "hybrid beats dense" (Track B, our own questions) also hold on independent Thai sets, and how does our dense retriever sit
next to published numbers? It does not say anything about the clinical correctness of the Q&A system. The tasks are written one JSON file each, so a run can be
resumed; embeddings are cached in data/external/cache.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.retrieval import embed, fusion  # noqa: E402
from ncdqa.retrieval.bm25 import BM25Index  # noqa: E402
from ncdqa.retrieval.thai_tokens import tokenize  # noqa: E402

EXT = ROOT / "data/external"
NANO = ["belebele_tha_thai_tha_thai", "xqu_ad_th", "NITI", "belebele_eng_latn_tha_thai", "belebele_tha_thai_eng_latn", "mkqa_th", "web_faq_tha", "mr_tidy_thai", "miracl_th",
        "multi_long_doc_th"]
K1, B, ALPHA, POOL = 2.18, 0.86, 0.6, 100


def load_nano(task: str):
    import pandas as pd
    base = EXT / "NanoMTEB-Thai"
    one = lambda kind: pd.concat([pd.read_parquet(p) for p in sorted((base / kind).glob(f"{task}-*.parquet"))])  # noqa: E731
    corpus, queries, qrels = one("corpus"), one("queries"), one("qrels")
    rel: dict[str, set] = {}
    for q, c in zip(qrels["query-id"], qrels["corpus-id"]):
        rel.setdefault(str(q), set()).add(str(c))
    return [str(x) for x in corpus["_id"]], list(corpus["text"]), [str(x) for x in queries["_id"]], list(queries["text"]), rel


def load_niti():
    import pandas as pd
    s = pd.read_parquet(EXT / "nitibench-statute/data/ccl-00000-of-00001.parquet")
    key = lambda law, sec: f"{law}|{sec}"  # noqa: E731
    ids = [key(a, b) for a, b in zip(s["law_name"], s["section_num"])]
    keep = {i: (i, t) for i, t in zip(ids, s["section_content"])}      # a duplicated key keeps the last text
    ids, texts = list(keep), [keep[i][1] for i in keep]
    q = pd.read_parquet(EXT / "nitibench/data/nitibench-ccl.parquet")
    qids, qtexts, rel = [], [], {}
    for n, (question, laws) in enumerate(zip(q["question"], q["relevant_laws"])):
        r = {key(d["law_name"], d["section_num"]) for d in laws}
        if r & set(ids):
            qids.append(str(n)); qtexts.append(question); rel[str(n)] = r & set(ids)
    return ids, texts, qids, qtexts, rel


def load_beir(name: str):
    """BEIR-format set from mteb/<name>: corpus.jsonl, queries.jsonl, qrels/test.tsv (a score above 0 counts as relevant)."""
    import pandas as pd
    base = EXT / name
    corpus = [json.loads(x) for x in (base / "corpus.jsonl").read_text(encoding="utf-8").split(chr(10)) if x.strip()]
    queries = {str(q["_id"]): q["text"] for q in (json.loads(x) for x in (base / "queries.jsonl").read_text(encoding="utf-8").split(chr(10)) if x.strip())}
    qrels = pd.read_csv(base / "qrels/test.tsv", sep=chr(9))
    rel: dict[str, set] = {}
    for q, c, sc in zip(qrels["query-id"], qrels["corpus-id"], qrels["score"]):
        if sc > 0:
            rel.setdefault(str(q), set()).add(str(c))
    qids = [q for q in queries if q in rel]
    return [str(c["_id"]) for c in corpus], [((c.get("title") or "") + " " + c["text"]).strip() for c in corpus], qids, [queries[q] for q in qids], rel


def load_cure(sub: str):
    """CURE v1 (mteb/CUREv1, CC-BY-NC-4.0), English, one specialty."""
    import pandas as pd
    base = EXT / "CUREv1"
    one = lambda kind: pd.read_parquet(base / f"en-{kind}/{sub}-00000-of-00001.parquet")  # noqa: E731
    corpus, queries, qrels = one("corpus"), one("queries"), one("qrels")
    rel: dict[str, set] = {}
    for q, c, sc in zip(qrels["query-id"], qrels["corpus-id"], qrels["score"]):
        if sc > 0:
            rel.setdefault(str(q), set()).add(str(c))
    qmap = {str(i): t for i, t in zip(queries["_id"], queries["text"])}
    qids = [q for q in qmap if q in rel]
    return [str(i) for i in corpus["_id"]], [((t or "") + " " + x).strip() for t, x in zip(corpus["title"], corpus["text"])], qids, [qmap[q] for q in qids], rel


def metrics(ranked: list[str], rel: set) -> dict:
    top10 = ranked[:10]
    dcg = sum(1 / math.log2(i + 2) for i, d in enumerate(top10) if d in rel)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(len(rel), 10)))
    rr = next((1 / (i + 1) for i, d in enumerate(top10) if d in rel), 0.0)
    return {"ndcg10": dcg / idcg if idcg else 0.0, "recall10": len(set(top10) & rel) / len(rel), "recall100": len(set(ranked[:100]) & rel) / len(rel), "mrr10": rr}


def boot(d: list[float], n: int = 2000, seed: int = 20261011):
    rng = random.Random(seed)
    m = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return [round(m[int(.025 * n)], 4), round(m[int(.975 * n)], 4)]


def download(ext: Path, tasks: list[str]) -> None:
    """Fetch the public sets from the Hugging Face hub into `ext` (used on Kaggle, where nothing is on disk yet)."""
    from huggingface_hub import snapshot_download
    want = lambda *names: any(t in names for t in tasks)  # noqa: E731
    if any(t not in ("NITI", "nfcorpus", "scifact") and not t.startswith("cure_") for t in tasks):
        snapshot_download("hakari-bench/NanoMTEB-Thai", repo_type="dataset", local_dir=ext / "NanoMTEB-Thai", allow_patterns=["corpus/*", "queries/*", "qrels/*"])
    if want("NITI"):
        snapshot_download("VISAI-AI/nitibench", repo_type="dataset", local_dir=ext / "nitibench")
        snapshot_download("VISAI-AI/nitibench-statute", repo_type="dataset", local_dir=ext / "nitibench-statute")
    for name in ("nfcorpus", "scifact"):
        if want(name):
            snapshot_download(f"mteb/{name}", repo_type="dataset", local_dir=ext / name, allow_patterns=["corpus.jsonl", "queries.jsonl", "qrels/test.tsv"])
    cure = [t.removeprefix("cure_") for t in tasks if t.startswith("cure_")]
    if cure:
        snapshot_download("mteb/CUREv1", repo_type="dataset", local_dir=ext / "CUREv1", allow_patterns=[f"en-{k}/{c}*" for c in cure for k in ("corpus", "queries", "qrels")])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tasks", nargs="*", default=NANO)
    ap.add_argument("--max-docs", type=int, default=0, help="debug: keep only the first N documents that are relevant plus filler (0 = all)")
    ap.add_argument("--ext", type=Path, default=None, help="folder of the public datasets (default data/external)")
    ap.add_argument("--download", action="store_true", help="download the datasets of --tasks into --ext first")
    ap.add_argument("--device", default="cpu", help="cpu or cuda")
    ap.add_argument("--fp16", action="store_true", help="half-precision embeddings on the GPU (faster; vectors differ slightly from float32, recorded in the result)")
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()
    global EXT
    if args.ext:
        EXT = args.ext
    if args.download:
        download(EXT, args.tasks)
    args.out.mkdir(parents=True, exist_ok=True)
    (EXT / "cache").mkdir(parents=True, exist_ok=True)
    model = embed.MODELS["bge-m3"]
    st = embed.load(model, args.device)
    if args.fp16:
        st.half()
    for task in args.tasks:
        dest = args.out / f"{task}.json"
        if dest.exists():
            print("skip (done)", task, flush=True)
            continue
        t0 = time.perf_counter()
        ids, texts, qids, qtexts, rel = (load_niti() if task == "NITI" else load_beir(task) if task in ("nfcorpus", "scifact")
                                         else load_cure(task.removeprefix("cure_")) if task.startswith("cure_") else load_nano(task))
        print(f"== {task}: {len(ids)} docs, {len(qids)} queries", flush=True)
        cache = EXT / "cache" / f"{task}_bge-m3_corpus.npy"
        if cache.exists():
            dvec = np.load(cache)
        else:
            order = sorted(range(len(texts)), key=lambda i: len(texts[i]))          # similar lengths per batch: much faster on CPU
            enc = embed.encode(st, [texts[i] for i in order], model.passage_prefix, batch_size=args.batch)
            dvec = np.zeros_like(enc)
            dvec[order] = enc
            np.save(cache, dvec)
        t_doc = time.perf_counter() - t0
        qvec = embed.encode(st, qtexts, model.query_prefix, batch_size=args.batch)
        bm = BM25Index(ids, [tokenize(t, "char3", ()) for t in texts], K1, B)
        bmw = BM25Index(ids, [tokenize(t, "newmm_latin", ()) for t in texts], K1, B)      # word-level BM25, extra column (the frozen one is character 3-grams)
        per = {"dense": [], "bm25": [], "hybrid": [], "bm25_word": [], "hybrid_word": []}
        sims = qvec @ dvec.T
        for qi, q in enumerate(qids):
            s = sims[qi]
            idx = np.argpartition(-s, min(POOL, len(s) - 1))[:POOL]
            idx = idx[np.argsort(-s[idx])]
            dense = [(ids[i], float(s[i])) for i in idx]
            lex = bm.top(tokenize(qtexts[qi], "char3", ()), POOL)
            hyb = fusion.convex(dense, lex, ALPHA, POOL) if lex else dense
            lexw = bmw.top(tokenize(qtexts[qi], "newmm_latin", ()), POOL)
            hybw = fusion.convex(dense, lexw, ALPHA, POOL) if lexw else dense
            for name, ranking in (("dense", dense), ("bm25", lex), ("hybrid", hyb), ("bm25_word", lexw), ("hybrid_word", hybw)):
                per[name].append(metrics([d for d, _ in ranking], rel[q]))
        res = {"task": task, "n_docs": len(ids), "n_queries": len(qids), "embed_seconds": round(t_doc, 1), "settings": {"model": "bge-m3", "device": args.device, "fp16": args.fp16, "bm25": "char3", "k1": K1, "b": B, "alpha": ALPHA, "pool": POOL}}
        for name, rows in per.items():
            res[name] = {m: round(sum(r[m] for r in rows) / len(rows), 4) for m in ("ndcg10", "recall10", "recall100", "mrr10")}
        d = [h["ndcg10"] - a["ndcg10"] for h, a in zip(per["hybrid"], per["dense"])]
        res["hybrid_minus_dense_ndcg10"] = {"mean": round(sum(d) / len(d), 4), "ci95": boot(d)}
        dw = [h["ndcg10"] - a["ndcg10"] for h, a in zip(per["hybrid_word"], per["dense"])]
        res["hybrid_word_minus_dense_ndcg10"] = {"mean": round(sum(dw) / len(dw), 4), "ci95": boot(dw)}
        dest.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: res[k] for k in ("dense", "bm25", "hybrid", "bm25_word", "hybrid_word", "hybrid_minus_dense_ndcg10", "hybrid_word_minus_dense_ndcg10")}, ensure_ascii=False), f"({time.perf_counter() - t0:.0f}s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
