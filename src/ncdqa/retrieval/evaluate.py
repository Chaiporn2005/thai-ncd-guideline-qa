"""Retrieval metrics: relevance rule, Recall@k, Hit@k, MRR@k and a paired bootstrap (Track B).

Relevance rule (data/schemas/rag/README.md, proposal D-RAG-008): a retrieved unit is relevant to one piece of evidence
when its `edition_id` equals the evidence `edition_id`, the evidence `pdf_page` lies in `pdf_page_start..pdf_page_end`, and
at least half of the evidence `quote` (whitespace collapsed) appears in the unit's `text`. Gold evidence is page/quote
based, so the same questions stay valid when chunking changes.

Per answerable question and cut-off k:
* Recall@k = (evidence items covered by the top-k) / (evidence items of the question); a one-page question is 0 or 1,
  a multi_page question can be 0.5.
* Hit@k    = 1 if at least one evidence item is covered, else 0.
* MRR@k    = 1 / rank of the first unit that covers any evidence (0 if none within k).
Unanswerable questions are left out of these means; they are reported by how confident the top hit is (for abstention).
"""

from __future__ import annotations

import random
import re
from typing import Iterable

_SPACE = re.compile(r"\s+")


def collapse(text: str) -> str:
    return _SPACE.sub("", text)


def covers(unit: dict, evidence: dict, collapsed_text: str | None = None) -> bool:
    if unit["edition_id"] != evidence["edition_id"]:
        return False
    if not unit["pdf_page_start"] <= evidence["pdf_page"] <= unit["pdf_page_end"]:
        return False
    quote = collapse(evidence["quote"])
    text = collapsed_text if collapsed_text is not None else collapse(unit["text"])
    if quote in text:
        return True
    half = quote[: max(len(quote) // 2, 1)]  # "at least half of the quote": the first half, or the second half, must be present
    return half in text or quote[len(quote) // 2:] in text


def ranked_cover(ranked_units: list[dict], evidence: list[dict]) -> list[set[int]]:
    """For each rank, the set of evidence indices the unit at that rank covers."""
    out = []
    for unit in ranked_units:
        text = collapse(unit["text"])
        out.append({i for i, e in enumerate(evidence) if covers(unit, e, text)})
    return out


def score_question(ranked_units: list[dict], evidence: list[dict], ks: Iterable[int]) -> dict:
    cover = ranked_cover(ranked_units, evidence)
    result: dict = {}
    for k in ks:
        seen = set().union(*cover[:k]) if cover[:k] else set()
        result[f"recall@{k}"] = len(seen) / len(evidence)
        result[f"hit@{k}"] = float(bool(seen))
        first = next((rank for rank, c in enumerate(cover[:k], 1) if c), None)
        result[f"mrr@{k}"] = 1 / first if first else 0.0
    return result


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def aggregate(per_question: dict[str, dict], keys: list[str] | None = None) -> dict:
    keys = keys or sorted({k for v in per_question.values() for k in v})
    return {k: round(mean([v[k] for v in per_question.values() if k in v]), 4) for k in keys}


def bootstrap_ci(values: list[float], n: int = 2000, seed: int = 20261010) -> tuple[float, float]:
    rng = random.Random(seed)
    means = sorted(mean([values[rng.randrange(len(values))] for _ in values]) for _ in range(n))
    return round(means[int(n * 0.025)], 4), round(means[int(n * 0.975) - 1], 4)


def paired_bootstrap(a: dict[str, float], b: dict[str, float], n: int = 2000, seed: int = 20261010) -> dict:
    """Difference b - a over the questions both runs answered, with a 95% bootstrap interval and win/lose counts."""
    qids = sorted(set(a) & set(b))
    diff = [b[q] - a[q] for q in qids]
    low, high = bootstrap_ci(diff, n, seed) if diff else (float("nan"), float("nan"))
    return {"n": len(qids), "mean_diff": round(mean(diff), 4), "ci95": [low, high],
            "b_better": sum(d > 0 for d in diff), "a_better": sum(d < 0 for d in diff), "ties": sum(d == 0 for d in diff)}
