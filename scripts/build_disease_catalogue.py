"""Build a metadata-only disease folder catalogue from the canonical records."""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/by_disease"
GROUPS = {
    "DM": ("01_diabetes", "เบาหวาน", "แนวทางและคู่มือเกี่ยวกับเบาหวาน"),
    "HT": ("02_hypertension", "ความดันโลหิตสูง", "แนวทางความดันและคู่มือการลดโซเดียม"),
    "LIPID": ("03_dyslipidemia", "ไขมันในเลือดผิดปกติ", "แนวทางไขมัน อาหาร และความเสี่ยงหัวใจและหลอดเลือด"),
    "CKD": ("04_ckd_optional", "โรคไตเรื้อรัง (optional)", "คู่มือโรคไต โภชนาการ และบริการไต; ขอบเขตเสริม"),
    "NCD_SERVICE": ("05_ncd_clinic_plus", "NCD Clinic Plus / ระบบบริการ", "คู่มือและรายงานการพัฒนาคุณภาพบริการ NCD"),
    "EXCLUDED": ("99_excluded", "ไม่นับในชุดเป้าหมาย", "เก็บประวัติรายการที่คัดออก พร้อมเหตุผล; ไม่รวมยอด55"),
}
TYPES = {
    "clinical_guideline": "แนวทางเวชปฏิบัติ",
    "service_manual": "คู่มือบริการ/การดำเนินงาน",
    "patient_education": "เอกสารให้ความรู้ผู้ป่วย/ประชาชน",
    "poster": "โปสเตอร์/สรุปภาพ",
    "report": "รายงาน/ถอดบทเรียน",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def usable_pages(summary: dict) -> str:
    """Pages a retrieval run can use from a normalize_thai.py summary (heuristic gate, not QA)."""
    counts = summary.get("status_counts", {})
    usable = counts.get("ok", 0) + counts.get("ok_minor_issues", 0)
    review = sum(counts.get(k, 0) for k in ("degraded", "garbled", "ocr_unreviewed"))
    return f"ใช้ได้{usable}/{summary.get('pdf_pages')}หน้า;รอตรวจ{review};ว่าง{counts.get('empty', 0)}"


def escape(value) -> str:
    if value is None:
        return "ไม่ทราบ"
    return re.sub(r"([\\`*\[\]<>_|])", r"\\\1", str(value)).replace("\n", " ")


def link(label: str, source: Path, target: Path) -> str:
    relative = Path(os.path.relpath(target, source.parent)).as_posix()
    return f"[{escape(label)}]({relative})"


def generate() -> tuple[dict[Path, str], dict]:
    records = [json.loads(line) for line in (ROOT / "data/manifests/documents.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    cohort = load(ROOT / "data/manifests/corpus_50_candidates.json")
    rights = {r["document_id"]: r for r in load(ROOT / "data/manifests/rights_review_20261005.json")["records"]}
    groups = {key: list(cohort["groups"][key]) for key in GROUPS if key != "EXCLUDED"}
    exclusions = {r["document_id"]: r["reason"] for r in cohort["excluded_from_target"]}
    groups["EXCLUDED"] = list(exclusions)
    lookup = {r["document_id"]: r for r in records}
    ids = [doc_id for values in groups.values() for doc_id in values]
    if len(lookup) != len(records) or Counter(ids) != Counter(lookup.keys()):
        raise ValueError("Each canonical record must occur exactly once in the catalogue")
    outputs = {}
    index = []
    summaries = []
    for group, ids in groups.items():
        folder, title, description = GROUPS[group]
        group_readme = DEST / folder / "README.md"
        table = ["| เอกสาร | ประเภท | บันทึกดาวน์โหลด | ผลสกัด |", "| --- | --- | --- | --- |"]
        downloaded = extracted = 0
        for doc_id in ids:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", doc_id):
                raise ValueError(f"Unsafe ID: {doc_id!r}")
            record = lookup[doc_id]
            doc_readme = DEST / folder / doc_id / "README.md"
            receipt = ROOT / "data/raw" / doc_id / "retrieval.json"
            extraction = ROOT / "data/processed/normalized-v1" / doc_id / "normalization.json"
            # Explicit prior-permission holds: the receipt stays local only and the local PDF was
            # deleted, so the catalogue never links to it and does not count it as downloaded.
            permission_hold = bool(rights.get(doc_id, {}).get("automated_extraction_hold"))
            outcome = load(receipt).get("outcome") if receipt.is_file() and not permission_hold else None
            extraction_status = usable_pages(load(extraction)) if extraction.is_file() else None
            downloaded += outcome == "downloaded"
            extracted += extraction.is_file()
            lines = [f"# {escape(record['title'])}", "", f"หมวด: {title} • {link('สารบัญหมวด', doc_readme, group_readme)}", "", "| รายการ | รายละเอียด |", "| --- | --- |"]
            fields = [("Document ID", doc_id), ("ผู้จัดทำ/หน่วยงาน", record.get("publisher")), ("ฉบับ", record.get("edition")), ("ประเภทเอกสาร", TYPES.get(record.get("document_type"), record.get("document_type"))), ("หัวข้อที่เกี่ยวข้อง", ", ".join(record.get("disease_tags", []))), ("ประชากร/ขอบเขต", record.get("population")), ("สถานะ metadata", record.get("status")), ("สถานะการสกัดใน manifest", record.get("extraction_status")), ("จำนวนหน้า PDF ที่บันทึก", record.get("pdf_pages")), ("สิทธิเผยแพร่ซ้ำ", record.get("redistribution_status")), ("อยู่ในชุด55", "ใช่ — candidate;ยังไม่ใช่ accepted" if group != "EXCLUDED" else "ไม่ใช่")]
            lines += [f"| {label} | {escape(value)} |" for label, value in fields]
            lines += ["", "## แหล่งเอกสาร", ""]
            for label, field in [("หน้าต้นทาง", "landing_url"), ("ช่องทางอ่าน/ดาวน์โหลดที่บันทึก", "download_url")]:
                url = record.get(field)
                if url:
                    if not url.startswith(("https://", "http://")):
                        raise ValueError(f"Unexpected source URL for {doc_id}")
                    url = url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
                    lines.append(f"- [{label}]({url})")
            lines += ["", "## ไฟล์และบันทึกที่เกี่ยวข้อง", "", f"- {link('metadata รายเอกสาร', doc_readme, doc_readme.parent / 'document.json')}", f"- {link('canonical manifest', doc_readme, ROOT / 'data/manifests/documents.jsonl')}"]
            if receipt.is_file() and not permission_hold:
                lines.append(f"- {link('บันทึกดาวน์โหลด', doc_readme, receipt)}: `{outcome}`")
            if extraction.is_file():
                lines.append(f"- {link('สรุปผลสกัด normalized-v1', doc_readme, extraction)}: `{extraction_status}`")
            if permission_hold:
                lines.append("- ต้องขออนุญาตเจ้าของสื่อก่อนใช้:ไม่เผยแพร่บันทึกดาวน์โหลดบนGitHub และลบสำเนาPDFในเครื่องแล้ว(2026-10-06)")
            elif outcome == "downloaded":
                lines.append(f"- บันทึกดาวน์โหลดระบุว่ามีสำเนาในเครื่องที่ `data/raw/{doc_id}/source.pdf`;PDFไม่ได้อยู่บนGitHub")
            elif group != "EXCLUDED":
                lines.append("- ยังไม่มี PDF ในรอบเตรียมล่าสุด;ลิงก์ต้นทางไม่ยืนยันว่าดาวน์โหลดได้")
            if doc_id in exclusions:
                lines += ["", f"**เหตุผลที่ไม่นับ:** {escape(exclusions[doc_id])}"]
            if permission_hold:
                lines += ["", "**พักการสกัดอัตโนมัติ:**มีข้อกำหนดให้ขออนุญาตเจ้าของสื่อก่อน"]
            lines += ["", "การจัดหมวดไม่ใช่การอนุมัติสิทธิ/ความถูกต้องทางคลินิกหรือการรับเข้า corpus", "ไฟล์นี้สร้างจาก metadata;แก้ข้อมูลต้นทางแล้วรัน `python scripts/build_disease_catalogue.py` ใหม่", ""]
            outputs[doc_readme] = "\n".join(lines)
            item = {"document_id": doc_id, "primary_group": group, "selected_candidate": group != "EXCLUDED", "exclusion_reason": exclusions.get(doc_id), "folder": doc_readme.parent.relative_to(ROOT).as_posix()}
            payload = {**item, "canonical_source": "data/manifests/documents.jsonl", "canonical_document": record}
            outputs[doc_readme.parent / "document.json"] = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
            index.append(item)
            table.append(f"| {link(record['title'], group_readme, doc_readme)} | {escape(TYPES.get(record.get('document_type'), record.get('document_type')))} | {'รอขออนุญาต' if permission_hold else escape(outcome) if outcome else 'ไม่มีบันทึก'} | {escape(extraction_status) if extraction_status else 'ไม่มีผลสกัด'} |")
        outputs[group_readme] = f"# {title}\n\n{description}\n\nรายการ{len(ids)};บันทึกดาวน์โหลดสำเร็จ{downloaded};มีผลสกัด{extracted}\nสถานะเหล่านี้มาจากบันทึกเดิม ไม่ใช่ผลตรวจคลินิกหรือการยืนยันว่ามีPDFหลังclone\n\n" + "\n".join(table) + f"\n\n{link('กลับสารบัญทั้งหมด', group_readme, DEST / 'README.md')}\n"
        summaries.append(f"| {link(title, DEST / 'README.md', group_readme)} | {len(ids)} | {downloaded} | {extracted} |")
    outputs[DEST / "README.md"] = "# เอกสารแยกตามโรคและระบบบริการ\n\nเปิดโฟลเดอร์หมวด แล้วเลือกโฟลเดอร์เอกสารเพื่อดูชื่อ/ผู้จัดทำ/ฉบับ/ประเภท/ลิงก์ต้นทางและบันทึกที่เกี่ยวข้อง\n55 selected candidates แบ่งหมวดหลักหนึ่งหมวดต่อเอกสาร;อีก3รายการเก็บใน99_excluded\nเอกสารข้ามโรคมี disease_tags ใน metadata และไม่นับซ้ำ\n\n| หมวด | รายการ | ดาวน์โหลดสำเร็จในบันทึก | มีผลสกัด |\n| --- | --- | --- | --- |\n" + "\n".join(summaries) + "\n\nแต่ละโฟลเดอร์มี README.md และ document.json;เป็นสารบัญ/metadata ไม่ใช่ไฟล์PDFหรือข้อความเต็ม\nraw/processed เก็บบันทึกตาม document_id เพื่อใช้กับ download/extraction pipeline\naccepted0;สิทธิ/QA/human reviewยังค้าง;CKDเป็นoptional\n\nสร้าง/อัปเดต: `python scripts/build_disease_catalogue.py`\nตรวจความตรงกับต้นทาง: `python scripts/build_disease_catalogue.py --check`\nข้อมูลหลักอยู่ที่ [canonical manifest](../manifests/documents.jsonl) และ [ชุดที่เลือก](../manifests/corpus_50_candidates.json)\n[Folder index สำหรับโปรแกรม](index.json)\n"
    outputs[DEST / "index.json"] = json.dumps({"canonical_manifest": "data/manifests/documents.jsonl", "selected_cohort": "data/manifests/corpus_50_candidates.json", "counts": {key: len(value) for key, value in groups.items()}, "records": index}, ensure_ascii=False, indent=2) + "\n"
    return outputs, {"canonical_records": len(records), "selected_candidates": len(index) - len(exclusions), "excluded": len(exclusions), "generated_files": len(outputs)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only consistency check")
    args = parser.parse_args()
    outputs, report = generate()
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, text in outputs.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
        extra = [str(p.relative_to(ROOT)) for p in DEST.rglob("*") if p.is_file() and p not in outputs] if DEST.exists() else []
        print(json.dumps({**report, "ok": not stale and not extra, "stale": stale, "unexpected": extra}))
        return int(bool(stale or extra))
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({**report, "written": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
