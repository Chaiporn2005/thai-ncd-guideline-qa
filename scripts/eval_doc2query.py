"""Does doc2query (LLM-written questions per chunk) help the hybrid retriever? (Track B, technique 6)

The questions (`scripts/validate_doc2query.py --merge-out`) are added to the index in two ways, tested apart and together:
* dense   each question is embedded with the query-side prefix (it is query-like text) and added to the child vectors with a link to
          its parent chunk, so a match on a question returns that parent (best child/question score per parent, as in parent-child);
* BM25    the questions are appended to the parent text before tokenising (the original doc2query/docTTTTTquery recipe).
BM25 parameters: the chain's value and, because Pyserini reports that expanded documents prefer larger k1 and b, the 'tuned2'
setting (k1 2.18, b 0.86; Pyserini, arXiv 2102.10073) that is already in the sweep config.

Bias to keep in mind: the gold questions and the doc2query questions were both written by an LLM from the same pages, so a match
can be easier than for real users. A column reports how often a dev question's best-matching generated question belongs to its own
evidence parent versus another parent, to show how close the wording is.

Usage:
    python -X utf8 scripts/eval_doc2query.py --d2q data/index/doc2query/questions.jsonl --sweep data/index/sweeps/hybrid-v1-bge-m3 \
        --model bge-m3 --questions ... --parents data/index/chunks-v11-t512 --children data/index/chunks-v11-t128 \
        --index data/index/kaggle/dense-bge-m3-t128 --out data/index/sweeps/doc2query-bge-m3
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from sweep_hybrid import Sweep, read_jsonl  # noqa: E402
from ncdqa.retrieval import embed, evaluate, fusion  # noqa: E402
from ncdqa.retrieval.bm25 import BM25Index, tokenize_units  # noqa: E402
from ncdqa.retrieval.dense import DenseIndex  # noqa: E402
from ncdqa.retrieval.parent_child import ParentChildIndex, build_parent_map  # noqa: E402
from ncdqa.retrieval.thai_tokens import load_dictionary, tokenize  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--d2q", type=Path, required=True)
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
    chain_bm = next(s for s in sw.cfg["stage_b_bm25_params"]["settings"] if s["name"] == chosen["B_bm25_params"])
    tuned2 = next(s for s in sw.cfg["stage_b_bm25_params"]["settings"] if s["name"] == "anserini_tuned_for_expansion")
    alpha = float(chosen["C_fusion_convex_vs_best_rrf"].replace("cc_alpha", ""))
    extra = tuple(load_dictionary(ROOT / tok["dictionary"])) if tok.get("dictionary") else ()

    gen: dict[str, list[str]] = defaultdict(list)
    for r in read_jsonl(args.d2q):
        gen[r["chunk_id"]].append(r["question"])
    parents = {c["chunk_id"]: c for c in sw.parents}
    missing = [p for p in parents if p not in gen]

    # dense: child vectors + question vectors (query prefix), questions linked to their parent
    child_index = DenseIndex.load(args.index)
    q_ids, q_texts = [], []
    for pid, qs in gen.items():
        if pid in parents:
            for i, q in enumerate(qs):
                q_ids.append(f"{pid}::q{i}")
                q_texts.append(q)
    qvec = embed.encode(sw.st, q_texts, sw.model.query_prefix, batch_size=32)
    parent_map = build_parent_map(read_jsonl(args.children / "chunks.jsonl"), list(parents.values()))
    parent_map.update({i: i.split("::")[0] for i in q_ids})
    expanded = ParentChildIndex(DenseIndex(np.vstack([child_index.vectors, qvec]), child_index.chunk_ids + q_ids), parent_map)
    qv = embed.encode(sw.st, [q["question"] for q in sw.questions], sw.model.query_prefix)
    dense_exp = [[(p, s) for p, s, _ in hits] for hits in expanded.search(qv, sw.pool, fetch=sw.pool * 6)]

    # how close is the wording of a gold dev question to the generated questions?
    sims = qv @ qvec.T
    own = other = 0
    for i, q in enumerate(sw.questions):
        best = int(sims[i].argmax())
        gold = {e["document_id"] for e in q["evidence"]}
        parent = q_ids[best].split("::")[0]
        own += parents[parent]["document_id"] in gold
        other += parents[parent]["document_id"] not in gold
    closeness = {"best_generated_question_is_from_a_gold_document": own, "from_another_document": other,
                 "mean_best_cosine": round(float(sims.max(axis=1).mean()), 3)}

    def bm25_lists(params: dict, with_questions: bool):
        units = [{**c, "text": c["text"] + ("\n" + "\n".join(gen.get(c["chunk_id"], [])) if with_questions else "")} for c in sw.parents]
        toks = tokenize_units(units, tok["mode"], extra, with_header=True)
        index = BM25Index([c["chunk_id"] for c in sw.parents], toks, params["k1"], params["b"])
        return [index.top(tokenize(q["question"], tok["mode"], extra), sw.pool) for q in sw.questions]

    def run(dense, lex):
        return [[u for u, _ in fusion.convex(d, l, alpha, 10)] for d, l in zip(dense, lex)]

    lex_plain = bm25_lists(chain_bm, False)
    base = sw.record("0_baseline", "hybrid chain, no doc2query", {"alpha": alpha}, run(sw.dense, lex_plain))
    cands = [base]
    cands.append(sw.record("dense_only_side", "dense + questions, BM25 unchanged", {}, run(dense_exp, lex_plain)))
    for label, params in (("chain params", chain_bm), ("tuned2 (k1 2.18, b 0.86)", tuned2)):
        lex_q = bm25_lists(params, True)
        cands.append(sw.record("bm25_side", f"BM25 + questions, {label}, dense unchanged", {"k1": params["k1"], "b": params["b"]}, run(sw.dense, lex_q)))
        cands.append(sw.record("both", f"dense + questions and BM25 + questions, {label}", {"k1": params["k1"], "b": params["b"]}, run(dense_exp, lex_q)))
    cands.append(sw.record("dense_only", "no BM25: dense + questions only", {}, [[p for p, _ in lst[:10]] for lst in dense_exp]))
    for e in cands:
        e["paired_vs_reference"] = evaluate.paired_bootstrap({q: v["recall@5"] for q, v in base["per_question"].items()},
                                                             {q: v["recall@5"] for q, v in e["per_question"].items()})
    sw.cfg = {**sw.cfg, "id": "doc2query_v1"}
    sw.save(args.out)
    (args.out / "d2q_extra.json").write_text(json.dumps({"parents_without_questions": len(missing), "parents": len(parents), "questions": len(q_ids),
                                                         "wording_closeness": closeness}, indent=1), encoding="utf-8")
    print((args.out / "report.md").read_text(encoding="utf-8"))
    print(json.dumps({"parents_without_questions": len(missing), "questions": len(q_ids), "wording_closeness": closeness}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
