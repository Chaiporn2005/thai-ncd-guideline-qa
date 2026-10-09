"""Turn a reviewer's page-tag export into final decisions by applying the reviewer's stated policy, and log every change.

The reviewer's own choices are kept unless a policy rule below changes them; each change is written to `amendments`
with the rule and the reason, so the result can be checked page by page. The export itself is never modified.

Rules (policy given by the reviewer on 2026-10-08):
  R1  contact_personal pages: tag in place (personal names, personal e-mails, mobile numbers) instead of cutting or
      tagging the whole page, because those pages carry real content and only a contact line is personal.
  R2  patient-case pages: tag the identifying details (age, residence, occupation, home/shop) in place; health
      findings and the nursing process stay. A case page with nothing identifying to tag keeps the reviewer's choice.
  R3  organisation contacts must stay searchable: a phone number or e-mail classified as an organisation's that would
      disappear from search because its only pages were cut gets those pages restored (low-content page kept; list page
      with names tagged in place and kept).
  R4  pages the reviewer did not decide get defaults: worked-example patients kept; personal-like contacts tagged;
      a page that is a list of people cut; names inside a content page tagged unless the document is a leaflet
      (credits stay).

Usage:
    python -X utf8 scripts/amend_page_tag_decisions.py --corpus data/processed/normalized-v7 \
        --decisions data/page_tag_decisions_normalized-v7.json \
        --out data/page_tag_decisions_normalized-v7_final.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_page_tag_review as build  # noqa: E402
import page_context as pc  # noqa: E402

LEAFLET_TYPES = pc.LEAFLET_TYPES


def redact_items(findings: list[dict], flags: list[bool]) -> list[dict]:
    seen, items = set(), []
    for finding, flag in zip(findings, flags):
        key = (finding["type"], finding["field"], finding["value"])
        if flag and key not in seen:
            seen.add(key)
            items.append({"type": finding["type"], "field": finding["field"], "value": finding["value"]})
    return items


def name_redaction(row: dict, entry: dict | None) -> list[dict]:
    """All titled names on the page plus the personal-like contacts the builder flagged."""
    items = redact_items(build.name_findings(row), [True] * 10_000)
    if entry:
        items += [i for i in redact_items(entry["findings"], entry["redact"]) if i["type"] != "name"]
    return items


def org_values(rows: dict[str, dict]) -> dict[tuple[str, str], set[str]]:
    """organisation phone/e-mail value -> pages whose text carries it (searchable pages only)."""
    found: dict[tuple[str, str], set[str]] = {}
    for key, row in rows.items():
        if not build.indexable(row):
            continue
        text = row.get("text") or ""
        for kind, pattern in (("email", pc.EMAIL), ("phone", pc.PHONE)):
            for m in pattern.finditer(text):
                if kind == "phone" and not pc.valid_phone(m.group(0)):
                    continue
                window = text[max(0, m.start() - build.CONTEXT_BEFORE):m.end() + build.CONTEXT_AFTER]
                if pc.classify_contact(kind, m.group(0), window)[0] == "org":
                    found.setdefault((kind, m.group(0)), set()).add(key)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=build.MANIFEST)
    args = parser.parse_args(argv)

    user = json.loads(args.decisions.read_text(encoding="utf-8"))
    doc_types = build.load_doc_types(args.manifest)
    rows: dict[str, dict] = {}
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        for line in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n"):
            if line.strip():
                row = json.loads(line)
                rows[f"{row['document_id']}:p{row['pdf_page']}"] = row
    entries = {}
    for key, row in rows.items():
        if build.indexable(row):
            entry, _ = build.decide_page(row, doc_types.get(row["document_id"], ""))
            if entry:
                entries[key] = entry

    personal = {d["key"]: dict(d) for d in user["personal"]}
    lowcontent = {d["key"]: dict(d) for d in user["lowcontent"]}
    amendments: list[dict] = []

    def change(key, rule, before, after, why):
        amendments.append({"key": key, "rule": rule, "from": before, "to": after, "why": why})

    # R1 / R2 : tag in place
    for key, entry in entries.items():
        decision = personal.get(key)
        if decision is None:
            continue
        if entry["group"] == "contact_personal" and decision["action"] != "redact":
            items = name_redaction(rows[key], entry)
            change(key, "R1", decision["action"], "redact", f"personal contacts/names tagged in place ({len(items)} values)")
            decision.update(action="redact", redact=items)
        elif entry["group"] == "case" and entry["suggest"] == "redact" and decision["action"] != "redact":
            items = redact_items(entry["findings"], entry["redact"])
            change(key, "R2", decision["action"], "redact", f"case identifiers tagged in place ({len(items)} values)")
            decision.update(action="redact", redact=items)

    # R4 : defaults for pages the reviewer did not decide
    for key, entry in entries.items():
        if key in personal:
            continue
        row, doc_type = rows[key], doc_types.get(rows[key]["document_id"], "")
        kinds = {f["type"] for f in entry["findings"]}
        if entry["group"] == "name_list":
            action, items, why = "exclude_page", [], "page is a list of people"
        elif entry["group"] == "contact_personal" or any(entry["redact"]):
            action, items, why = "redact", redact_items(entry["findings"], entry["redact"]), "personal-like contacts tagged"
        elif entry["page_class"] == "name_partial" and doc_type not in LEAFLET_TYPES:
            action, items, why = "redact", name_redaction(row, entry), "names inside a content page tagged"
        else:
            action, items, why = "keep", [], ("worked-example patient" if "case_example" in kinds else
                                              "leaflet credits / organisation contact kept")
        if action == "redact" and not items:
            action, why = "keep", "nothing to tag"
        personal[key] = {"key": key, "action": action, "redact": items}
        change(key, "R4", "undecided", action, why)

    # R3 : organisation contacts must survive somewhere
    def survives(page_key: str) -> bool:
        decision, low = personal.get(page_key), lowcontent.get(page_key)
        if low and low["action"] in ("exclude", "reocr"):
            return False
        return not (decision and decision["action"] in ("exclude_page", "tag_name_list"))

    for (kind, value), pages in sorted(org_values(rows).items()):
        if any(survives(p) for p in pages):
            continue
        for page_key in sorted(pages):
            low, decision = lowcontent.get(page_key), personal.get(page_key)
            if low and low["action"] in ("exclude", "reocr") and low["kind"] != "garbage_text_layer":
                change(page_key, "R3", f"lowcontent:{low['action']}", "lowcontent:keep", f"only searchable copy of an organisation {kind}")
                low["action"] = "keep"
            if decision and decision["action"] in ("exclude_page", "tag_name_list"):
                items = name_redaction(rows[page_key], entries.get(page_key))
                change(page_key, "R3", decision["action"], "redact", f"only searchable copy of an organisation {kind}; names tagged in place")
                decision.update(action="redact", redact=items)

    out = dict(user)
    out.update(personal=list(personal.values()), lowcontent=list(lowcontent.values()),
               personal_undecided=len([k for k in entries if k not in personal]), lowcontent_undecided=0,
               amendments=amendments, amended_by="Claude (AI-suggested policy defaults; reviewer to confirm)")
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "amendments_by_rule": dict(Counter(a["rule"] for a in amendments)),
                      "personal_decisions": len(personal), "undecided": out["personal_undecided"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
