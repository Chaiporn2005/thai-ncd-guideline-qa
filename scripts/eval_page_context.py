"""Measure the population tagging in scripts/page_context.py against chapters whose population is known.

Ground truth comes from the table of contents of the Thai diabetes CPG 2566 (dm-cpg-2566-revised-2567):
chapters 16-17 (children and adolescents) are PDF pages 201-234 and chapter 18 (pregnancy) is pages 235-244;
every other page is general. The old method (any keyword hit on the page) is reported beside the context method
so the improvement, and the pages that are still wrong, can be checked by hand.

Usage:
    python -X utf8 scripts/eval_page_context.py --corpus data/processed/normalized-v7
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_context as pc  # noqa: E402

DOCUMENT = "dm-cpg-2566-revised-2567"
TRUTH_RANGES = {"pediatric": (201, 234), "pregnancy": (235, 244)}
KEYWORDS = {
    "pediatric": re.compile(r"เด็ก|วัยรุ่น|ทารก|ปฐมวัย|pediatric|paediatric|children|adolescen", re.I),
    "pregnancy": re.compile(r"ตั้งครรภ์|มีครรภ์|ขณะครรภ์|ให้นมบุตร|หลังคลอด|GDM|gestational|pregnan", re.I),
}


def truth(page: int) -> str | None:
    return next((label for label, (a, b) in TRUTH_RANGES.items() if a <= page <= b), None)


def metrics(rows: list[dict], predict, label: str) -> dict:
    tp = fp = fn = 0
    for row in rows:
        if row["status"] == "empty":
            continue
        actual, guessed = truth(row["pdf_page"]) == label, predict(row)
        tp += actual and guessed
        fp += (not actual) and guessed
        fn += actual and (not guessed)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(tp / (tp + fp), 2) if tp + fp else None,
            "recall": round(tp / (tp + fn), 2) if tp + fn else None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    args = parser.parse_args(argv)
    path = args.corpus / DOCUMENT / "pages.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]
    context = pc.population_for_document(rows)
    report = {}
    for label in TRUTH_RANGES:
        report[label] = {
            "keyword_any_hit": metrics(rows, lambda r: bool(KEYWORDS[label].search(r["text"])), label),
            "context_all": metrics(rows, lambda r: context[r["pdf_page"]]["label"] == label, label),
            "context_high_confidence": metrics(
                rows, lambda r: context[r["pdf_page"]]["label"] == label and context[r["pdf_page"]]["confidence"] == "high", label),
        }
    report["pages_labelled_outside_truth"] = [
        {"page": r["pdf_page"], "label": context[r["pdf_page"]]["label"], "confidence": context[r["pdf_page"]]["confidence"]}
        for r in rows if context[r["pdf_page"]]["label"] not in (None, "mixed", truth(r["pdf_page"]))]
    report["truth_pages_missed"] = [r["pdf_page"] for r in rows if r["status"] != "empty" and truth(r["pdf_page"])
                                    and context[r["pdf_page"]]["label"] not in (truth(r["pdf_page"]),)]
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
