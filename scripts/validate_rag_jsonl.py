"""Validate retrieval (Track B) JSON/JSONL files against data/schemas/rag/.

JSON Schema checks each record; cross-field checks that a schema cannot express
(page order, rank order, chunk_id consistency, unique IDs) run afterwards.

Usage:
    python scripts/validate_rag_jsonl.py chunk path/to/chunks.jsonl
    python scripts/validate_rag_jsonl.py run_manifest path/to/run_manifest.json

Exit codes: 0 valid, 1 invalid records, 2 bad arguments or unreadable input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "data" / "schemas" / "rag"
KINDS = ("page_input", "chunk", "retrieval_result", "run_manifest", "question")
MAX_REPORTED = 50


def load_records(path: Path) -> list[tuple[int, object]]:
    """Return (line_number, record) pairs; a .json file is one record at line 1."""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix == ".json":
        return [(1, json.loads(text))]
    records = []
    # Split on "\n" only: page text can hold U+2028/U+2029 or a form feed, which str.splitlines() would treat as line
    # breaks and cut a JSON record in two. JSONL escapes newlines, so "\n" is the only record separator.
    for number, line in enumerate(text.split("\n"), start=1):
        if line.strip():
            records.append((number, json.loads(line)))
    return records


def cross_field_errors(kind: str, record: dict) -> list[str]:
    errors = []
    if kind == "chunk":
        if record["pdf_page_end"] < record["pdf_page_start"]:
            errors.append("pdf_page_end is before pdf_page_start")
        if record["pdf_page_start"] == record["pdf_page_end"] and record["char_end"] <= record["char_start"]:
            errors.append("char_end must be after char_start within one page")
        prefix = f"{record['document_id']}:p{record['pdf_page_start']:03d}-p{record['pdf_page_end']:03d}:"
        if not record["chunk_id"].startswith(prefix):
            errors.append(f"chunk_id must start with {prefix}")
    elif kind == "retrieval_result":
        ranks = [hit["rank"] for hit in record["hits"]]
        if ranks != list(range(1, len(ranks) + 1)):
            errors.append("hit ranks must be 1..n in order")
        if len(ranks) > record["k"]:
            errors.append("more hits than k")
        chunk_ids = [hit["chunk_id"] for hit in record["hits"]]
        if len(set(chunk_ids)) != len(chunk_ids):
            errors.append("duplicate chunk_id in hits")
        for hit in record["hits"]:
            if hit["pdf_page_end"] < hit["pdf_page_start"]:
                errors.append(f"rank {hit['rank']}: pdf_page_end is before pdf_page_start")
    return errors


def unique_key(kind: str, record: dict) -> tuple | None:
    return {
        "page_input": lambda r: (r["document_id"], r["pdf_page"]),
        "chunk": lambda r: (r["chunk_id"],),
        "retrieval_result": lambda r: (r["run_id"], r["qid"]),
        "question": lambda r: (r["qid"],),
    }.get(kind, lambda r: None)(record)


def validate(kind: str, path: Path) -> list[str]:
    schema = json.loads((SCHEMA_DIR / f"{kind}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    problems: list[str] = []
    seen: dict[tuple, int] = {}
    for line, record in load_records(path):
        schema_errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
        for error in schema_errors:
            location = "/".join(str(p) for p in error.path) or "<record>"
            problems.append(f"line {line}: {location}: {error.message}")
        if schema_errors:
            continue
        problems.extend(f"line {line}: {message}" for message in cross_field_errors(kind, record))
        key = unique_key(kind, record)
        if key is not None:
            if key in seen:
                problems.append(f"line {line}: duplicate key {key} (first at line {seen[key]})")
            else:
                seen[key] = line
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        problems = validate(args.kind, args.path)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "input_error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": not problems, "kind": args.kind, "path": str(args.path),
                      "problem_count": len(problems), "problems": problems[:MAX_REPORTED]},
                     ensure_ascii=False, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
