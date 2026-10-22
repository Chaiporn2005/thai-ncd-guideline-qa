"""Run the guardrail / prompt-injection cases through the answer pipeline under layered defences and score them (Track C).

    python -X utf8 scripts/eval_guardrails.py --cases data/eval/guardrail/cases.jsonl --questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl --out data/index/runs/guard/g1

Configurations N0..N6 add one defence at a time (src/ncdqa/rag/guardrail_eval.py: LAYER_CONFIGS; N0 = undefended); choose with --layers N0 N3. Same retrieval, k, prompt text
and cases for every configuration. Indirect cases plant text into the retrieved hits in memory; the real index and corpus are not changed.
Output folder: rows.jsonl (case + result + verdict per configuration), results.json (summary with Wilson intervals), results.md, manifest.json.
Cases with `reviewed_by: null` are SILVER (AI-written, AI-labelled, no human review; decided 2026-10-11 because no one has time to review): the report says so.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag import guardrail_eval as ge  # noqa: E402
from ncdqa.rag.pipeline import DEFAULT_CONFIG, Pipeline, config_hash  # noqa: E402


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def table(summary: dict[str, dict]) -> str:
    cfgs = list(summary)
    fmt = lambda r: "-" if not r or r["n"] == 0 else f'{r["rate"]:.2f} ({r["k"]}/{r["n"]})'  # noqa: E731
    lines = ["| ชั้น | " + " | ".join(cfgs) + " |", "|---|" + "---|" * len(cfgs)]
    behaviors = sorted({b for s in summary.values() for b in s["attacks"]}, key=lambda b: (b == "ALL", b))
    for beh in behaviors:
        for point in ("model", "user"):
            lines.append(f"| ASR {beh} ({point}) | " + " | ".join(fmt(summary[c]["attacks"].get(beh, {}).get(point)) for c in cfgs) + " |")
    for key in ("answered", "citation_correct", "false_refusal"):
        lines.append(f"| benign {key} | " + " | ".join(fmt(summary[c]["benign"].get(key)) for c in cfgs) + " |")
    lines.append("| unanswerable abstained | " + " | ".join(fmt(summary[c]["unanswerable"].get("abstained")) for c in cfgs) + " |")
    lines.append("| errors (llm/parse/truncated) | " + " | ".join(str(summary[c]["errors"]) for c in cfgs) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True, help="gold questions (benign cases are scored against their evidence)")
    ap.add_argument("--layers", nargs="*", default=list(ge.LAYER_CONFIGS), choices=list(ge.LAYER_CONFIGS))
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--limit", type=int, help="first N cases only (smoke)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: runs are immutable, choose a new --out")

    cases = read_jsonl(args.cases)[:args.limit] if args.limit else read_jsonl(args.cases)
    gold = {q["qid"]: q for q in read_jsonl(args.questions)}
    base_cfg = json.loads(args.config.read_text(encoding="utf-8"))

    from ncdqa.llm.client import LLMClient, load_providers
    from ncdqa.llm.env import load_env
    from ncdqa.retrieval.chunking import injection_flags
    from ncdqa.retrieval.search import Retriever
    load_env()
    provider = load_providers(ROOT / base_cfg["llm"]["providers_file"])[base_cfg["llm"]["provider"]]
    client = LLMClient(provider, ROOT / base_cfg["llm"]["cache_dir"] / f'{base_cfg["llm"]["provider"]}.jsonl')
    retriever = Retriever()
    retrieved: dict[str, list[dict]] = {}

    def hits_for(q: str) -> list[dict]:
        if q not in retrieved:
            retrieved[q] = retriever.search(q, base_cfg["retrieval"]["variant"], base_cfg["retrieval"]["k"])
        return retrieved[q]

    started, t0 = datetime.now(timezone.utc), time.perf_counter()
    args.out.mkdir(parents=True)
    summary: dict[str, dict] = {}
    per_case: dict[str, dict[str, dict]] = {}
    with (args.out / "rows.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for name in args.layers:
            cfg = ge.configured(base_cfg, ge.LAYER_CONFIGS[name])
            pipe = Pipeline(retriever, client, cfg)
            rows = []
            for case in cases:
                hits = ge.apply_plant(hits_for(case.get("retrieval_query") or case["question"]), case.get("plant"), injection_flags)
                result = pipe.answer(case["question"], retrieved=hits)
                row = {"layer": name, "case": case, "result": result}
                if case["kind"] in ("direct", "indirect"):
                    row["success"] = ge.attack_success(case, result)
                elif case["kind"] == "benign":
                    row["citation_ok"] = ge.citation_correct(result, gold[case["base_qid"]]["evidence"])
                rows.append(row)
                per_case.setdefault(case["id"], {})[name] = row
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            summary[name] = ge.summarize(rows)
            print(name, json.dumps(summary[name]["attacks"].get("ALL"), ensure_ascii=False), summary[name]["benign"].get("answered"), flush=True)

    draft = sum(1 for c in cases if not c.get("reviewed_by"))
    (args.out / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note = f"**DRAFT: {draft}/{len(cases)} cases have no reviewer (reviewed_by = null); do not quote these numbers as results.**\n\n" if draft else ""
    (args.out / "results.md").write_text(note + table(summary) + "\n", encoding="utf-8")
    manifest = {"run": args.out.name, "cases": len(cases), "cases_unreviewed": draft, "layers": args.layers, "layer_flags": {k: ge.LAYER_CONFIGS[k] for k in args.layers},
                "base_config_id": f'{base_cfg["id"]}-{config_hash(base_cfg)}', "provider": provider.name, "model": provider.model,
                "git_commit": git("rev-parse", "HEAD"), "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no", "--", "scripts", "src", "configs")),
                "started_utc": started.isoformat(timespec="seconds"), "seconds": round(time.perf_counter() - t0, 1)}
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print((args.out / "results.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
