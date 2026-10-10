"""Does LLM query rewriting / expansion help the hybrid retriever, and how stable are the models? (Track B, technique 5)

Reads the outputs a Kaggle GPU run produced (`llm_outputs.jsonl`: id "qid:mode", model, repeat, batch_size, text) and
1. validity: share of outputs that survive the safeguards (kept numbers/terms, non-empty);
2. drift: repeat 0 vs repeat 1 (same prompt, greedy decoding, different batch size): exact-match share and mean text similarity;
3. agreement between models on the same prompt (mean text similarity); the same function is used later to compare a hosted API's
   cached answers with the local models';
4. retrieval: the chain a finished sweep carried forward, with the query replaced as the mode prescribes, against the original query
   on the same dev questions (paired bootstrap):
     rewrite  dense and BM25 query = rewritten question (fallback: original)
     hyde     dense query = embedding of the hypothetical passage (document-side prefix), BM25 unchanged (HyDE is a dense method);
              hyde_avg = normalised mean of the passage vector and the original query vector (our variant)
     q2d      dense query = question + newline + passage (the paper's [SEP] is a BERT token, replaced by a line break here);
              BM25 query = original question tokens x5 + passage tokens (query2doc, n = 5)

Usage:
    python -X utf8 scripts/eval_query_rewrite.py --outputs data/index/kaggle_llm/llm_outputs.jsonl --sweep data/index/sweeps/hybrid-v1-bge-m3 \
        --model bge-m3 --questions ... --parents data/index/chunks-v11-t512 --children data/index/chunks-v11-t128 \
        --index data/index/kaggle/dense-bge-m3-t128 --out data/index/sweeps/rewrite-bge-m3
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from sweep_hybrid import Sweep, read_jsonl  # noqa: E402
from ncdqa.retrieval import embed, evaluate, fusion, query_rewrite as qr  # noqa: E402
from ncdqa.retrieval.thai_tokens import tokenize  # noqa: E402


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--outputs", type=Path, required=True)
    ap.add_argument("--sweep", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--parents", type=Path, required=True)
    ap.add_argument("--children", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=ROOT / "configs/retrieval/hybrid_sweep_v1.json")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: choose a new --out")

    sw = Sweep(args)
    prior = json.loads((args.sweep / "sweep_results.json").read_text(encoding="utf-8"))
    chosen = {d["stage"]: d["best"] for d in prior["decisions"]}
    tok = next(v for v in sw.cfg["stage_a_tokenizer"]["variants"] if v["name"] == chosen["A_tokenizer"])
    bm = next(s for s in sw.cfg["stage_b_bm25_params"]["settings"] if s["name"] == chosen["B_bm25_params"])
    final = chosen["C_fusion_convex_vs_best_rrf"]
    alpha = float(final.replace("cc_alpha", "")) if final.startswith("cc_alpha") else None
    if alpha is None:
        sys.exit("this script expects the convex-combination chain; adapt for RRF")
    index, extra = sw.bm25_index(tok["mode"], tok.get("dictionary"), bm["k1"], bm["b"])
    qs = sw.questions
    mode_tok = tok["mode"]

    def lexical(text: str) -> list[tuple[str, float]]:
        return index.top(tokenize(text, mode_tok, extra), sw.pool)

    def run(dense_lists, lexical_lists) -> list[list[str]]:
        return [[u for u, _ in fusion.convex(d, l, alpha, 10)] for d, l in zip(dense_lists, lexical_lists)]

    base_lex = [lexical(q["question"]) for q in qs]
    base = sw.record("0_baseline", "original query (same chain)", {"alpha": alpha, "tokenizer": tok["name"], "bm25": bm["name"]}, run(sw.dense, base_lex))

    rows = defaultdict(dict)  # (model, mode) -> {repeat: {qid: text}}
    for r in read_jsonl(args.outputs):
        rows[(r["model"], r["mode"])].setdefault(r["repeat"], {})[r["id"].split(":")[0]] = r["text"]
    stats, cands = [], []
    qtext = {q["qid"]: q["question"] for q in qs}
    for (model_id, mode), reps in sorted(rows.items()):
        r0, r1 = reps.get(0, {}), reps.get(1, {})
        status = Counter()
        texts = []
        for q in qs:
            used, st = qr.finalize(mode, q["question"], r0.get(q["qid"]))
            status[st] += 1
            texts.append(used)
        common = [k for k in r0 if k in r1]
        cleaned0 = {k: qr.clean(r0[k], mode) for k in common}
        cleaned1 = {k: qr.clean(r1[k], mode) for k in common}
        stats.append({"model": model_id, "mode": mode, "outputs": len(r0), "status": dict(status),
                      "repeat_exact_match": round(sum(cleaned0[k] == cleaned1[k] for k in common) / max(len(common), 1), 3),
                      "repeat_mean_similarity": round(float(np.mean([sim(cleaned0[k], cleaned1[k]) for k in common])) if common else float("nan"), 3),
                      "mean_chars": round(float(np.mean([len(t) for t in texts])), 1)})
        name = f"{model_id.split('/')[-1]} | {mode}"
        if mode == "rewrite":
            dense = sw.dense_lists_for(texts)
            lex = [lexical(t) for t in texts]
            cands.append(sw.record("rewrite", name, {"model": model_id, "mode": mode}, run(dense, lex)))
            # our variant: keep the original query and add the rewrite (vector mean; BM25 tokens of both)
            qv0 = embed.encode(sw.st, [q["question"] for q in qs], sw.model.query_prefix)
            rv = embed.encode(sw.st, texts, sw.model.query_prefix)
            mixed = qv0 + rv
            mixed /= np.linalg.norm(mixed, axis=1, keepdims=True)
            dense_add = [[(p, s) for p, s, _ in hits] for hits in sw.pc.search(mixed, sw.pool, fetch=sw.pool * 4)]
            lex_add = [index.top(tokenize(q["question"], mode_tok, extra) + tokenize(t, mode_tok, extra), sw.pool) for q, t in zip(qs, texts)]
            cands.append(sw.record("rewrite", name + " (added to the original query)", {"model": model_id, "mode": mode, "variant": "add"}, run(dense_add, lex_add)))
        elif mode == "hyde":
            dense = sw.dense_lists_for(texts, sw.model.passage_prefix)
            cands.append(sw.record("hyde", name + " (passage vector only)", {"model": model_id, "mode": mode}, run(dense, base_lex)))
            qv = embed.encode(sw.st, [q["question"] for q in qs], sw.model.query_prefix)
            pv = embed.encode(sw.st, texts, sw.model.passage_prefix)
            mean = qv + pv
            mean /= np.linalg.norm(mean, axis=1, keepdims=True)
            avg = [[(p, s) for p, s, _ in hits] for hits in sw.pc.search(mean, sw.pool, fetch=sw.pool * 4)]
            cands.append(sw.record("hyde", name + " (mean of passage and query vectors)", {"model": model_id, "mode": mode, "variant": "avg"}, run(avg, base_lex)))
        elif mode == "q2d":
            dense = sw.dense_lists_for([f"{q['question']}\n{t}" for q, t in zip(qs, texts)])
            lex = [index.top(tokenize(q["question"], mode_tok, extra) * qr.Q2D_QUERY_REPEATS + tokenize(t, mode_tok, extra), sw.pool)
                   for q, t in zip(qs, texts)]
            cands.append(sw.record("q2d", name, {"model": model_id, "mode": mode}, run(dense, lex)))

    # model-to-model agreement on the same prompt
    agree = []
    by_mode = defaultdict(dict)
    for (model_id, mode), reps in rows.items():
        by_mode[mode][model_id] = {k: qr.clean(v, mode) for k, v in reps.get(0, {}).items()}
    for mode, models in by_mode.items():
        names = sorted(models)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                common = [k for k in models[a] if k in models[b]]
                agree.append({"mode": mode, "a": a, "b": b, "mean_similarity": round(float(np.mean([sim(models[a][k], models[b][k]) for k in common])), 3)})

    cands = [base] + cands
    for e in cands:
        e["paired_vs_reference"] = evaluate.paired_bootstrap({q: v["recall@5"] for q, v in base["per_question"].items()},
                                                             {q: v["recall@5"] for q, v in e["per_question"].items()})
    sw.cfg = {**sw.cfg, "id": "query_rewrite_v1"}
    sw.save(args.out)
    (args.out / "llm_stats.json").write_text(json.dumps({"validity_and_drift": stats, "model_agreement": agree,
                                                         "few_shot_overlap_with_questions": qr.examples_overlap(list(qtext.values()))},
                                                        ensure_ascii=False, indent=1), encoding="utf-8")
    print((args.out / "report.md").read_text(encoding="utf-8"))
    print(json.dumps({"validity_and_drift": stats, "model_agreement": agree}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
