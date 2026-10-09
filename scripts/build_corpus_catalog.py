"""Write a categorised list of the documents in a corpus version (CSV for review, Markdown for reading).

Joins the corpus inventory with the canonical manifest and the rights queue, then groups documents by
disease category and document type. Category rule: a document tagged ncd_service or with both diabetes and
hypertension goes to "NCD service / cross-disease"; otherwise its single disease tag decides. Only metadata
is written (no page text), so both outputs can be tracked.

Usage:
    python -X utf8 scripts/build_corpus_catalog.py --corpus data/processed/normalized-v7 \
        --inventory data/manifests/corpus_normalized-v7_inventory.json \
        --csv data/manifests/corpus_normalized-v7_catalog.csv --markdown docs/corpus_catalog.md
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

MANIFEST = Path("data/manifests/documents.jsonl")
RIGHTS = Path("data/manifests/rights_review_20261005.json")
CATEGORIES = {
    "type_2_diabetes": "เบาหวาน (DM)",
    "hypertension": "ความดันโลหิตสูง (HT)",
    "dyslipidemia": "ไขมันในเลือดผิดปกติ (Lipid)",
    "chronic_kidney_disease": "โรคไตเรื้อรัง (CKD, optional)",
    "cross": "ระบบบริการ NCD / ข้ามโรค (DM+HT)",
}
TYPES = {"clinical_guideline": "แนวทางเวชปฏิบัติ", "service_manual": "คู่มือบริการ/บุคลากร",
         "report": "รายงาน/ทบทวน/บทความ", "patient_education": "สื่อความรู้ประชาชน/ผู้ป่วย", "poster": "โปสเตอร์"}
AUDIENCE = {"clinical_guideline": "บุคลากรการแพทย์", "service_manual": "บุคลากรการแพทย์", "report": "บุคลากร/ผู้บริหาร",
            "patient_education": "ประชาชน/ผู้ป่วย", "poster": "ประชาชน/ผู้ป่วย"}
PERMISSION_EVIDENCE_PENDING = "ศูนย์เบาหวานศิริราช"


def category(tags: list[str]) -> str:
    if "ncd_service" in tags or {"type_2_diabetes", "hypertension"} <= set(tags):
        return "cross"
    return tags[0]


def year(record: dict) -> str:
    """Publication year (B.E.); an undated edition only gets the web posting year as a hint."""
    edition = str(record.get("edition") or "")
    undated = re.match(r"ไม่ระบุ|ไม่ยืนยัน|undated", edition, re.I) or "undated" in record["document_id"]
    sources = [record.get("publication_date"), record["document_id"]] + ([] if undated else [edition])
    for value in sources:
        m = re.search(r"25[4-7]\d", str(value or ""))
        if m:
            return m.group(0)
    posted = re.search(r"25[4-7]\d|20[12]\d", edition)
    if not posted:
        return "ไม่ระบุ"
    posted_be = int(posted.group(0)) + (543 if posted.group(0).startswith("20") else 0)
    return f"ไม่ระบุ (เว็บ {posted_be})"


def page_stats(folder: Path) -> dict:
    rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
    def indexable(r):
        review = r.get("human_review") or {}
        return not r.get("index_exclusion") and (r["status"] in ("ok", "ok_minor_issues") or (
            r["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix")))
    idx = [r for r in rows if indexable(r)]
    return {"pages": len(rows), "indexable": len(idx), "ocr": sum(r["text_source"] == "ocr" for r in idx)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)

    manifest = {r["document_id"]: r for r in (json.loads(x) for x in MANIFEST.read_text(encoding="utf-8").split("\n")
                                               if x.strip())}
    rights = {r["document_id"]: r for r in json.loads(RIGHTS.read_text(encoding="utf-8"))["records"]}
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    rows = []
    for item in inventory["records"]:
        doc_id = item["document_id"]
        m = manifest[doc_id]
        stats = page_stats(args.corpus / doc_id)
        notes = []
        if PERMISSION_EVIDENCE_PENDING in m["publisher"]:
            notes.append("รอแนบหลักฐานอนุญาต")
        if stats["indexable"] == 0:
            notes.append("ไม่มีหน้าเข้า index")
        rows.append({"category": category(m["disease_tags"]), "document_type": m["document_type"],
                     "document_id": doc_id, "title": m["title"], "publisher": m["publisher"], "year_be": year(m),
                     "audience": AUDIENCE[m["document_type"]], "disease_tags": " ".join(m["disease_tags"]),
                     "pdf_pages": stats["pages"], "indexable_pages": stats["indexable"], "ocr_pages": stats["ocr"],
                     "rights": rights.get(doc_id, {}).get("rights_review_status", "not_in_queue"),
                     "landing_url": m.get("landing_url") or "", "notes": "; ".join(notes),
                     "review_keep": "", "review_notes": ""})
    order = list(CATEGORIES)
    rows.sort(key=lambda r: (order.index(r["category"]), list(TYPES).index(r["document_type"]), r["document_id"]))

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8-sig", newline="") as f:  # BOM so Excel shows Thai correctly
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    matrix = Counter((r["category"], r["document_type"]) for r in rows)
    lines = [f"# รายการเอกสารใน corpus `{args.corpus.name}` แยกหมวด", "",
             f"สร้างโดย `scripts/build_corpus_catalog.py` จาก inventory + `documents.jsonl` + rights queue · "
             f"{len(rows)} เอกสาร · {sum(r['pdf_pages'] for r in rows):,} หน้า PDF · "
             f"เข้า index {sum(r['indexable_pages'] for r in rows):,} หน้า (OCR {sum(r['ocr_pages'] for r in rows)})", "",
             f"ไฟล์สำหรับตรวจ/จดโน้ต: [`{args.csv.as_posix()}`](../{args.csv.as_posix()}) (คอลัมน์ `review_keep`, `review_notes` ว่างไว้ให้กรอก)", "",
             "กติกาจัดหมวด: เอกสารที่ติดแท็ก `ncd_service` หรือมีทั้งเบาหวานและความดัน → หมวดระบบบริการ/ข้ามโรค; "
             "นอกนั้นใช้แท็กโรคของเอกสาร · กลุ่มผู้อ่านอนุมานจากประเภทเอกสาร", "",
             "## ภาพรวม (หมวดโรค × ประเภทเอกสาร)", "",
             "| หมวด | " + " | ".join(TYPES.values()) + " | รวม | หน้าเข้า index |",
             "| --- | " + " | ".join("---:" for _ in TYPES) + " | ---: | ---: |"]
    for cat in order:
        if cat in by_cat:
            lines.append(f"| {CATEGORIES[cat]} | " + " | ".join(str(matrix[(cat, t)] or "") for t in TYPES)
                         + f" | {len(by_cat[cat])} | {sum(r['indexable_pages'] for r in by_cat[cat]):,} |")
    for cat in order:
        if cat not in by_cat:
            continue
        lines += ["", f"## {CATEGORIES[cat]} — {len(by_cat[cat])} เอกสาร", "",
                  "| ประเภท | เอกสาร | ผู้จัดทำ | ปี พ.ศ. | ผู้อ่าน | หน้า (index/OCR) | หมายเหตุ |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in by_cat[cat]:
            title = f"[{r['title']}]({r['landing_url']})" if r["landing_url"] else r["title"]
            lines.append(f"| {TYPES[r['document_type']]} | {title}<br>`{r['document_id']}` | {r['publisher']} | {r['year_be']} | "
                         f"{r['audience']} | {r['pdf_pages']} ({r['indexable_pages']}/{r['ocr_pages']}) | {r['notes']} |")
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"documents": len(rows), "by_category": {CATEGORIES[c]: len(v) for c, v in by_cat.items()}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
