"""Apply the three-way review (drafting model, other model, Claude) of the supplementary questions.

Reads `questions_silver.jsonl` of the supplement run and `decisions.json` (Claude's ruling per question: keep / fix / drop
with the reason, informed by the two cross-review files). Writes:
  * `questions_supplement.jsonl`: schema-shaped rows. Status stays silver (a person must make them gold); dropped ones
    become status `rejected` with the reason in `changes`; an edited question keeps the old text in `changes`;
    unanswerable rows have empty evidence as the schema requires.
  * `unanswerable_context.jsonl`: the nearest page and quote of each unanswerable question, for the human reviewer.
Every edited question/answer is re-checked with the same mechanical checks as the drafts (exact quote, lexical leak, ...).

Usage:
    python -X utf8 scripts/finalize_supplement.py --corpus data/processed/normalized-v11 --run-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_silver_questions as v  # noqa: E402


def read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    run = args.run_dir

    questions = {q["qid"]: q for q in read(run / "questions_silver.jsonl")}
    decisions = json.loads((run / "decisions.json").read_text(encoding="utf-8"))
    assert set(decisions) == set(questions), sorted(set(questions) ^ set(decisions))
    texts: dict[tuple[str, int], str] = {}
    for doc in {e["document_id"] for q in questions.values() for e in q["evidence"]}:
        for line in (args.corpus / doc / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                texts[(doc, row["pdf_page"])] = row["text"]

    out, context, problems = [], [], []
    for qid, q in questions.items():
        d = decisions[qid]
        row = {k: q[k] for k in ("qid", "split", "status", "question", "answer", "type", "answerable", "evidence",
                                 "generated_by", "reviewed_by", "review_date", "changes")}
        row["evidence"] = [dict(e) for e in q["evidence"]]
        if d["decision"] == "drop":
            row["status"] = "rejected"
            row["changes"] = f"dropped before human review: {d['reason']}"
        elif d["decision"] == "fix":
            was = f"{q['question']} => {q['answer']}"
            row["question"] = d.get("question", q["question"])
            row["answer"] = d.get("answer", q["answer"])
            row["type"] = d.get("type", q["type"])
            if "evidence" in d:
                row["evidence"] = []
                for e in d["evidence"]:
                    text = texts[(e["document_id"], e["pdf_page"])]
                    quote = e["quote"] if "quote" in e else text[text.index(e["from"]):text.index(e["to"], text.index(e["from"])) + len(e["to"])]
                    row["evidence"].append({"document_id": e["document_id"], "edition_id": q["evidence"][0]["edition_id"],
                                            "pdf_page": e["pdf_page"], "quote": quote})
            row["changes"] = f"{d['reason']} [was: {was}]"
        if d["decision"] != "drop":
            draft = {"question": row["question"], "answer": row["answer"], "type": row["type"],
                     "answerable": row["answerable"],
                     "evidence": [{k: e[k] for k in ("document_id", "pdf_page", "quote")} for e in row["evidence"]]}
            bad = v.check(draft, {"frame": 1}, texts)
            if bad:
                problems.append((qid, bad))
        if not row["answerable"] and row["evidence"]:
            context.append({"qid": qid, "nearest_evidence": row["evidence"]})
            row["evidence"] = []
        out.append(row)

    (run / "questions_supplement.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                                                    encoding="utf-8", newline="\n")
    (run / "unanswerable_context.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in context),
                                                    encoding="utf-8", newline="\n")
    print(json.dumps({"rows": len(out), "by_status": Counter(r["status"] for r in out),
                      "kept_by_type": Counter(r["type"] for r in out if r["status"] != "rejected"),
                      "mechanical_problems": problems}, ensure_ascii=False, default=dict))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
