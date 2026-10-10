"""Run dense retrieval for a question set and score it (Track B, L1): results.jsonl, metrics.json, run_manifest.json.

Plain dense search: `--chunks` is the chunk set that was embedded into `--index`.
Parent-child: `--index` holds vectors of the small chunks (`--children`), `--chunks` is the larger parent set that is
returned and scored.

A `test` run is refused unless every question of the split is gold and the work tree is clean (README: the test split is
measured once per frozen configuration).

Usage:
    python -X utf8 scripts/run_retrieval.py --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl \
        --split dev --model e5-base --chunks data/index/chunks-v11-t256 --index data/index/dense-e5-base-t256 --out runs/dense-e5-t256
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import answer_match, embed, evaluate  # noqa: E402
from ncdqa.retrieval.dense import DenseIndex  # noqa: E402
from ncdqa.retrieval.parent_child import ParentChildIndex, build_parent_map  # noqa: E402

KS = [1, 3, 5, 10]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--split", choices=["dev", "test", "smoke", "all"], default="dev")
    ap.add_argument("--model", choices=sorted(embed.MODELS), required=True)
    ap.add_argument("--chunks", type=Path, required=True, help="chunk set that is returned and scored")
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--children", type=Path, help="chunk set of the vectors in --index (parent-child mode)")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--fetch", type=int, default=50, help="children fetched before collapsing to parents")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--alt", type=Path, nargs="*", default=[], help="alt_evidence sidecar files (scripts/build_alt_evidence.py)")
    ap.add_argument("--corpus", type=Path, default=ROOT / "data/processed/normalized-v11", help="pages used for the answer-match idf")
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: runs are immutable, choose a new --out")

    started = datetime.now(timezone.utc)
    questions = [q for q in read_jsonl(args.questions) if q["status"] != "rejected" and "??" not in q["question"]]
    if args.split != "all":
        questions = [q for q in questions if q["split"] == ("dev" if args.split == "smoke" else args.split)]
    if args.split == "smoke":
        questions = questions[:10]
    dirty = bool(git("status", "--porcelain"))
    if args.split == "test" and (dirty or any(q["status"] != "gold" for q in questions)):
        sys.exit("refused: a test run needs every test question gold and a clean work tree")

    for sidecar in args.alt:
        alt = {r["qid"]: r["alt_evidence"] for r in read_jsonl(sidecar)}
        for q in questions:
            if q["qid"] in alt:
                q["alt_evidence"] = alt[q["qid"]]
    page_texts = [json.loads(x)["text"] for f in sorted(args.corpus.glob("*/pages.jsonl"))
                  for x in f.read_text(encoding="utf-8").split("\n") if x.strip()]
    matcher = answer_match.AnswerMatcher(page_texts)

    units = {c["chunk_id"]: c for c in read_jsonl(args.chunks / "chunks.jsonl")}
    index = DenseIndex.load(args.index)
    if args.children:
        children = read_jsonl(args.children / "chunks.jsonl")
        search_index = ParentChildIndex(index, build_parent_map(children, list(units.values())))
    else:
        search_index = index

    model = embed.MODELS[args.model]
    st = embed.load(model)
    t0 = time.perf_counter()
    qvec = embed.encode(st, [q["question"] for q in questions], model.query_prefix, batch_size=16)
    encode_ms = (time.perf_counter() - t0) * 1000 / max(len(questions), 1)
    t1 = time.perf_counter()
    found = search_index.search(qvec, args.k, args.fetch) if args.children else search_index.search(qvec, args.k)
    search_ms = (time.perf_counter() - t1) * 1000 / max(len(questions), 1)

    rows, per_q, by_type, top_scores = [], {}, defaultdict(dict), {}
    for q, hits in zip(questions, found):
        ranked = [(h[0], h[1]) for h in hits]
        rows.append({"run_id": args.out.name, "qid": q["qid"], "variant": "A", "k": args.k, "query": q["question"],
                     "hits": [{"rank": r, "chunk_id": cid, "score": round(score, 5),
                               "document_id": units[cid]["document_id"], "edition_id": units[cid]["edition_id"],
                               "pdf_page_start": units[cid]["pdf_page_start"], "pdf_page_end": units[cid]["pdf_page_end"]}
                              for r, (cid, score) in enumerate(ranked, 1)],
                     "latency_ms": {"total": round(encode_ms + search_ms, 2), "encode": round(encode_ms, 2), "search": round(search_ms, 2)}})
        if q["answerable"]:
            per_q[q["qid"]] = {**evaluate.score_question([units[c] for c, _ in ranked], q["evidence"], KS),
                               **evaluate.score_lenient([units[c] for c, _ in ranked], q, KS, matcher)}
            by_type[q["type"]][q["qid"]] = per_q[q["qid"]]
        elif ranked:
            top_scores[q["qid"]] = ranked[0][1]

    keys = [f"{m}@{k}" for k in KS for m in ("recall", "hit", "mrr")]
    metrics = {"run": args.out.name, "model": model.key, "units": args.chunks.name,
               "mode": "parent-child" if args.children else "dense", "children": args.children.name if args.children else None,
               "split": args.split, "questions": len(questions), "answerable": len(per_q),
               "status_counts": {s: sum(q["status"] == s for q in questions) for s in ("silver", "gold")},
               "overall": evaluate.aggregate(per_q, keys),
               "lenient": evaluate.aggregate(per_q, ["lenient_" + k for k in keys]),
               "ci95": {k: evaluate.bootstrap_ci([v[k] for v in per_q.values()]) for k in ("recall@5", "recall@10", "mrr@10")},
               "by_type": {t: {"n": len(v), **evaluate.aggregate(v, ["recall@5", "recall@10", "mrr@10"])} for t, v in sorted(by_type.items())},
               "unanswerable": {"n": len(top_scores), "mean_top1_score": round(evaluate.mean(list(top_scores.values())), 4),
                                "answerable_mean_top1_score": round(evaluate.mean([r["hits"][0]["score"] for r in rows
                                                                                  if r["qid"] in per_q and r["hits"]]), 4)},
               "latency_ms_per_query": {"encode": round(encode_ms, 2), "search": round(search_ms, 2)},
               "caution": "silver questions are AI drafts: a pilot, not a result" if any(q["status"] == "silver" for q in questions) else ""}
    args.out.mkdir(parents=True)
    (args.out / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
    (args.out / "per_question.json").write_text(json.dumps(per_q, indent=1), encoding="utf-8")
    (args.out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    config = {"args": {k: str(v) for k, v in vars(args).items()}, "k_values": KS}
    (args.out / "config.json").write_text(json.dumps(config, indent=1), encoding="utf-8")

    index_manifest = json.loads((args.index / "index_manifest.json").read_text(encoding="utf-8"))
    from huggingface_hub import snapshot_download
    revision = Path(snapshot_download(model.hf_id, local_files_only=True)).name
    inventory = ROOT / "data/manifests" / f"corpus_{units[next(iter(units))]['corpus_version']}_inventory.json"
    manifest = {"run_id": args.out.name, "split": args.split if args.split in ("smoke", "dev", "test") else "dev", "variant": "A",
                "k": args.k, "git_commit": git("rev-parse", "HEAD"), "git_dirty": dirty,
                "config_path": str((args.out / "config.json").relative_to(ROOT)) if args.out.is_relative_to(ROOT) else "config.json",
                "config_sha256": sha256(args.out / "config.json"), "corpus_version": next(iter(units.values()))["corpus_version"],
                "corpus_inventory_sha256": sha256(inventory) if inventory.exists() else "0" * 64,
                "chunk_config_id": next(iter(units.values()))["chunk_config_id"], "chunks_sha256": sha256(args.chunks / "chunks.jsonl"),
                "embedding_model": {"name": model.hf_id, "revision": revision}, "bm25": None, "fusion": None,
                "index_sha256": index_manifest["vectors_sha256"], "questions_sha256": sha256(args.questions),
                "results_sha256": sha256(args.out / "results.jsonl"), "device": index_manifest.get("device", "cpu"),
                "machine": platform.processor() or platform.machine(), "python": platform.python_version(),
                "packages": {p: metadata.version(p) for p in ("torch", "sentence-transformers", "transformers", "numpy")},
                "started_at": started.isoformat().replace("+00:00", "Z"),
                "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "n_questions": len(questions),
                "notes": args.notes or metrics["mode"]}
    (args.out / "run_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("run", "mode", "questions", "answerable", "overall")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
