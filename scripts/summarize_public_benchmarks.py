"""One table from the per-task files of scripts/eval_public_benchmarks.py (Track C).

    python -X utf8 scripts/summarize_public_benchmarks.py --run data/index/runs/public_benchmarks/kaggle_new/results \
        --cpu-run data/index/runs/public_benchmarks/run1 --out data/index/runs/public_benchmarks/table.md

Groups: Thai (general and legal) and English medical (domain shift). Columns: nDCG@10 of dense (bge-m3), BM25 (the frozen tokenizer), hybrid (frozen convex fusion), the
hybrid-minus-dense difference with a 95% bootstrap interval, and BM25 minus dense. --cpu-run (float32 on CPU) is compared with --run (float16 on GPU) on the tasks both
have, to show that the GPU did not change the numbers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

NL = chr(10)
THAI = ["NITI", "belebele_tha_thai_tha_thai", "xqu_ad_th", "belebele_eng_latn_tha_thai", "belebele_tha_thai_eng_latn", "mkqa_th", "web_faq_tha", "mr_tidy_thai", "miracl_th",
        "multi_long_doc_th"]
MED = ["scifact", "nfcorpus", "cure_dermatology", "cure_pulmonology"]
LEFT_OUT = ("belebele_eng_latn_tha_thai", "belebele_tha_thai_eng_latn", "mkqa_th")
NAMES = {"NITI": "NitiBench-CCL (Thai law)", "scifact": "SciFact (biomedical claims, EN)", "nfcorpus": "NFCorpus (nutrition/medicine, EN)",
         "cure_dermatology": "CURE dermatology (clinician questions, EN)", "cure_pulmonology": "CURE pulmonology (clinician questions, EN)"}


def load(run: Path, tasks: list[str]) -> list[dict]:
    return [json.loads((run / f"{t}.json").read_text(encoding="utf-8")) for t in tasks if (run / f"{t}.json").exists()]


def fmt_diff(d: dict) -> str:
    return f"{d['mean']:+.3f} [{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]"


def table(rows: list[dict]) -> list[str]:
    head = "| task | docs | queries | dense | BM25 | hybrid | hybrid - dense (95% CI) | BM25 - dense |"
    lines = [head, "|" + "---|" * (head.count("|") - 1)]
    for r in rows:
        lines.append(f"| {NAMES.get(r['task'], r['task'])} | {r['n_docs']} | {r['n_queries']} | {r['dense']['ndcg10']:.3f} | {r['bm25']['ndcg10']:.3f} | "
                     f"**{r['hybrid']['ndcg10']:.3f}** | {fmt_diff(r['hybrid_minus_dense_ndcg10'])} | {r['bm25']['ndcg10'] - r['dense']['ndcg10']:+.3f} |")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--cpu-run", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    thai, med = load(args.run, THAI), load(args.run, MED)
    out = ["# Frozen retrieval stack on public benchmarks (nDCG@10)" + NL, "## Thai" + NL, *table(thai)]
    wins = sum(r["hybrid_minus_dense_ndcg10"]["ci95"][0] > 0 for r in thai)
    losses = sum(r["hybrid_minus_dense_ndcg10"]["ci95"][1] < 0 for r in thai)
    out.append(f"{NL}hybrid beats dense (interval above 0) on {wins} of {len(thai)} Thai tasks and is worse (interval below 0) on {losses}.{NL}")
    out += ["## English medical (domain shift)" + NL, *table(med)]
    wins = sum(r["hybrid_minus_dense_ndcg10"]["ci95"][0] > 0 for r in med)
    losses = sum(r["hybrid_minus_dense_ndcg10"]["ci95"][1] < 0 for r in med)
    out.append(f"{NL}hybrid beats dense on {wins} of {len(med)} English medical tasks and is worse on {losses}. (For English the frozen tokenizer splits Latin text into words "
               f"and uses character 3-grams only for Thai, so this BM25 is ordinary word-level BM25.){NL}")
    xs = [(r["bm25"]["ndcg10"] - r["dense"]["ndcg10"], r["hybrid_minus_dense_ndcg10"]["mean"]) for r in thai + med if r["task"] not in LEFT_OUT]
    if len(xs) > 2:
        mx, my = sum(a for a, _ in xs) / len(xs), sum(b for _, b in xs) / len(xs)
        den = (sum((a - mx) ** 2 for a, _ in xs) * sum((b - my) ** 2 for _, b in xs)) ** 0.5
        r_ = sum((a - mx) * (b - my) for a, b in xs) / den
        out.append(f"Pattern: the hybrid gain shrinks as BM25 falls behind dense (Pearson r = {r_:.2f} between 'BM25 - dense' and 'hybrid - dense' over {len(xs)} tasks; the two "
                   f"cross-lingual sets, where BM25 cannot match across languages, and mkqa, where every method scores near 0, are left out).{NL}")
    if args.cpu_run:
        cpu = {r["task"]: r for r in load(args.cpu_run, THAI)}
        diffs = [(abs(r[k]["ndcg10"] - cpu[r["task"]][k]["ndcg10"]), r["task"], k) for r in thai if r["task"] in cpu for k in ("dense", "bm25", "hybrid")]
        if diffs:
            worst = max(diffs)
            out.append(f"GPU (float16) vs CPU (float32) on {len({d[1] for d in diffs})} Thai tasks: largest nDCG@10 difference {worst[0]:.4f} ({worst[1]}, {worst[2]}).{NL}")
    out.append("Settings: bge-m3 (max length 512, no prefix); BM25 k1 2.18, b 0.86; convex fusion alpha 0.6, pool 100 (configs/retrieval/frozen_v1.json). Nothing tuned on these sets. "
               "Retrieval only: no generation, and not a measure of clinical correctness. Kaggle T4, float16, torch cu128.")
    text = NL.join(out) + NL
    args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
