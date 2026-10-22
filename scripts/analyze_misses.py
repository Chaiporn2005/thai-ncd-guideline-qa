"""Where do the hybrid's misses go? Same disease group or another one (Track B diagnostic for the soft-boost idea).

For every answerable dev question whose Recall@5 is 0 under the chain a finished sweep carried forward, compare the gold document's
primary group with the groups of the top-5 returned parents, and say whether the gold document appears at all in the top 5 / top 30.

Usage:
    python -X utf8 scripts/analyze_misses.py --sweep data/index/sweeps/hybrid-v1-bge-m3 --model bge-m3 --questions ... \
        --parents data/index/chunks-v11-t512 --children data/index/chunks-v11-t128 --index data/index/kaggle/dense-bge-m3-t128
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from sweep_hybrid import Sweep  # noqa: E402
from ncdqa.retrieval import evaluate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sweep", type=Path, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--parents", type=Path, required=True)
    ap.add_argument("--children", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=ROOT / "configs/retrieval/hybrid_sweep_v1.json")
    args = ap.parse_args(argv)
    sw = Sweep(args)
    fused, chain = sw.provisional_hybrid(json.loads((args.sweep / "sweep_results.json").read_text(encoding="utf-8")))
    groups = {r["document_id"]: r["primary_group"] for r in json.loads((ROOT / "data/by_disease/index.json").read_text(encoding="utf-8"))["records"]}
    misses = Counter()
    rows = []
    for q, lst in zip(sw.questions, fused):
        ranked = [u for u, _ in lst]
        sc = evaluate.score_question([sw.units[u] for u in ranked[:5]], q["evidence"], [5])
        if sc["recall@5"] > 0:
            continue
        gold_doc = q["evidence"][0]["document_id"]
        gold_group = groups.get(gold_doc)
        top5_docs = [sw.units[u]["document_id"] for u in ranked[:5]]
        top30_docs = [sw.units[u]["document_id"] for u in ranked[:30]]
        top5_groups = [groups.get(d) for d in top5_docs]
        kind = ("gold document in top 5 (wrong page)" if gold_doc in top5_docs else
                "gold document in top 6-30" if gold_doc in top30_docs else "gold document not in top 30")
        misses[kind] += 1
        misses["top-5 contains the gold group: " + ("yes" if gold_group in top5_groups else "no")] += 1
        misses["share of top-5 in gold group >= 3 of 5" if sum(g == gold_group for g in top5_groups) >= 3 else "share of top-5 in gold group < 3 of 5"] += 1
        rows.append({"qid": q["qid"], "type": q["type"], "gold_group": gold_group, "top5_groups": top5_groups, "kind": kind})
    print(json.dumps({"chain": chain, "misses_at_5": len(rows), "summary": dict(misses)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
