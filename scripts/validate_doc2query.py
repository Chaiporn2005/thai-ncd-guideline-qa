"""Check the doc2query files an agent wrote (mechanical checks only) and merge the accepted ones (Track B).

Per part: one line per input chunk, same order and ids; 2-6 questions per used chunk or none with a reason; each question is Thai
(at least 5 Thai letters and a fifth of its letters; English medical terms are fine), at most 130 characters, free of garbling (`?` runs), page/figure/document references and
contact details; no duplicate question inside a chunk. Problems are listed per chunk, never dropped silently.

Usage:
    python -X utf8 scripts/validate_doc2query.py --run-dir data/agent_runs/20261010-doc2query --parts cal part01 part02
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

THAI = re.compile(r"[฀-๿]")
LETTER = re.compile(r"[฀-๿A-Za-z]")
REFERENCE = re.compile(r"หน้า(?:ที่)?\s*\d|(?<![฀-๿])ภาพที่|(?<![฀-๿])รูปที่|ตารางที่|ตามตาราง|ในเอกสาร|ข้อความข้างต้น|\.pdf", re.I)
PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}\b")


def read(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").split("\n") if x.strip()]


def question_problems(q: str) -> list[str]:
    out = []
    letters = LETTER.findall(q)
    if len(THAI.findall(q)) < 5 or len(THAI.findall(q)) < 0.2 * len(letters):  # English medical terms are wanted; almost no Thai is not
        out.append(f"not mostly Thai: {q[:40]!r}")
    if "??" in q or len(q) > 130 or len(q) < 8:
        out.append(f"garbled or wrong length: {q[:40]!r}")
    if REFERENCE.search(q):
        out.append(f"refers to page/table/document: {q[:40]!r}")
    if PERSONAL.search(q):
        out.append(f"contact detail: {q[:40]!r}")
    return out


def check_part(inputs: list[dict], outputs: list[dict]) -> list[str]:
    problems: list[str] = []
    if [r["chunk_id"] for r in inputs] != [r.get("chunk_id") for r in outputs]:
        return ["output chunk ids differ from the input (missing, extra or reordered)"]
    for row in outputs:
        cid, qs = row["chunk_id"], row.get("questions") or []
        if not qs:
            if not row.get("skipped") or "?" * 4 in row["skipped"]:
                problems.append(f"{cid}: empty without a readable reason")
            continue
        if not 2 <= len(qs) <= 6:
            problems.append(f"{cid}: {len(qs)} questions")
        if len({q.strip() for q in qs}) != len(qs):
            problems.append(f"{cid}: duplicate question")
        for q in qs:
            problems.extend(f"{cid}: {msg}" for msg in question_problems(q))
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--parts", nargs="+", required=True)
    ap.add_argument("--merge-out", type=Path, help="write the questions that pass every per-question check (JSONL: chunk_id, question)")
    args = ap.parse_args(argv)
    report, bad = {}, 0
    for part in args.parts:
        out_file = args.run_dir / "out" / f"{part}.jsonl"
        if not out_file.exists():
            report[part] = {"status": "missing"}
            bad += 1
            continue
        inputs = read(args.run_dir / "parts" / f"{part}.jsonl")
        try:
            outputs = read(out_file)
        except json.JSONDecodeError as err:  # a worker may still be writing the file
            report[part] = {"status": f"not valid JSONL yet: {err}"}
            bad += 1
            continue
        problems = check_part(inputs, outputs)
        bad += bool(problems)
        report[part] = {"chunks": len(inputs), "questions": sum(len(r.get("questions") or []) for r in outputs),
                        "skipped": sum(1 for r in outputs if not r.get("questions")), "problems": problems[:20], "problem_count": len(problems)}
    if args.merge_out:
        kept = dropped = 0
        args.merge_out.parent.mkdir(parents=True, exist_ok=True)
        with args.merge_out.open("w", encoding="utf-8", newline="\n") as f:
            for part in args.parts:
                out_file = args.run_dir / "out" / f"{part}.jsonl"
                if report.get(part, {}).get("status") or "output chunk ids differ" in " ".join(report[part].get("problems", [])):
                    continue  # an unfinished part is never merged
                for row in read(out_file):
                    for q in row.get("questions") or []:
                        if question_problems(q):
                            dropped += 1
                        else:
                            kept += 1
                            f.write(json.dumps({"chunk_id": row["chunk_id"], "question": q.strip()}, ensure_ascii=False) + "\n")
        report["_merge"] = {"kept_questions": kept, "dropped_questions": dropped, "file": str(args.merge_out)}
    (args.run_dir / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: {x: v for x, v in r.items() if x != "problems"} for k, r in report.items()}, ensure_ascii=False))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
