"""Apply a person's page-tag decisions (population labels, personal-data handling) to build a new corpus version.

Input is the JSON exported from the page built by scripts/build_page_tag_review.py.
  * Every page gets `population`: general (default), pediatric, pregnancy or mixed.
  * `redact`: each ticked value must occur in that page; every occurrence in every stored text field
    (text, text_before_review_edits, removed_edge_lines, ocr_figures) is replaced by a typed placeholder.
  * `exclude_page`: the page keeps its status but gets `index_exclusion` and its stored text is emptied,
    so the personal data is not carried into chunks or indexes (data minimisation).
  * On redacted and excluded pages the raw copies of the text (`pre_normalization_text`, `ocr_text`, `reviewed_from_text`)
    are emptied and their SHA-256 is kept, because a value cannot be replaced reliably in text spelled differently.
  * `tag_name_list`: a page that lists people is tagged `pdpa_tag: personal_name_list` and kept in storage, but gets
    `index_exclusion`, so it is not searched by default.
  * low-content pages: `exclude` marks `index_exclusion`; `reocr` marks a garbled text layer for a new OCR pass
    (`needs_ocr`, status garbled); `keep` is refused for a garbled text layer because it would be indexed as noise.
The decisions file holds the personal data it removes, so keep it in an ignored folder; the manifest written
with --manifest lists only page keys, actions and counts and can be tracked.

Usage:
    python -X utf8 scripts/apply_page_tags.py --source data/processed/normalized-v7 \
        --decisions data/agent_runs/20261008-page-tags/page_tag_decisions_normalized-v7.json \
        --out data/processed/normalized-v8 --manifest data/manifests/page_tags_normalized-v8.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LABELS = {"general", "pediatric", "pregnancy", "elderly", "mixed"}
ACTIONS = {"keep", "redact", "exclude_page", "tag_name_list"}
LOW_CONTENT_ACTIONS = {"keep", "exclude", "reocr"}
PLACEHOLDER = {"name": "[ชื่อบุคคล]", "email": "[อีเมลบุคคล]", "phone": "[เบอร์โทรบุคคล]",
               "citizen_id": "[เลขประจำตัวประชาชน]", "hospital_number": "[เลข HN/AN]",
               "age": "[อายุผู้ป่วย]", "place": "[ที่อยู่ผู้ป่วย]", "occupation": "[อาชีพผู้ป่วย]", "dwelling": "[ที่พักผู้ป่วย]"}
TEXT_FIELDS = ("text", "text_before_review_edits")
LIST_FIELDS = ("removed_edge_lines", "ocr_figures")
# Raw copies of the page text kept for provenance (before normalization, OCR output, the text a reviewer saw). They are
# spelled differently from `text` (spacing, vowel marks), so a value cannot be replaced in them reliably: on pages
# where personal data is redacted or excluded they are emptied and their SHA-256 is kept so the original stays verifiable.
RAW_FIELDS = ("pre_normalization_text", "ocr_text", "reviewed_from_text")


class DecisionError(ValueError):
    pass


def population_map(decisions: dict) -> dict[str, str]:
    labels = {}
    for doc in decisions.get("population", []):
        for start, end, label in doc["ranges"]:
            if label not in LABELS:
                raise DecisionError(f"{doc['document_id']}: unknown population label {label!r}")
            for page in range(int(start), int(end) + 1):
                labels[f"{doc['document_id']}:p{page}"] = label
    return labels


def replace_everywhere(row: dict, old: str, new: str) -> int:
    count = 0
    for field in TEXT_FIELDS:
        if isinstance(row.get(field), str):
            count += row[field].count(old)
            row[field] = row[field].replace(old, new)
    for field in LIST_FIELDS:
        if isinstance(row.get(field), list):
            items = []
            for item in row[field]:
                if isinstance(item, str):
                    count += item.count(old)
                    item = item.replace(old, new)
                items.append(item)
            row[field] = items
    return count


def drop_raw_copies(row: dict) -> list[str]:
    dropped = []
    for field in RAW_FIELDS:
        if isinstance(row.get(field), str) and row[field]:
            row[f"{field}_sha256"] = hashlib.sha256(row[field].encode("utf-8")).hexdigest()
            row[field] = ""
            dropped.append(field)
    return dropped


def apply_personal(row: dict, decision: dict, reviewer: str, date: str) -> dict:
    key = f"{row['document_id']}:p{row['pdf_page']}"
    action = decision["action"]
    if action not in ACTIONS:
        raise DecisionError(f"{key}: unknown action {action!r}")
    record = {"action": action, "decided_by": reviewer, "decided_at": date}
    if action == "redact":
        stored = [row.get(f) or "" for f in TEXT_FIELDS] + [x for f in LIST_FIELDS for x in row.get(f) or []
                                                            if isinstance(x, str)]
        for item in decision["redact"]:
            if item["type"] not in PLACEHOLDER:
                raise DecisionError(f"{key}: {item['type']} cannot be redacted by value; exclude the page instead")
            if not any(item["value"] in s for s in stored):
                raise DecisionError(f"{key}: value to redact not found ({item['type']})")
        counts = Counter()
        # Longest first, so a value that contains a shorter one is replaced whole.
        for item in sorted(decision["redact"], key=lambda x: -len(x["value"])):
            counts[item["type"]] += replace_everywhere(row, item["value"], PLACEHOLDER[item["type"]])
        record["redacted"] = dict(sorted(counts.items()))
        record["raw_copies_dropped"] = drop_raw_copies(row)
    elif action == "tag_name_list":
        row["pdpa_tag"] = "personal_name_list"
        row["index_exclusion"] = {"reason": "pdpa_tagged_name_list", "decided_by": reviewer, "decided_at": date}
    elif action == "exclude_page":
        row["index_exclusion"] = {"reason": "personal_data_minimisation", "decided_by": reviewer, "decided_at": date}
        row["text"] = ""
        row.pop("text_before_review_edits", None)
        record["raw_copies_dropped"] = drop_raw_copies(row)
        for field in LIST_FIELDS:
            if field in row:
                row[field] = []
    row["personal_data"] = record
    return row


def apply_low_content(row: dict, decision: dict, reviewer: str, date: str) -> dict:
    """Mark a page as kept or excluded after review of its low content; text stays so the choice can be audited."""
    action = decision["action"]
    key = f"{row['document_id']}:p{row['pdf_page']}"
    if action not in LOW_CONTENT_ACTIONS:
        raise DecisionError(f"{key}: unknown low-content action {action!r}")
    if action == "keep" and decision.get("kind") == "garbage_text_layer":
        raise DecisionError(f"{key}: a garbled text layer cannot be kept as it is; choose exclude or reocr")
    row["low_content_review"] = {"kind": decision.get("kind"), "action": action, "decided_by": reviewer, "decided_at": date}
    if action in ("exclude", "reocr") and not row.get("index_exclusion"):
        reason = "awaiting_reocr" if action == "reocr" else f"low_content_{decision.get('kind', 'page')}"
        row["index_exclusion"] = {"reason": reason, "decided_by": reviewer, "decided_at": date}
    if action == "reocr":
        row["needs_ocr"] = True
    if decision.get("kind") == "garbage_text_layer" and action in ("exclude", "reocr"):
        row["status"] = "garbled"  # the text layer itself is broken, so consumers that ignore index_exclusion skip it too
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="build even if some flagged pages or documents were not reviewed (they stay as they are)")
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error(f"{args.out} exists; corpus versions are never overwritten")
    data = json.loads(args.decisions.read_text(encoding="utf-8"))
    reviewer = (data.get("reviewer") or "").strip()
    if not reviewer:
        raise DecisionError("decisions have no reviewer")
    pending = {"personal_undecided": data.get("personal_undecided", 0),
               "lowcontent_undecided": data.get("lowcontent_undecided", 0),
               "population_docs_not_reviewed": data.get("population_docs_not_reviewed", [])}
    if (pending["personal_undecided"] or pending["lowcontent_undecided"] or pending["population_docs_not_reviewed"]) \
            and not args.allow_incomplete:
        raise DecisionError(f"review incomplete: {pending['personal_undecided']} personal-data pages, "
                            f"{pending['lowcontent_undecided']} low-content pages and "
                            f"{len(pending['population_docs_not_reviewed'])} documents undecided "
                            "(finish the review or pass --allow-incomplete)")
    labels = population_map(data)
    personal = {d["key"]: d for d in data.get("personal", [])}
    lowcontent = {d["key"]: d for d in data.get("lowcontent", [])}
    date = datetime.now(timezone.utc).date().isoformat()

    seen, plans, page_log = set(), [], []
    totals, actions, population, low_actions = Counter(), Counter(), Counter(), Counter()
    for folder in sorted(p for p in args.source.iterdir() if (p / "pages.jsonl").exists()):
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        for row in rows:
            key = f"{row['document_id']}:p{row['pdf_page']}"
            row["population"] = labels.get(key, "general")
            population[row["population"]] += 1
            if key in personal:
                apply_personal(row, personal[key], reviewer, date)
                seen.add(key)
                actions[row["personal_data"]["action"]] += 1
                page_log.append({"key": key, **{k: v for k, v in row["personal_data"].items() if k != "decided_by"}})
            if key in lowcontent:
                apply_low_content(row, lowcontent[key], reviewer, date)
                seen.add(key)
                low_actions[f"{lowcontent[key].get('kind')}:{lowcontent[key]['action']}"] += 1
        plans.append((folder, rows))
    unknown = (set(personal) | set(labels) | set(lowcontent)) - {f"{r['document_id']}:p{r['pdf_page']}" for _, rows in plans for r in rows}
    if unknown:
        raise DecisionError(f"decisions for pages not in the source: {sorted(unknown)[:5]}")

    for folder, rows in plans:
        out_dir = args.out / folder.name
        out_dir.mkdir(parents=True)
        blob = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
        (out_dir / "pages.jsonl").write_bytes(blob)
        summary = json.loads((folder / "normalization.json").read_text(encoding="utf-8"))
        totals.update(r["status"] for r in rows)
        summary.update(pages_jsonl_sha256=hashlib.sha256(blob).hexdigest(),
                       population_counts=dict(sorted(Counter(r["population"] for r in rows).items())),
                       index_excluded_pages=[r["pdf_page"] for r in rows if r.get("index_exclusion")],
                       derived_from={"corpus_version": folder.parent.name,
                                     "pages_jsonl_sha256": summary["pages_jsonl_sha256"],
                                     "page_tag_decisions": args.decisions.name},
                       created_at=datetime.now(timezone.utc).isoformat())
        (out_dir / "normalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")

    manifest = {"corpus_version": args.out.name, "derived_from": args.source.name, "review_id": data.get("review_id"),
                "reviewer": reviewer, "exported_at": data.get("exported_at"), "built_at": date,
                "population_pages": dict(sorted(population.items())),
                "population_ranges": [d for d in data.get("population", []) if d["ranges"]],
                "personal_data_actions": dict(sorted(actions.items())), "personal_data_pages": page_log,
                "low_content_actions": dict(sorted(low_actions.items())), **pending}
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"documents": len(plans), "population_pages": dict(population), "personal_data": dict(actions), "low_content": dict(low_actions),
                      "status_totals": dict(totals), **pending}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
