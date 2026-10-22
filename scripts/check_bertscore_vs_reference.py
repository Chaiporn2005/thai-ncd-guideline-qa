"""Check our BERTScore (src/ncdqa/eval/bertscore.py) against the reference `bert_score` package on the same pairs (Track C, 2026-10-14).

    pip/uv install bert-score   (not a project requirement: only this check uses it)
    python -X utf8 scripts/check_bertscore_vs_reference.py --eval data/index/runs/eval/test_luna_N7 --variant B --n 24 --out data/index/runs/eval/bertscore_reference_check.json

Same pairs, same model (BAAI/bge-m3), same layer (8), same idf sentences. Prints our F1 and the package's F1 per setting and the largest difference. The main guard is needed: the package
starts worker processes for idf on Windows, which re-import this file.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--eval", type=Path, required=True, help="eval folder with per_question.csv")
    ap.add_argument("--variant", default="B")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--layer", type=int, default=8)
    ap.add_argument("--compat", action="store_true", help="score with our reference-compatible mode (special tokens kept as match targets with weight 0)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    import bert_score

    from ncdqa.eval.bertscore import BertScorer
    rows = [r for r in csv.DictReader(open(args.eval / "per_question.csv", encoding="utf-8-sig")) if r["variant"] == args.variant and r["answer"].strip() and r["gold_answer"].strip()][:args.n]
    cands, refs = [r["answer"] for r in rows], [r["gold_answer"] for r in rows]
    out = {"pairs": len(rows), "layer": args.layer, "compat": args.compat, "settings": {}}
    for idf in (False, True):
        kw = {"reference_compat": True} if args.compat else {}
        ours = BertScorer("BAAI/bge-m3", args.layer, refs if idf else None, **kw)
        mine = [ours.score(c, r)["f1"] for c, r in zip(cands, refs)]
        sc = bert_score.BERTScorer(model_type="BAAI/bge-m3", num_layers=args.layer, idf=idf, idf_sents=refs if idf else None, batch_size=8, device="cpu", rescale_with_baseline=False, nthreads=1)
        _, _, f = sc.score(cands, refs)
        ref = [float(x) for x in f]
        d = [abs(a - b) for a, b in zip(mine, ref)]
        out["settings"]["idf" if idf else "no_idf"] = {"ours_mean": round(st.mean(mine), 4), "reference_mean": round(st.mean(ref), 4), "max_abs_diff": round(max(d), 5), "mean_abs_diff": round(st.mean(d), 5)}
        print(f'idf={idf}: ours {st.mean(mine):.4f} | reference {st.mean(ref):.4f} | max |diff| {max(d):.5f} | mean |diff| {st.mean(d):.5f}', flush=True)
    if args.out:
        args.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
