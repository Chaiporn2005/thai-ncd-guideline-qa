"""Compare two normalizations of the same PDFs page by page, and say how many searchable pages the change would touch.

Built to measure Track A's normalize_thai.py v2 (underlined >=/<= signs, citation superscripts, image-only figure pages)
against the earlier extraction that Track B's corpus versions were built on. Both roots hold <document_id>/pages.jsonl;
`--current` is a Track B version, used only to know which pages are searchable PDF-text pages today.

Usage:
    python -X utf8 scripts/compare_normalization.py --old data/processed/normalized-v2 --new <scratch>/v2prime         --current data/processed/normalized-v11
"""
import argparse
import collections, json, re, sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--old", type=Path, required=True)
parser.add_argument("--new", type=Path, required=True)
parser.add_argument("--current", type=Path, required=True)
args = parser.parse_args()
ours_root, new_root, v11_root = args.old, args.new, args.current


def load(root, doc):
    f = root / doc / "pages.jsonl"
    if not f.exists():
        return {}
    return {json.loads(l)["pdf_page"]: json.loads(l) for l in f.read_text(encoding="utf-8").split("\n") if l.strip()}


def searchable(r):
    hr = r.get("human_review") or {}
    return not r.get("index_exclusion") and (r["status"] in ("ok", "ok_minor_issues") or (r["status"] in ("ocr_unreviewed", "degraded") and hr.get("outcome") in ("pass", "fix")))


SIGNS = "≥≤<>"
def signs(t): return collections.Counter(c for c in t if c in SIGNS)
def nums(t): return collections.Counter(re.findall(r"\d+(?:[.,]\d+)*", t))
def norm(t): return re.sub(r"\s+", " ", t).strip()

stats = collections.Counter()
examples = collections.defaultdict(list)
per_doc = collections.Counter()
for d in sorted(p.name for p in new_root.iterdir() if (p / "pages.jsonl").exists()):
    ours, new, v11 = load(ours_root, d), load(new_root, d), load(v11_root, d)
    for page, n in new.items():
        o = ours.get(page)
        if not o:
            continue
        stats["pages_compared"] += 1
        v = v11.get(page)
        in_search = bool(v and searchable(v) and v.get("text_source") != "ocr")
        stats["compared_and_searchable_pdf_text_pages"] += in_search
        if norm(o["text"]) != norm(n["text"]):
            stats["text_differs"] += 1
            per_doc[d] += 1
            if in_search:
                stats["differs_and_searchable"] += 1
            if signs(o["text"]) != signs(n["text"]):
                stats["sign_differs"] += 1
                if in_search:
                    stats["sign_differs_searchable"] += 1
                if len(examples["sign"]) < 8:
                    examples["sign"].append((d[:30], page, dict(signs(o["text"])), dict(signs(n["text"]))))
            if nums(o["text"]) != nums(n["text"]):
                stats["numbers_differ"] += 1
                if in_search:
                    stats["numbers_differ_searchable"] += 1
        if o["status"] != n["status"]:
            stats["status_changed"] += 1
            stats[f"status {o['status']}->{n['status']}"] += 1
print(dict(stats))
print("docs with most differing pages:", per_doc.most_common(8))
for e in examples["sign"]:
    print("  sign", e)
