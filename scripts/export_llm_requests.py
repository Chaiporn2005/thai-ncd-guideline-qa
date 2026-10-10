"""Write the LLM requests for query rewriting, one row per (question, mode), for the Kaggle LLM kernel (Track B).

Prompts come from src/ncdqa/retrieval/query_rewrite.py, so the same text is used for local models and for hosted APIs. A question that
carries personal identifiers is not exported (it keeps its original wording). The few-shot examples are checked against the question
file: any example that shares a 20-character run with a question stops the export.

Usage:
    python -X utf8 scripts/export_llm_requests.py --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl --split dev \
        --out data/index/llm-requests/requests.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ncdqa.retrieval import query_rewrite as qr  # noqa: E402

MODES = ("rewrite", "hyde", "q2d")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    questions = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    questions = [q for q in questions if q["status"] != "rejected" and (args.split == "all" or q["split"] == args.split)]
    overlap = qr.examples_overlap([q["question"] for q in [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]])
    if overlap:
        sys.exit(f"few-shot examples overlap with questions: {overlap}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    skipped = 0
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for q in questions:
            if not qr.sendable(q["question"]):
                skipped += 1
                continue
            for mode in MODES:
                f.write(json.dumps({"id": f"{q['qid']}:{mode}", "mode": mode, "messages": qr.messages(mode, q["question"])}, ensure_ascii=False) + "\n")
    print(json.dumps({"questions": len(questions), "not_sendable": skipped, "requests": (len(questions) - skipped) * len(MODES)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
