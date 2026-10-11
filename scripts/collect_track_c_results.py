"""Copy the small aggregate result files of Track C (answer step) into runs/frozen_gen_v1/ so they can go to git (plan E-10).

    python -X utf8 scripts/collect_track_c_results.py

Copies only files that hold numbers and settings, never question or answer text: metrics.json, manifest.json, results.json/md of the guardrail runs, the BERTScore
selection files, the judge checks and the dev-vs-test table. `per_question.csv`, `answers.jsonl` and `rows.jsonl` hold question text and chunk text (some from
documents that must not be published, Decision 0008) and stay in data/index/runs/ on the machine that produced them.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/index/runs"
DEST = ROOT / "runs/frozen_gen_v1"

FILES = {
    "generation/{name}_manifest.json": [f"gen/{n}/manifest.json" for n in ("dev-A", "dev-B", "dev-C", "dev-A-p3", "dev-B-p3", "dev-C-p3", "test-A", "test-B", "test-C", "dev-B-graph", "recover-plain", "recover-graph")],
    "eval/{name}_metrics.json": [f"eval/{n}/metrics.json" for n in ("test_luna_N7", "dev_p2_N7", "dev_p3_N7", "dev_luna_N2", "dev_luna_N7", "dev_codex-luna", "dev_agy-claude", "recover_luna")],
    "eval/{name}_manifest.json": [f"eval/{n}/manifest.json" for n in ("test_luna_N7", "dev_p2_N7", "dev_p3_N7", "recover_luna")],
    "eval/{name}": ["eval/bertscore_variants.json", "eval/bert_selection_dev.json", "eval/judge_sanity.json", "eval/judge_bias.json", "eval/dev_judge_agreement.json", "eval/dev_vs_test.md"],
    "guardrail/{name}_results.json": [f"guard/{n}/results.json" for n in ("g2", "g4_adaptive_v2", "g5_adaptive_n7", "g6_main_n7")],
    "guardrail/{name}": ["guard/input_guard_silver.json"],
    "guardrail/{name}_manifest.json": [f"guard/{n}/manifest.json" for n in ("g2", "g4_adaptive_v2", "g5_adaptive_n7", "g6_main_n7")],
}


def main() -> int:
    copied, missing = [], []
    for pattern, sources in FILES.items():
        for rel in sources:
            src = RUNS / rel
            if not src.exists():
                missing.append(rel)
                continue
            parts = Path(rel).parts
            name = parts[1] if len(parts) == 3 else Path(rel).name
            dst = DEST / pattern.format(name=name)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied.append(str(dst.relative_to(ROOT)))
    print(f"copied {len(copied)} files to {DEST.relative_to(ROOT)}")
    if missing:
        print("not found (run the step that creates them):", ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
