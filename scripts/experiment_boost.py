"""Soft boost by disease group and population on top of the hybrid retrieval of a finished sweep (Track B, technique 4).

Why: in the pilot most misses ended in a different document on a neighbouring topic (another disease group). A question usually
shows its group ("ไต", "ความดัน"), and every unit knows its document's primary group and its page population tag.

Group boost: the question vector is compared with the centroid of each group's child-chunk vectors; p(group | question) =
softmax(tau * cosine). A unit's score gets + w_group * p(its group). It is a soft push, never a filter: a wrong guess costs at
most w_group, and a question that spans groups loses nothing.
Population boost: if the question names a population (child/pregnancy/elderly) units tagged with it get + w_pop; optionally
(`penalty`) units tagged with another non-general population get - w_pop. The tags come from the page-tag review (docs/population_tag_experiment.md).

tau, w_group, w_pop are our own grids (no paper fixes them for this corpus); the selection rule is the one declared in the sweep
config: highest Recall@5 against the unboosted baseline, with the paired interval reported, 'not distinguishable' kept provisional.

Usage:
    python -X utf8 scripts/experiment_boost.py --sweep data/index/sweeps/hybrid-v1-bge-m3 --model bge-m3 --questions ... \
        --parents data/index/chunks-v11-t512 --children data/index/chunks-v11-t128 --index data/index/kaggle/dense-bge-m3-t128 --out data/index/sweeps/boost-bge-m3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from sweep_hybrid import Sweep, read_jsonl  # noqa: E402
from ncdqa.retrieval import embed, evaluate, fusion  # noqa: E402
from ncdqa.retrieval.thai_tokens import load_dictionary, tokenize  # noqa: E402
from ncdqa.retrieval.bm25 import BM25Index, tokenize_units  # noqa: E402

POPULATION_TERMS = {
    "pediatric": re.compile(r"เด็ก|วัยรุ่น|ทารก|ปฐมวัย|นักเรียน"),
    "pregnancy": re.compile(r"ตั้งครรภ์|มีครรภ์|หลังคลอด|ให้นมบุตร|คนท้อง"),
    "elderly": re.compile(r"สูงอายุ|สูงวัย|ผู้เฒ่า"),
}


def question_population(text: str) -> str | None:
    found = [p for p, rx in POPULATION_TERMS.items() if rx.search(text)]
    return found[0] if len(found) == 1 else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
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

    prior = json.loads((args.sweep / "sweep_results.json").read_text(encoding="utf-8"))
    chosen = {d["stage"]: d["best"] for d in prior["decisions"]}
    tok_name, bm_name = chosen["A_tokenizer"], chosen["B_bm25_params"]
    alpha = float(chosen["C_fusion_convex_vs_best_rrf"].replace("cc_alpha", "")) if chosen["C_fusion_convex_vs_best_rrf"].startswith("cc_") else None
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    tok = next(v for v in cfg["stage_a_tokenizer"]["variants"] if v["name"] == tok_name)
    bm = next(s for s in cfg["stage_b_bm25_params"]["settings"] if s["name"] == bm_name)

    ns = argparse.Namespace(config=args.config, questions=args.questions, model=args.model, parents=args.parents,
                            children=args.children, index=args.index)
    sw = Sweep(ns)
    bm_lists = sw.bm25_lists(tok["mode"], tok.get("dictionary"), bm["k1"], bm["b"])
    groups = {r["document_id"]: r["primary_group"] for r in json.loads((ROOT / "data/by_disease/index.json").read_text(encoding="utf-8"))["records"]}
    unit_group = {c["chunk_id"]: groups.get(c["document_id"]) for c in sw.parents}
    unit_pop = {c["chunk_id"]: c.get("population", "general") for c in sw.parents}

    # group centroids from the child vectors (the same vectors the dense side uses)
    vectors = np.load(args.index / "vectors.npy")
    ids = json.loads((args.index / "chunk_ids.json").read_text(encoding="utf-8"))
    child_doc = {c["chunk_id"]: c["document_id"] for c in read_jsonl(args.children / "chunks.jsonl")}
    by_group: dict[str, list[int]] = defaultdict(list)
    for i, cid in enumerate(ids):
        g = groups.get(child_doc[cid])
        if g and g != "EXCLUDED":
            by_group[g].append(i)
    names = sorted(by_group)
    centroids = np.stack([vectors[by_group[g]].mean(axis=0) for g in names])
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
    model = embed.MODELS[args.model]
    qvec = embed.encode(embed.load(model), [q["question"] for q in sw.questions], model.query_prefix)
    sims = qvec @ centroids.T

    truth = [groups.get(q["evidence"][0]["document_id"]) for q in sw.questions]
    top1 = [names[i] for i in sims.argmax(axis=1)]
    acc = sum(a == b for a, b in zip(top1, truth)) / len(truth)
    confusion = Counter((t, p) for t, p in zip(truth, top1) if t != p)

    def run(base_alpha: float | None, tau: float, w_group: float, w_pop: float, penalty: bool) -> list[list[str]]:
        out = []
        for i, q in enumerate(sw.questions):
            dl, bl = sw.dense[i], bm_lists[i]
            scores = dict(fusion.convex(dl, bl, base_alpha, 200)) if base_alpha is not None else dict(fusion.minmax(dl))
            if w_group:
                e = np.exp(tau * (sims[i] - sims[i].max()))
                p = dict(zip(names, e / e.sum()))
                scores = {u: s + w_group * p.get(unit_group[u], 0.0) for u, s in scores.items()}
            pop = question_population(q["question"]) if w_pop else None
            if pop:
                scores = {u: s + (w_pop if unit_pop[u] == pop else (-w_pop if penalty and unit_pop[u] not in ("general", pop) else 0.0))
                          for u, s in scores.items()}
            out.append([u for u, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:10]])
        return out

    rows = [sw.record("0_baseline", f"hybrid_best_provisional ({tok_name}, {bm_name}, alpha={alpha})", {"alpha": alpha}, run(alpha, 0, 0, 0, False))]
    rows.append(sw.record("0_baseline", "dense_only", {}, run(None, 0, 0, 0, False)))
    base = rows[0]
    grid = []
    for tau in (20.0, 50.0):
        for w in (0.05, 0.1, 0.2, 0.3):
            grid.append(sw.record("group_boost", f"group tau{tau:g} w{w}", {"tau": tau, "w_group": w}, run(alpha, tau, w, 0, False)))
    n_pop = sum(question_population(q["question"]) is not None for q in sw.questions)
    for w in (0.1, 0.2, 0.4):
        for pen in (False, True):
            grid.append(sw.record("population_boost", f"population w{w}{' +penalty' if pen else ''}", {"w_pop": w, "penalty": pen}, run(alpha, 0, 0, w, pen)))
    ref_name = base["name"]
    cands = [base] + grid
    best = sw.pick("boost", cands, ref_name)
    # also report group + population together with the best group setting
    bg = max((g for g in grid if g["stage"] == "group_boost"), key=lambda e: (e["overall"]["recall@5"], e["overall"]["mrr@10"]))
    bp = max((g for g in grid if g["stage"] == "population_boost"), key=lambda e: (e["overall"]["recall@5"], e["overall"]["mrr@10"]))
    both = sw.record("group_plus_population", f"{bg['name']} + {bp['name']}", {**bg["params"], **bp["params"]},
                     run(alpha, bg["params"]["tau"], bg["params"]["w_group"], bp["params"]["w_pop"], bp["params"]["penalty"]))
    sw.cfg = {**sw.cfg, "id": "boost_v1", "selection_rule": cfg["selection_rule"]}
    sw.save(args.out)
    extra = {"group_classifier_top1_accuracy": round(acc, 3), "questions": len(truth), "confusions": {f"{t}->{p}": n for (t, p), n in confusion.most_common(8)},
             "questions_naming_a_population": n_pop, "groups": names, "baseline_chain": {"tokenizer": tok_name, "bm25": bm_name, "alpha": alpha},
             "group_plus_population_vs_baseline": evaluate.paired_bootstrap({q: v["recall@5"] for q, v in base["per_question"].items()},
                                                                            {q: v["recall@5"] for q, v in both["per_question"].items()})}
    (args.out / "boost_extra.json").write_text(json.dumps(extra, ensure_ascii=False, indent=1), encoding="utf-8")
    print((args.out / "report.md").read_text(encoding="utf-8"))
    print(json.dumps(extra, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
