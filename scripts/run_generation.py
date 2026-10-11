"""Run the answer pipeline over a question set and write an immutable run folder (Track C).

    python -X utf8 scripts/run_generation.py --questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl --split smoke --out data/index/runs/gen/smoke1

Splits: dev, test, smoke (first --limit dev questions), all. A `test` run needs every test question gold and a clean work tree
(same rule as scripts/run_retrieval.py): freeze the config and prompt first, then run once. Output folder:
  answers.jsonl  one row per question: gold fields + the pipeline result with its trace
  manifest.json  config, config_id, git commit, provider/model, counts per status, cache hits, time
With --retrieval-results (a results.jsonl of Track B's frozen runs, e.g. data/handoff/track_c_20261012/results/dev-B/results.jsonl) and --chunks
(chunks-v12-t512.jsonl) the hits are taken from those saved rankings (top k of the config) instead of calling the Retriever, so every variant is answered
from exactly the ranking Track B reported, and no index or GPU is needed.
The pipeline config is `configs/rag/generate_v1.json`; override pieces for an ablation with --set a.b.c=value (recorded in the manifest).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag.pipeline import DEFAULT_CONFIG, Pipeline, load_pipeline  # noqa: E402


def code_hashes() -> dict:
    """sha256 of the files that decide an answer. Untracked files do not show up in `git status --untracked-files=no`, so the manifest carries its own
    freeze evidence: the same hashes mean the same prompt, validator, pipeline and graph code."""
    import hashlib
    files = sorted((ROOT / "src/ncdqa/rag").glob("*.py")) + [ROOT / "src/ncdqa/llm/client.py", ROOT / "scripts/run_generation.py"]
    return {str(f.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(f.read_bytes()).hexdigest()[:16] for f in files}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]


def hits_from_saved(row: dict, units: dict, k: int) -> list[dict]:
    out = []
    for h in row["hits"][:k]:
        c = units[h["chunk_id"]]
        out.append({"rank": h["rank"], "chunk_id": h["chunk_id"], "score": h["score"], "document_id": c["document_id"], "edition_id": c["edition_id"],
                    "pdf_page_start": c["pdf_page_start"], "pdf_page_end": c["pdf_page_end"], "text": c["text"], "injection_flags": c["injection_flags"]})
    return out


def apply_overrides(cfg: dict, items: list[str]) -> None:
    for item in items:
        path, _, raw = item.partition("=")
        node = cfg
        keys = path.split(".")
        for key in keys[:-1]:
            node = node[key]
        if keys[-1] not in node:
            sys.exit(f"--set {path}: no such key in the config")
        node[keys[-1]] = json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--split", choices=["dev", "test", "smoke", "all"], default="dev")
    ap.add_argument("--limit", type=int, default=3, help="questions in a smoke run")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--set", dest="overrides", action="append", default=[], metavar="a.b=json", help="override a config value (ablation)")
    ap.add_argument("--pipeline", default="plain", help="plain (src/ncdqa/rag/pipeline.py), graph (the LangGraph version), or module:Class of your own pipeline, e.g. ncdqa.rag.react_agent:ReactAgent. "
                    "The class is built as Class(retriever, client, cfg) and must have answer(question, retrieved=None) -> dict in the same shape (docs/handoff_react_and_track_d.md)")
    ap.add_argument("--retrieval-results", type=Path, help="results.jsonl of a saved retrieval run (variant A, B or C)")
    ap.add_argument("--chunks", type=Path, help="chunks jsonl that holds the text of the chunk ids in --retrieval-results")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--notes", default="")
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: runs are immutable, choose a new --out")

    questions = [q for q in read_jsonl(args.questions) if q["status"] != "rejected"]
    if args.split != "all":
        questions = [q for q in questions if q["split"] == ("dev" if args.split == "smoke" else args.split)]
    if args.split == "smoke":
        questions = questions[:args.limit]
    dirty = bool(git("status", "--porcelain", "--untracked-files=no", "--", "scripts", "src", "configs", "data/schemas", "tests"))
    if args.split == "test" and (dirty or any(q["status"] != "gold" for q in questions)):
        sys.exit("refused: a test run needs every test question gold and a clean work tree")

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    apply_overrides(cfg, args.overrides)
    from ncdqa.llm.client import LLMClient, load_providers
    from ncdqa.llm.env import load_env
    load_env()
    provider = load_providers(ROOT / cfg["llm"]["providers_file"])[cfg["llm"]["provider"]]
    client = LLMClient(provider, ROOT / cfg["llm"]["cache_dir"] / f'{cfg["llm"]["provider"]}.jsonl')
    saved = None
    if args.retrieval_results:
        if not args.chunks:
            sys.exit("--retrieval-results needs --chunks")
        units = {c["chunk_id"]: c for c in read_jsonl(args.chunks)}
        saved = {r["qid"]: r for r in read_jsonl(args.retrieval_results)}
        variant = next(iter(saved.values()))["variant"]
        cfg["retrieval"]["variant"] = variant
        missing = [q["qid"] for q in questions if q["qid"] not in saved]
        if missing:
            sys.exit(f"no saved ranking for {missing[:5]}...")
        retriever = None
    else:
        from ncdqa.retrieval.search import Retriever
        retriever = Retriever()
    if args.pipeline == "graph":
        from ncdqa.rag.graph import GraphPipeline
        pipe = GraphPipeline(retriever, client, cfg)
    elif args.pipeline == "plain":
        pipe = Pipeline(retriever, client, cfg)
    else:
        import importlib
        module, _, cls = args.pipeline.partition(":")
        pipe = getattr(importlib.import_module(module), cls)(retriever, client, cfg)

    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    rows, status = [], Counter()
    args.out.mkdir(parents=True)
    with (args.out / "answers.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for q in questions:
            hits = None if saved is None else hits_from_saved(saved[q["qid"]], units, cfg["retrieval"]["k"])
            result = pipe.answer(q["question"], retrieved=hits)
            status[result["status"]] += 1
            row = {"qid": q["qid"], "split": q["split"], "type": q["type"], "answerable": q["answerable"], "gold_answer": q["answer"],
                   "gold_evidence": q["evidence"], **result}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            print(f'{q["qid"]} {result["status"]}', flush=True)
    cached = sum(1 for r in rows if r["trace"].get("cached"))
    manifest = {"run": args.out.name, "split": args.split, "questions": len(rows), "config": cfg, "config_id": pipe.config_id,
                "pipeline": args.pipeline, "overrides": args.overrides, "provider": provider.name, "model": provider.model, "git_commit": git("rev-parse", "HEAD"),
                "git_dirty": dirty, "code_sha256": code_hashes(), "status_counts": dict(status), "llm_cache_hits": cached, "llm_calls": sum(1 for r in rows if "cached" in r["trace"]),
                "started_utc": started.isoformat(timespec="seconds"), "seconds": round(time.perf_counter() - t0, 1), "notes": args.notes}
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["status_counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
