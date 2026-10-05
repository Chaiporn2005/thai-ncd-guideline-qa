"""Validate research metadata without fetching URLs or approving clinical content."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate(value, schema, location):
    """Check the subset of JSON Schema used in this repository, including formats."""
    errors = []
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        matches = {
            "null": value is None,
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }
        if not any(matches.get(kind, False) for kind in types):
            return [f"{location}: expected {types}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: invalid enum value {value!r}")
    if value is None:
        return errors
    if isinstance(value, str):
        if len(value.strip()) < schema.get("minLength", 0):
            errors.append(f"{location}: empty string")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{location}: invalid pattern")
        if schema.get("format") == "date":
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError:
                errors.append(f"{location}: expected YYYY-MM-DD")
        if schema.get("format") == "uri":
            try:
                parts = urlsplit(value)
                valid_url = parts.scheme in ("https", "http") and bool(parts.netloc)
            except ValueError:
                valid_url = False
            if not valid_url:
                errors.append(f"{location}: expected HTTP(S) URL")
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            errors.append(f"{location}: below minimum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{location}: too few items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            errors.append(f"{location}: duplicate items")
        for index, item in enumerate(value):
            errors += validate(item, schema.get("items", {}), f"{location}[{index}]")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{location}: missing {field}")
        for field, item in value.items():
            if field in properties:
                errors += validate(item, properties[field], f"{location}.{field}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{location}: unexpected field {field}")
    return errors


def inspect(records, schema):
    errors, warnings = [], []
    seen_ids, seen_editions, seen_hashes, seen_urls = {}, {}, {}, {}
    for line, record in records:
        label = f"line {line}"
        record_errors = validate(record, schema, label)
        errors += record_errors
        if record_errors:
            continue
        for field, seen in (("document_id", seen_ids), ("edition_id", seen_editions)):
            key = record[field]
            if key in seen:
                errors.append(f"{label}: duplicate {field} {key!r} (line {seen[key]})")
            seen[key] = line
        digest = record["sha256"]
        if digest:
            if digest in seen_hashes:
                errors.append(f"{label}: duplicate bytes (line {seen_hashes[digest]}); curate one record")
            seen_hashes[digest] = line
        for url in {record["landing_url"], record["download_url"], *record["alternate_urls"]} - {None}:
            if url in seen_urls:
                warnings.append(f"{label}: shared URL with line {seen_urls[url]}; check identity")
            seen_urls[url] = line
        if record["status"] in {"human_approved", "accepted"}:
            review = record["human_review"]
            if not review or review["approved"] is not True:
                errors.append(f"{label}: approval status requires actual human review")
        if record["status"] in {"qa_passed", "human_approved", "accepted"}:
            if record["content_access"] != "full_document" or record["extraction_status"] != "qa_passed":
                errors.append(f"{label}: later stage requires full content and extraction QA")
        if record["status"] == "accepted" and not digest:
            errors.append(f"{label}: accepted record requires actual byte hash")
        if record["status"] == "accepted" and record["thai_context"] == "not_verified":
            errors.append(f"{label}: accepted record requires verified Thai context")
        if record["status"] == "accepted" and record["scope_fit"] == "requires_scope_expansion":
            errors.append(f"{label}: document is outside the currently approved scope")
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=ROOT / "data/manifests/documents.jsonl")
    args = parser.parse_args()
    schema = json.loads((ROOT / "data/schemas/document.schema.json").read_text(encoding="utf-8"))
    records, parse_errors = [], []
    try:
        lines = args.manifest.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"Cannot read manifest: {exc}", file=sys.stderr)
        return 1
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            records.append((number, json.loads(line)))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"line {number}: invalid JSON ({exc.msg})")
    errors, warnings = inspect(records, schema)
    errors = parse_errors + errors
    for item in errors:
        print("ERROR:", item)
    for item in warnings:
        print("WARNING:", item)
    if errors:
        return 1
    documents = [record for _, record in records]
    accepted = [r for r in documents if r["status"] == "accepted"]
    summary = {
        "records": len(documents),
        "candidate_work_ids": len({r["work_id"] for r in documents}),
        "distinct_editions": len({r["edition_id"] for r in documents}),
        "accepted_records": len(accepted),
        "accepted_unique_works": len({r["work_id"] for r in accepted}),
        "status_counts": dict(Counter(r["status"] for r in documents)),
        "metadata_valid": True,
        "clinical_content_verified_by_this_script": False,
        "course_corpus_equivalence_verified": False,
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
