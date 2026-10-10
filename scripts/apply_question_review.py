"""Apply reviewers' exported decisions to the silver questions and write the reviewed question file.

Each export is the JSON a reviewer downloads from a review page. Per question: `accept` -> status gold; `edit` -> gold
with the reviewer's question/answer and the change recorded; `reject` -> status rejected. `reviewed_by` and
`review_date` come from the export. A question with no decision stays silver. Conflicting decisions for one question
(two exports) stop the run: a person must resolve them. The result is checked against `question.schema.json`.

Usage:
    python -X utf8 scripts/apply_question_review.py --questions data/agent_runs/20261010-silver-questions/questions_silver.jsonl \
        --reviews data/questions/reviews/*.json --out data/agent_runs/20261010-silver-questions/questions_reviewed.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply(questions: list[dict], exports: list[dict]) -> tuple[list[dict], dict]:
    decisions: dict[str, dict] = {}
    for export in exports:
        reviewer = (export.get("reviewer") or "").strip()
        if not reviewer:
            raise ValueError(f"export {export.get('part_id')} has no reviewer name")
        date = (export.get("exported_at") or "")[:10]
        for d in export.get("decisions", []):
            if d["qid"] in decisions:
                raise ValueError(f"{d['qid']} was decided in two exports: resolve by hand")
            decisions[d["qid"]] = {**d, "reviewer": reviewer, "date": date}
    known = {q["qid"] for q in questions}
    unknown = sorted(set(decisions) - known)
    if unknown:
        raise ValueError(f"decisions for unknown questions: {unknown[:5]}")

    out = []
    for q in questions:
        d = decisions.get(q["qid"])
        q = dict(q)
        if d:
            if d["decision"] in ("edit", "reject") and not (d.get("note") or "").strip():
                raise ValueError(f"{q['qid']}: {d['decision']} without a note")
            q["reviewed_by"], q["review_date"] = d["reviewer"], d["date"]
            if d["decision"] == "reject":
                q["status"], q["changes"] = "rejected", d["note"].strip()
            else:
                q["status"] = "gold"
                if d["decision"] == "edit":
                    new_q = (d.get("question") or q["question"]).strip()
                    new_a = (d.get("answer") if "answer" in d else q["answer"])
                    new_a = (new_a or "").strip() or None
                    if q["answerable"] and new_a is None:
                        raise ValueError(f"{q['qid']}: an answerable question needs an answer")
                    q["changes"] = f"{d['note'].strip()} [was: {q['question']} => {q['answer']}]"
                    q["question"], q["answer"] = new_q, new_a
        out.append(q)
    # the schema wants no evidence on an unanswerable question; the nearest page the drafter chose goes to a sidecar
    context = [{"qid": q["qid"], "nearest_evidence": q["evidence"]} for q in out if not q["answerable"] and q["evidence"]]
    for q in out:
        if not q["answerable"]:
            q["evidence"] = []
    report = {"unanswerable_context": context, "questions": len(out), "by_status": dict(Counter(q["status"] for q in out)),
              "by_reviewer": dict(Counter(q["reviewed_by"] for q in out if q["reviewed_by"])),
              "gold_by_split": dict(Counter(q["split"] for q in out if q["status"] == "gold")),
              "still_silver": [q["qid"] for q in out if q["status"] == "silver"]}
    return out, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", type=Path, required=True)
    ap.add_argument("--reviews", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    questions = [json.loads(x) for x in args.questions.read_text(encoding="utf-8").split("\n") if x.strip()]
    exports = [json.loads(p.read_text(encoding="utf-8")) for p in args.reviews]
    try:
        out, report = apply(questions, exports)
    except ValueError as err:
        sys.exit(f"stopped: {err}")
    args.out.write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in out), encoding="utf-8", newline="\n")
    context = report.pop("unanswerable_context")
    args.out.with_name(args.out.stem + "_unanswerable_context.jsonl").write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in context), encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False))
    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_rag_jsonl
    return validate_rag_jsonl.main(["question", str(args.out)])


if __name__ == "__main__":
    raise SystemExit(main())
