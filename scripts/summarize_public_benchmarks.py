"""One table from the per-task files of scripts/eval_public_benchmarks.py (Track C).

    python -X utf8 scripts/summarize_public_benchmarks.py --run data/index/runs/public_benchmarks/run1 --out data/index/runs/public_benchmarks/run1_table.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ORDER = ["NITI", "belebele_tha_thai_tha_thai", "xqu_ad_th", "belebele_eng_latn_tha_thai", "belebele_tha_thai_eng_latn", "mkqa_th", "web_faq_tha", "mr_tidy_thai", "miracl_th",
         "multi_long_doc_th"]
NAMES = {"NITI": "NitiBench-CCL (กฎหมายไทย)"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rows = [json.loads((args.run / f"{t}.json").read_text(encoding="utf-8")) for t in ORDER if (args.run / f"{t}.json").exists()]
    pending = [t for t in ORDER if not (args.run / f"{t}.json").exists()]
    lines = ["| task | docs | queries | dense | BM25 | hybrid | hybrid − dense (95% CI) | recall@100 dense / hybrid |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        d = r["hybrid_minus_dense_ndcg10"]
        lines.append(f"| {NAMES.get(r['task'], r['task'])} | {r['n_docs']} | {r['n_queries']} | {r['dense']['ndcg10']:.3f} | {r['bm25']['ndcg10']:.3f} | **{r['hybrid']['ndcg10']:.3f}** | "
                     f"{d['mean']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}] | {r['dense']['recall100']:.3f} / {r['hybrid']['recall100']:.3f} |")
    wins = sum(r["hybrid_minus_dense_ndcg10"]["ci95"][0] > 0 for r in rows)
    lines.append(f"\nnDCG@10 (binary relevance); frozen settings of Track B, nothing tuned on these sets. hybrid beats dense with an interval above 0 on {wins} of {len(rows)} tasks.")
    if pending:
        lines.append("Not finished: " + ", ".join(pending))
    text = "\n".join(lines) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
