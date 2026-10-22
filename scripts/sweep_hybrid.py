"""Hybrid (dense + Thai BM25) sweep with a recorded reason for every choice (Track B).

Three stages, each declared in the config file with the source of every value: (A) tokenizer / dictionary, (B) BM25 k1 and b,
(C) fusion (RRF k, convex-combination alpha). The best setting of a stage is carried into the next one by the config's
selection rule, which is fixed before any number is seen. Dense side: parent-child (child chunks matched, parent chunks
returned) or plain dense. Everything runs on cached query vectors, so a stage takes seconds.

Usage:
    python -X utf8 scripts/sweep_hybrid.py --config configs/retrieval/hybrid_sweep_v1.json --model bge-m3 \
        --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl --parents data/index/chunks-v11-t512 \
        --children data/index/chunks-v11-t128 --index data/index/kaggle/dense-bge-m3-t128 --out data/index/sweeps/hybrid-v1-bge-m3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import embed, evaluate, fusion  # noqa: E402
from ncdqa.retrieval.bm25 import BM25Index, tokenize_units  # noqa: E402
from ncdqa.retrieval.dense import DenseIndex  # noqa: E402
from ncdqa.retrieval.parent_child import ParentChildIndex, build_parent_map  # noqa: E402
from ncdqa.retrieval.thai_tokens import load_dictionary, tokenize  # noqa: E402

KS = [1, 3, 5, 10]
KEYS = [f"{m}@{k}" for k in KS for m in ("recall", "hit", "mrr")]


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


class Sweep:
    def __init__(self, args):
        self.cfg = json.loads(args.config.read_text(encoding="utf-8"))
        self.pool = self.cfg["pool"]
        qs = [q for q in read_jsonl(args.questions) if q["status"] != "rejected" and q["split"] == "dev" and q["answerable"]
              and "??" not in q["question"]]  # a question whose Thai was lost when the file was written is not a question
        self.questions = qs
        self.parents = read_jsonl(args.parents / "chunks.jsonl")
        self.units = {c["chunk_id"]: c for c in self.parents}
        children = read_jsonl(args.children / "chunks.jsonl")
        model = embed.MODELS[args.model]
        st = embed.load(model)
        self.model, self.st = model, st
        qvec = embed.encode(st, [q["question"] for q in qs], model.query_prefix, batch_size=16)
        pc = ParentChildIndex(DenseIndex.load(args.index), build_parent_map(children, self.parents))
        self.pc = pc
        found = pc.search(qvec, self.pool, fetch=self.pool * 4)
        self.dense = [[(p, s) for p, s, _ in hits] for hits in found]
        self.results: list[dict] = []
        self.decisions: list[dict] = []

    def score(self, ranked_lists: list[list[str]]) -> dict:
        per_q = {}
        for q, ranked in zip(self.questions, ranked_lists):
            per_q[q["qid"]] = evaluate.score_question([self.units[c] for c in ranked], q["evidence"], KS)
        by_type: dict = {}
        for q in self.questions:
            by_type.setdefault(q["type"], {})[q["qid"]] = per_q[q["qid"]]
        return {"overall": evaluate.aggregate(per_q, KEYS), "per_question": per_q,
                "by_type": {t: {"n": len(v), **evaluate.aggregate(v, ["recall@5", "mrr@10"])} for t, v in sorted(by_type.items())}}

    def record(self, stage: str, name: str, params: dict, ranked_lists: list[list[str]], note: str = "") -> dict:
        entry = {"stage": stage, "name": name, "params": params, "note": note, **self.score(ranked_lists)}
        self.results.append(entry)
        return entry

    def bm25_index(self, mode: str, dictionary: str | None, k1: float, b: float) -> tuple[BM25Index, tuple[str, ...]]:
        extra = tuple(load_dictionary(ROOT / dictionary)) if dictionary else ()
        toks = tokenize_units(self.parents, mode, extra, with_header=True)
        return BM25Index([c["chunk_id"] for c in self.parents], toks, k1, b), extra

    def bm25_lists(self, mode: str, dictionary: str | None, k1: float, b: float):
        index, extra = self.bm25_index(mode, dictionary, k1, b)
        return [index.top(tokenize(q["question"], mode, extra), self.pool) for q in self.questions]

    def dense_lists_for(self, texts: list[str], prefix: str | None = None) -> list[list[tuple[str, float]]]:
        """Parent-child dense lists for arbitrary query texts (used for rewritten queries)."""
        vec = embed.encode(self.st, texts, self.model.query_prefix if prefix is None else prefix, batch_size=16)
        return [[(p, s) for p, s, _ in hits] for hits in self.pc.search(vec, self.pool, fetch=self.pool * 4)]

    def provisional_hybrid(self, prior: dict) -> tuple[list[list[tuple[str, float]]], dict]:
        """Fused ranked lists (pool deep, with scores) of the chain the declared rule carried forward in a finished sweep."""
        chosen = {d["stage"]: d["best"] for d in prior["decisions"]}
        tok = next(v for v in self.cfg["stage_a_tokenizer"]["variants"] if v["name"] == chosen["A_tokenizer"])
        bm = next(s for s in self.cfg["stage_b_bm25_params"]["settings"] if s["name"] == chosen["B_bm25_params"])
        final = chosen["C_fusion_convex_vs_best_rrf"]
        lexical = self.bm25_lists(tok["mode"], tok.get("dictionary"), bm["k1"], bm["b"])
        if final.startswith("cc_alpha"):
            alpha = float(final.replace("cc_alpha", ""))
            fused = [fusion.convex(dl, bl, alpha, self.pool) for dl, bl in zip(self.dense, lexical)]
            fusion_desc = {"type": "convex", "alpha": alpha}
        else:
            k = int(final.replace("rrf_k", ""))
            fused = [fusion.rrf([[p for p, _ in dl], [u for u, _ in bl]], k, self.pool) for dl, bl in zip(self.dense, lexical)]
            fusion_desc = {"type": "rrf", "k": k}
        return fused, {"tokenizer": tok["name"], "bm25": bm["name"], **fusion_desc}

    def pick(self, stage: str, candidates: list[dict], reference_name: str, metric: str = "recall@5") -> dict:
        best = max(candidates, key=lambda e: (e["overall"][metric], e["overall"]["mrr@10"]))
        ref = next(e for e in candidates if e["name"] == reference_name)
        base = {q: v[metric] for q, v in ref["per_question"].items()}
        paired = evaluate.paired_bootstrap(base, {q: v[metric] for q, v in best["per_question"].items()})
        distinguishable = paired["ci95"][0] > 0
        decision = {"stage": stage, "rule_metric": metric, "reference": reference_name, "best": best["name"],
                    "best_overall": best["overall"][metric], "reference_overall": ref["overall"][metric], "paired_vs_reference": paired,
                    "label": "reference kept" if best["name"] == reference_name else
                    ("improvement distinguishable from the reference" if distinguishable else "not distinguishable: provisional only")}
        self.decisions.append(decision)
        for e in candidates:
            e["paired_vs_reference"] = evaluate.paired_bootstrap(base, {q: v[metric] for q, v in e["per_question"].items()})
        return best

    def run(self) -> None:
        cfg = self.cfg
        dense_only = self.record("0_reference", "dense_parent_child_only", {}, [[p for p, _ in lst[:10]] for lst in self.dense])
        a = cfg["stage_a_tokenizer"]
        params = a["bm25_params"]
        cands = []
        for v in a["variants"]:
            t0 = time.time()
            lists = self.bm25_lists(v["mode"], v.get("dictionary"), params["k1"], params["b"])
            self.record("A_tokenizer_bm25_only", v["name"], {"bm25": params, "tokenizer": v}, [[u for u, _ in lst[:10]] for lst in lists])
            fused = [[d for d, _ in fusion.rrf([[p for p, _ in dl], [u for u, _ in bl]], a["fusion"]["k"], 10)]
                     for dl, bl in zip(self.dense, lists)]
            cands.append(self.record("A_tokenizer_hybrid_rrf", v["name"], {"bm25": params, "tokenizer": v, "rrf_k": a["fusion"]["k"]}, fused,
                                     note=f"{round(time.time() - t0)} s"))
        best_a = self.pick("A_tokenizer", cands, a["reference"])
        tok = best_a["params"]["tokenizer"]

        b = cfg["stage_b_bm25_params"]
        cands = []
        for s in b["settings"]:
            lists = self.bm25_lists(tok["mode"], tok.get("dictionary"), s["k1"], s["b"])
            self.record("B_bm25_params_bm25_only", s["name"], {"k1": s["k1"], "b": s["b"], "source": s["source"]}, [[u for u, _ in lst[:10]] for lst in lists])
            fused = [[d for d, _ in fusion.rrf([[p for p, _ in dl], [u for u, _ in bl]], a["fusion"]["k"], 10)] for dl, bl in zip(self.dense, lists)]
            cands.append(self.record("B_bm25_params_hybrid_rrf", s["name"], {"k1": s["k1"], "b": s["b"], "source": s["source"], "tokenizer": tok["name"]}, fused))
        best_b = self.pick("B_bm25_params", cands, b["reference"])
        k1, bb = best_b["params"]["k1"], best_b["params"]["b"]

        lists = self.bm25_lists(tok["mode"], tok.get("dictionary"), k1, bb)
        c = cfg["stage_c_fusion"]
        cands = []
        for k in c["rrf_k"]["values"]:
            fused = [[d for d, _ in fusion.rrf([[p for p, _ in dl], [u for u, _ in bl]], k, 10)] for dl, bl in zip(self.dense, lists)]
            cands.append(self.record("C_fusion_rrf", f"rrf_k{k}", {"rrf_k": k, "k1": k1, "b": bb, "tokenizer": tok["name"]}, fused))
        best_rrf = self.pick("C_fusion_rrf", cands, "rrf_k60")
        cands_cc = []
        for alpha in c["convex_alpha"]["values"]:
            fused = [[d for d, _ in fusion.convex(dl, bl, alpha, 10)] for dl, bl in zip(self.dense, lists)]
            cands_cc.append(self.record("C_fusion_convex", f"cc_alpha{alpha}", {"alpha": alpha, "k1": k1, "b": bb, "tokenizer": tok["name"]}, fused))
        ref_for_cc = best_rrf
        pool_all = cands_cc + [ref_for_cc]
        self.pick("C_fusion_convex_vs_best_rrf", pool_all, ref_for_cc["name"])

    def save(self, out: Path) -> None:
        out.mkdir(parents=True, exist_ok=True)
        (out / "sweep_results.json").write_text(json.dumps({"config": self.cfg, "questions": len(self.questions), "decisions": self.decisions,
                                                            "results": self.results}, ensure_ascii=False, indent=1), encoding="utf-8")
        lines = [f"# Hybrid sweep report ({self.cfg['id']}); {len(self.questions)} answerable dev questions, silver (pilot)\n",
                 "Selection rule (declared before running): " + self.cfg["selection_rule"] + "\n", "## Decisions\n",
                 "| stage | reference | best | R@5 ref -> best | paired diff (95% CI) | label |", "|---|---|---|---|---|---|"]
        for d in self.decisions:
            p = d["paired_vs_reference"]
            lines.append(f"| {d['stage']} | {d['reference']} | {d['best']} | {d['reference_overall']:.3f} -> {d['best_overall']:.3f} | "
                         f"{p['mean_diff']:+.3f} ({p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}) | {d['label']} |")
        by_stage: dict = {}
        for r in self.results:
            by_stage.setdefault(r["stage"], []).append(r)
        for stage, rows in by_stage.items():
            lines += [f"\n## {stage}\n", "| name | R@1 | R@5 | R@10 | MRR@10 | table R@5 | diff vs ref (95% CI) |", "|---|---|---|---|---|---|---|"]
            for r in rows:
                o, p = r["overall"], r.get("paired_vs_reference")
                diff = f"{p['mean_diff']:+.3f} ({p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f})" if p else ""
                lines.append(f"| {r['name']} | {o['recall@1']:.3f} | {o['recall@5']:.3f} | {o['recall@10']:.3f} | {o['mrr@10']:.3f} | "
                             f"{r['by_type'].get('table', {}).get('recall@5', float('nan')):.3f} | {diff} |")
        (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--model", choices=sorted(embed.MODELS), required=True)
    ap.add_argument("--parents", type=Path, required=True)
    ap.add_argument("--children", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: sweeps are immutable, choose a new --out")
    sweep = Sweep(args)
    sweep.run()
    sweep.save(args.out)
    print((args.out / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
