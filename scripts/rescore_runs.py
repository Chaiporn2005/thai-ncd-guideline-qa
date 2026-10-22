"""Re-score saved retrieval runs under the strict and the lenient relevance definition, without re-encoding anything.

Each run folder keeps `results.jsonl` (the ranked chunk ids). This reads the chunk set the run used (from its
`config.json`), the questions, optional `alt_evidence` sidecar files, and writes per run: `metrics.json` and
`per_question.json` (strict keys unchanged, lenient keys prefixed `lenient_`) to a NEW folder. Strict numbers must equal the
original `metrics.json`; the script checks that and stops if they differ.

Usage:
    python -X utf8 scripts/rescore_runs.py --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl \
        --alt data/questions/alt_evidence_duplicates.jsonl --runs data/index/runs/*-gpu --out data/index/runs_rescored
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import answer_match, evaluate  # noqa: E402

KS = [1, 3, 5, 10]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, nargs="+", required=True)
    ap.add_argument("--alt", type=Path, nargs="*", default=[])
    ap.add_argument("--corpus", type=Path, default=ROOT / "data/processed/normalized-v11")
    ap.add_argument("--runs", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--min-overlap", type=float, default=0.35)
    args = ap.parse_args(argv)

    questions = {q["qid"]: q for f in args.questions for q in read_jsonl(f)}
    for f in args.alt:
        for row in read_jsonl(f):
            questions[row["qid"]]["alt_evidence"] = row["alt_evidence"]
    page_texts = []
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        page_texts += [json.loads(x)["text"] for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    matcher = answer_match.AnswerMatcher(page_texts, args.min_overlap)

    chunk_cache: dict[str, dict] = {}
    for run in sorted(args.runs):
        if not (run / "results.jsonl").exists():
            continue
        config = json.loads((run / "config.json").read_text(encoding="utf-8"))["args"]
        chunk_dir = ROOT / config["chunks"].replace("\\", "/")
        units = chunk_cache.setdefault(str(chunk_dir), {c["chunk_id"]: c for c in read_jsonl(chunk_dir / "chunks.jsonl")})
        original = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
        per_q, by_type, gained = {}, defaultdict(dict), []
        for row in read_jsonl(run / "results.jsonl"):
            q = questions[row["qid"]]
            if not q["answerable"]:
                continue
            ranked = [units[h["chunk_id"]] for h in row["hits"]]
            scores = {**evaluate.score_question(ranked, q["evidence"], KS), **evaluate.score_lenient(ranked, q, KS, matcher)}
            per_q[q["qid"]] = scores
            by_type[q["type"]][q["qid"]] = scores
            if scores["lenient_hit@5"] > scores["hit@5"]:
                gained.append(q["qid"])
        keys = [f"{m}@{k}" for k in KS for m in ("recall", "hit", "mrr")]
        strict = evaluate.aggregate(per_q, keys)
        if strict != original["overall"]:
            sys.exit(f"{run.name}: strict numbers changed ({strict} vs {original['overall']}): the question set differs from the run's")
        out = args.out / run.name
        out.mkdir(parents=True, exist_ok=True)
        lenient_keys = ["lenient_" + k for k in keys]
        metrics = {"run": run.name, "units": original["units"], "mode": original["mode"], "split": original["split"],
                   "answerable": len(per_q), "strict": strict, "lenient": evaluate.aggregate(per_q, lenient_keys),
                   "ci95": {k: evaluate.bootstrap_ci([v[k] for v in per_q.values()])
                            for k in ("recall@5", "lenient_recall@5", "recall@10", "lenient_recall@10")},
                   "questions_that_gain_at_5": gained, "min_overlap": args.min_overlap,
                   "by_type": {t: {"n": len(v), **evaluate.aggregate(v, ["recall@5", "lenient_recall@5", "recall@10", "lenient_recall@10"])}
                               for t, v in sorted(by_type.items())}}
        (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (out / "per_question.json").write_text(json.dumps(per_q, indent=1), encoding="utf-8")
        s, l = strict, metrics["lenient"]
        print(f"{run.name:34s} R@5 strict {s['recall@5']:.3f} lenient {l['lenient_recall@5']:.3f} | "
              f"R@10 {s['recall@10']:.3f} -> {l['lenient_recall@10']:.3f} | gain@5: {len(gained)} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
