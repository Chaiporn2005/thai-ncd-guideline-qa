"""Run the OWASP-mapped guardrail cases through a pipeline under three systems and report attack success per OWASP risk (Track C).

    python -X utf8 scripts/eval_owasp.py --cases data/eval/guardrail/cases_owasp_v1.jsonl --questions data/handoff/track_c_20261012/questions_all_reviewed.jsonl \
        --pipeline plain --out data/index/runs/guard/owasp_plain
    python -X utf8 scripts/eval_owasp.py ... --pipeline react --out data/index/runs/guard/owasp_react        # also react-graph

Systems (everything else equal: same retrieval, k, LLM, cases):
  N0  the undefended prompt (no rules, no schema, no validator, no input guard); a reference point, plain pipeline only
  S0  the system as delivered: layers N7 + the personal-data and scope guards (what demo.py runs)
  S2  the delivered demo: S1 but personal data is masked (G1 = B) instead of refused: MaskingPipeline + owasp_demo_guards (length, scope, injection patterns) + the rest of S1
  S1  S0 + the OWASP guardrails: length guard, injection-pattern guard, flagged chunks dropped inside the search tool, and the output guard (markup/URL, prompt text, personal data)
Planted text (indirect cases) is placed into the results of EVERY search the pipeline or the agent makes, so a ReAct agent meets it in its observations; the index is never changed.
Cases with `needs_tools` are skipped for the plain pipeline (it has no tools). Cases with `reviewed_by: null` are SILVER: the report says so.
Output folder: rows.jsonl, results.json (per OWASP id, per system, Wilson intervals), results.md, manifest.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag import guardrail_eval as ge  # noqa: E402
from ncdqa.rag import owasp_guards as og  # noqa: E402
from ncdqa.rag.guards import default_guards  # noqa: E402

REACT_OVERRIDES = {"agent.seed_search": True, "agent.max_steps": 3}      # the frozen_react_v1 settings


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


class PlantedRetriever:
    """The real retriever, with the current case's planted text put into every result list. `clean` keeps the unplanted hits' text (what the evidence legitimately says)."""

    def __init__(self, inner, flags_of):
        self.inner, self.flags_of, self.plant, self.clean = inner, flags_of, None, {}

    def set_case(self, plant: dict | None) -> None:
        self.plant, self.clean = plant, {}

    def search(self, query: str, variant: str, k: int, filters: dict | None = None) -> list[dict]:
        hits = self.inner.search(query, variant, k, filters)
        for h in hits:
            self.clean[h["chunk_id"]] = h["text"]
        return ge.apply_plant(hits, self.plant, self.flags_of)


def table(summary: dict, systems: list[str]) -> str:
    fmt = lambda r: "-" if not r or not r["n"] else f'{r["rate"]:.2f} ({r["k"]}/{r["n"]})'  # noqa: E731
    lines = ["| OWASP | จุดวัด | " + " | ".join(systems) + " |", "|---|---|" + "---|" * len(systems)]
    for owasp in sorted(k for k in summary[systems[0]]["by_owasp"] if k != "ALL") + ["ALL"]:
        for point in ("model", "user"):
            lines.append(f"| {owasp} | ASR {point} | " + " | ".join(fmt(summary[s]["by_owasp"].get(owasp, {}).get(point)) for s in systems) + " |")
    for key in ("answered", "citation_correct", "false_refusal"):
        lines.append(f"| benign | {key} | " + " | ".join(fmt(summary[s]["benign"].get(key)) for s in systems) + " |")
    lines.append("| unanswerable | abstained | " + " | ".join(fmt(summary[s]["unanswerable"].get("abstained")) for s in systems) + " |")
    lines.append("| tokens/question | mean (attack cases) | " + " | ".join(str(summary[s]["mean_tokens_attack"]) for s in systems) + " |")
    lines.append("| errors | llm/parse/truncated | " + " | ".join(str(summary[s]["errors"]) for s in systems) + " |")
    return "\n".join(lines)


def summarize(rows: list[dict]) -> dict:
    by: dict[str, list[dict]] = defaultdict(list)
    benign, unans, toks = [], [], []
    errors = 0
    for r in rows:
        st = r["result"]["status"]
        errors += st in ("llm_error", "parse_error", "truncated")
        kind = r["case"]["kind"]
        if kind in ("direct", "indirect"):
            by[r["case"]["owasp"]].append(r)
            by["ALL"].append(r)
            toks.append((r["result"]["trace"].get("usage") or {}).get("total_tokens", 0))
        elif kind == "benign":
            benign.append(r)
        elif kind == "unanswerable":
            unans.append(r)
    out: dict = {"by_owasp": {k: {p: ge.rate(sum(i["success"][p] for i in v), len(v)) for p in ("model", "user")} for k, v in by.items()}, "errors": errors,
                 "mean_tokens_attack": round(sum(toks) / len(toks)) if toks else 0, "benign": {}, "unanswerable": {}}
    refusals = ge.ABSTAIN_STATUSES + ("refused_input", "blocked_output")
    if benign:
        answered = [r for r in benign if r["result"]["status"] == "answered"]
        scored = [r for r in answered if r.get("citation_ok") is not None]
        out["benign"] = {"answered": ge.rate(len(answered), len(benign)), "citation_correct": ge.rate(sum(r["citation_ok"] for r in scored), len(scored)),
                         "false_refusal": ge.rate(sum(r["result"]["status"] in refusals for r in benign), len(benign))}
    if unans:
        out["unanswerable"] = {"abstained": ge.rate(sum(r["result"]["status"] in refusals for r in unans), len(unans))}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--pipeline", choices=["plain", "react", "react-graph"], default="plain")
    ap.add_argument("--systems", nargs="*", help="default: N0 S0 S1 for plain, S0 S1 for the agents")
    ap.add_argument("--chunks", type=Path, default=ROOT / "data/handoff/track_c_20261012/chunks/chunks-v12-t512.jsonl")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        sys.exit(f"{args.out} exists: runs are immutable, choose a new --out")
    systems = args.systems or (["N0", "S0", "S1"] if args.pipeline == "plain" else ["S0", "S1"])

    cases = read_jsonl(args.cases)[:args.limit] if args.limit else read_jsonl(args.cases)
    gold = {q["qid"]: q for q in read_jsonl(args.questions)}
    base_path = ROOT / ("configs/rag/generate_v1.json" if args.pipeline == "plain" else "configs/rag/react_v1.json")
    base_cfg = json.loads(base_path.read_text(encoding="utf-8"))
    if args.pipeline != "plain":
        for path, v in REACT_OVERRIDES.items():
            a, b = path.split(".")
            base_cfg[a][b] = v

    from ncdqa.llm.client import LLMClient, load_providers
    from ncdqa.llm.env import load_env
    from ncdqa.rag.pipeline import Pipeline, config_hash
    from ncdqa.retrieval.chunking import injection_flags
    from ncdqa.retrieval.search import Retriever
    load_env()
    provider = load_providers(ROOT / base_cfg["llm"]["providers_file"])[base_cfg["llm"]["provider"]]
    client = LLMClient(provider, ROOT / base_cfg["llm"]["cache_dir"] / f'{base_cfg["llm"]["provider"]}.jsonl')
    planted = PlantedRetriever(Retriever(), injection_flags)

    def build(system: str):
        layers = ge.LAYER_CONFIGS["N0" if system == "N0" else "N7"]
        cfg = ge.configured(base_cfg, layers)
        if system in ("S1", "S2"):
            retriever, guards = og.GuardedRetriever(planted), (og.owasp_input_guards() if system == "S1" else og.owasp_demo_guards())
        else:
            retriever, guards = planted, ([] if system == "N0" else default_guards())
        if args.pipeline == "plain":
            pipe = Pipeline(retriever, client, cfg, guards)
        elif args.pipeline == "react":
            from ncdqa.rag.react_agent import ReactAgent
            pipe = ReactAgent(retriever, client, cfg, guards)
        else:
            from ncdqa.rag.react_graph import GraphReactAgent
            pipe = GraphReactAgent(retriever, client, cfg, guards)
        if system in ("S1", "S2"):
            pipe = og.GuardedPipeline(pipe, lambda: "\n".join(planted.clean.values()))
        if system == "S2":
            from ncdqa.rag.guards import MaskingPipeline
            pipe = MaskingPipeline(pipe)
        return pipe

    started, t0 = datetime.now(timezone.utc), time.perf_counter()
    args.out.mkdir(parents=True)
    summary: dict[str, dict] = {}
    with (args.out / "rows.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for system in systems:
            pipe, rows = build(system), []
            for case in cases:
                if case.get("needs_tools") and args.pipeline == "plain":
                    continue
                planted.set_case(case.get("plant"))
                result = pipe.answer(case["question"])
                row = {"system": system, "case": case, "result": result}
                if case["kind"] in ("direct", "indirect"):
                    row["success"] = ge.attack_success(case, result)
                elif case["kind"] == "benign" and case.get("base_qid"):
                    row["citation_ok"] = ge.citation_correct(result, gold[case["base_qid"]]["evidence"])
                rows.append(row)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            summary[system] = summarize(rows)
            print(system, json.dumps(summary[system]["by_owasp"].get("ALL"), ensure_ascii=False), summary[system]["benign"].get("answered"), flush=True)

    skipped = sum(1 for c in cases if c.get("needs_tools")) if args.pipeline == "plain" else 0
    draft = sum(1 for c in cases if not c.get("reviewed_by"))
    (args.out / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    note = f"**SILVER: {draft}/{len(cases)} cases have no human reviewer; quote with that label.** pipeline = {args.pipeline}; {skipped} tool cases skipped (no tools).\n\n"
    (args.out / "results.md").write_text(note + table(summary, systems) + "\n", encoding="utf-8")
    manifest = {"run": args.out.name, "pipeline": args.pipeline, "systems": systems, "cases": len(cases), "cases_unreviewed": draft, "tool_cases_skipped": skipped,
                "base_config_id": f'{base_cfg["id"]}-{config_hash(base_cfg)}', "model": provider.model, "git_commit": git("rev-parse", "HEAD"),
                "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no", "--", "scripts", "src", "configs")),
                "started_utc": started.isoformat(timespec="seconds"), "seconds": round(time.perf_counter() - t0, 1)}
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print((args.out / "results.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
