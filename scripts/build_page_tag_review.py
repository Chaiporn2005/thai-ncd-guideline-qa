"""Build a local HTML page for a person to tag page populations and decide personal-data (PDPA) handling.

Reads every indexable page of a corpus version and uses page context (scripts/page_context.py), not bare keywords:
  * population: a page is tagged child / pregnancy / elderly only when it is about that population (subject,
    density of specific terms, chapter title); passing mentions, cautions in adult content, reference lists and
    organisation names do not count; pages mixing adult and specific content are "mixed";
  * people: a page that is mostly a list of people (committee, reviewers) is separated for a decision; a few names
    crediting a leaflet or infographic, and names inside content, are kept without asking;
  * contacts: phone numbers and e-mail addresses are classified as organisation (kept), personal (suggested for
    removal) or ambiguous (shown with context); Thai citizen IDs (checksum-valid) and HN/AN numbers are personal;
  * pages with little content or a garbled text layer, and patient-case narratives, are grouped with sample images.
Suggestions are only defaults; the person decides and exports a JSON for scripts/apply_page_tags.py.
The page embeds matched personal data, so write it only to an ignored folder. Nothing is uploaded.

Usage:
    python -X utf8 scripts/build_page_tag_review.py --corpus data/processed/normalized-v7 \
        --raw data/raw --out data/agent_runs/20261008-page-tags
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_context as pc  # noqa: E402

MANIFEST = Path("data/manifests/documents.jsonl")

# Case narratives: a real (even unnamed) person's age, place, family and results together can identify them.
CASE_NARRATIVE = re.compile(r"กรณีศึกษา")
CASE_EXAMPLE = re.compile(r"ผู้ป่วย(?:ชาย|หญิง)\s*อายุ\s*\d+\s*ปี")
CASE_MIN_MENTIONS = 3

# Quasi-identifiers in a patient-case narrative: age, residence, occupation and home/shop. Health findings stay.
CASE_IDENTIFIERS = {
    "age": re.compile(r"อายุ\s*\d{1,3}\s*ปี"),
    "place": re.compile(r"(?:ชุมชน)?เขตพื้นที่รับผิดชอบ\s*โรงพยาบาล[ก-๙]+(?:\s*จังหวัด[ก-๙]+)?|จังหวัด[ก-๙]+"),
    "occupation": re.compile(r"อาชีพ(?!นอก)[ก-๙]{3,}"),
    "dwelling": re.compile(r"ร้านขายของชำ"),
}
CITIZEN_ID = re.compile(r"(?<![\d-])\d[- ]?\d{4}[- ]?\d{5}[- ]?\d{2}[- ]?\d(?![\d-])")
HOSPITAL_NUMBER = re.compile(r"\b(?:HN|AN)\s*[:.]?\s*\d{4,}")
CONTEXT_BEFORE, CONTEXT_AFTER = 200, 120  # window used to classify a contact

# Pages that would only add noise (or nothing) as standalone retrieval units.
NAV_TOKENS = re.compile(r"Previous Page|Next Page|Previous Chapter|Next Chapter|Contents|HOME|กลับหน้าสารบัญ|บันทึก", re.I)
GLYPH_RUN = re.compile(r"(?:/g\s?\d+){3,}")  # font glyph ids left by a broken text layer, e.g. /g94/g67/g92
DIVIDER = re.compile(r"^\s*(?:บทที่|หมวด|ภาคผนวก|ตอนที่|ส่วนที่|Chapter|Part)", re.I)
CAPTION = re.compile(r"^\s*(?:รูปที่|ตารางที่|แผนภูมิที่|แผนภาพที่|ภาพที่|Figure|Fig\.|Table)", re.I)
NAV_ONLY_SIGNAL, EMPTY_SIGNAL, DIVIDER_SIGNAL, EDGE_SIGNAL, SHORT_SIGNAL = 15, 30, 80, 150, 100
EDGE_PAGES = 3  # cover zone: the first pages; the same count is checked from the end
GLYPH_SHARE = 0.3


def thai_id_valid(digits: str) -> bool:
    if len(digits) != 13 or digits.startswith(("978", "979")):  # ISBN-13 prefixes
        return False
    total = sum(int(d) * (13 - i) for i, d in enumerate(digits[:12]))
    return (11 - total % 11) % 10 == int(digits[12])


def indexable(row: dict) -> bool:
    review = row.get("human_review") or {}
    return not row.get("index_exclusion") and (row["status"] in ("ok", "ok_minor_issues") or (
        row["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix")))


def page_strings(row: dict):
    """Every stored string of a page that can hold document text."""
    yield "text", row.get("text") or ""
    if row.get("text_before_review_edits"):
        yield "text_before_review_edits", row["text_before_review_edits"]
    for field in ("removed_edge_lines", "ocr_figures"):
        for value in row.get(field) or []:
            if isinstance(value, str):
                yield field, value


def context(text: str, start: int, end: int, width: int = 60) -> list[str]:
    return [text[max(0, start - width):start], text[start:end], text[end:end + width]]


def personal_findings(row: dict, name_class: str = "none") -> list[dict]:
    """Personal data on a page. Names are listed only on pages that list people (so they can be redacted);
    contacts carry their organisation/personal/ambiguous class and the reason."""
    found = []
    for field, text in page_strings(row):
        if name_class in ("name_list", "name_partial"):
            for m in pc.NAME.finditer(text):
                found.append({"type": "name", "field": field, "value": m.group(0), "context": context(text, *m.span())})
        for kind, pattern in (("email", pc.EMAIL), ("phone", pc.PHONE)):
            for m in pattern.finditer(text):
                if kind == "phone" and not pc.valid_phone(m.group(0)):
                    continue
                window = text[max(0, m.start() - CONTEXT_BEFORE):m.end() + CONTEXT_AFTER]
                klass, why = pc.classify_contact(kind, m.group(0), window)
                found.append({"type": kind, "field": field, "value": m.group(0), "context": context(text, *m.span()),
                              "contact": klass, "why": why})
        for m in CITIZEN_ID.finditer(text):
            if thai_id_valid(re.sub(r"\D", "", m.group(0))):
                found.append({"type": "citizen_id", "field": field, "value": m.group(0), "context": context(text, *m.span())})
        for m in HOSPITAL_NUMBER.finditer(text):
            found.append({"type": "hospital_number", "field": field, "value": m.group(0), "context": context(text, *m.span())})
    found.extend(case_findings(row.get("text") or ""))
    if any(f["type"] == "case" for f in found):
        found.extend(case_identifier_findings(row.get("text") or ""))
    return found


def case_identifier_findings(text: str) -> list[dict]:
    found, seen = [], set()
    for kind, pattern in CASE_IDENTIFIERS.items():
        for m in pattern.finditer(text):
            if (kind, m.group(0)) not in seen:
                seen.add((kind, m.group(0)))
                found.append({"type": kind, "field": "text", "value": m.group(0), "context": context(text, *m.span())})
    return found


def name_findings(row: dict) -> list[dict]:
    found = []
    for field, text in page_strings(row):
        for m in pc.NAME.finditer(text):
            found.append({"type": "name", "field": field, "value": m.group(0), "context": context(text, *m.span())})
    return found


def case_findings(text: str) -> list[dict]:
    found = []
    mentions = list(CASE_NARRATIVE.finditer(text))
    if len(mentions) >= CASE_MIN_MENTIONS and "สารบัญ" not in text[:200]:
        found.append({"type": "case", "field": "text", "value": f"กรณีศึกษา ×{len(mentions)}",
                      "context": context(text, *mentions[0].span())})
    elif m := CASE_EXAMPLE.search(text):
        found.append({"type": "case_example", "field": "text", "value": m.group(0), "context": context(text, *m.span())})
    return found


def personal_like(finding: dict) -> bool:
    """A contact that belongs to a person: classified personal, or a free-mail address / mobile number with no
    organisation clue (kept conservative: such a value is tagged unless the reviewer says it is an office's)."""
    if finding["type"] not in ("email", "phone"):
        return False
    if finding.get("contact") == "personal":
        return True
    digits = re.sub(r"\D", "", finding["value"])
    return finding.get("contact") == "ambiguous" and (bool(pc.FREE_MAIL.search(finding["value"])) or bool(pc.MOBILE.match(digits)))


def redact_default(finding: dict) -> bool:
    if finding["type"] in ("citizen_id", "hospital_number", "age", "place", "occupation", "dwelling"):
        return True
    return personal_like(finding)


def decide_page(row: dict, doc_type: str) -> tuple[dict | None, str]:
    """(entry needing a decision or None, name class of the page).

    Pages needing no decision are kept: names crediting a leaflet, a few names inside content, organisation contacts.
    """
    text = row.get("text") or ""
    name_class, name_reasons, _ = pc.name_page_class(text, doc_type)
    findings = personal_findings(row, name_class)
    if not findings:
        return None, name_class
    kinds = {f["type"] for f in findings}
    personal = [f for f in findings if redact_default(f) and f["type"] not in ("age", "place", "occupation", "dwelling")]
    ambiguous = [f for f in findings if f["type"] in ("email", "phone") and f.get("contact") == "ambiguous"
                 and not personal_like(f)]
    focus = None
    if "case" in kinds:
        group = "case"
        tagged = [f for f in findings if f["type"] in ("age", "place", "occupation", "dwelling")]
        suggest = "redact" if tagged else "exclude_page"
        reason = ("บรรยายเคสผู้ป่วย: แทนข้อมูลระบุตัว (อายุ/ที่อยู่/อาชีพ/ที่พัก) ด้วยแท็ก เก็บข้อมูลทางคลินิกไว้"
                  if tagged else "บรรยายเคสผู้ป่วยแต่ไม่พบข้อมูลระบุตัวที่ตรวจได้ — ถ้าเป็นเคสจริงควรตัดออก")
        focus = (tagged or [next(f for f in findings if f["type"] == "case")])[0]
    elif name_class == "name_list":
        group, suggest = "name_list", "exclude_page"
        reason = "ทั้งหน้าเป็นรายชื่อบุคคล: " + "; ".join(name_reasons)
    elif personal:
        group, suggest = "contact_personal", "redact"
        reason = "ข้อมูลติดต่อ/เลขประจำตัวที่เป็นของบุคคล: " + "; ".join(sorted({f.get("why") or f["type"] for f in personal}))
        focus = personal[0]
        findings = findings + name_findings(row)  # names beside the personal contacts are tagged as well
    elif name_class == "name_partial" or ambiguous or "case_example" in kinds:
        group, suggest = "review", "keep"
        parts = []
        if name_class == "name_partial":
            parts.append("รายชื่อปนอยู่กับเนื้อหาอื่น: " + "; ".join(name_reasons))
        if ambiguous:
            parts.append("ข้อมูลติดต่อที่ยังไม่ชัดว่าเป็นของใคร")
        if "case_example" in kinds:
            parts.append("ตัวอย่างผู้ป่วย (น่าจะสมมติ) — ตรวจว่าไม่ใช่เคสจริง")
        reason = "; ".join(parts)
        focus = (ambiguous or findings)[0]
    else:
        return None, name_class
    preview = " ".join(text.split())[:300]
    if focus:
        before, value, after = focus["context"]
        preview = " ".join((before + "【" + value + "】" + after).split())
    return ({"key": f"{row['document_id']}:p{row['pdf_page']}", "document_id": row["document_id"], "p": row["pdf_page"],
             "page_class": name_class, "group": group, "suggest": suggest, "reason": reason,
             "redact": [redact_default(f) for f in findings], "findings": findings, "preview": preview}, name_class)


def signal(text: str) -> int:
    """Count of letters and digits: the amount of content a page carries, ignoring spacing and punctuation."""
    return len(re.findall(r"[ก-๙A-Za-z0-9]", text))


def low_content(row: dict, last_page: int) -> dict | None:
    """Classify a page that is garbled or carries little content; None for a normal page."""
    text = row.get("text") or ""
    glyph_chars = sum(len(m) for m in GLYPH_RUN.findall(text))
    if glyph_chars >= 40 and glyph_chars >= GLYPH_SHARE * len(text):
        return {"kind": "garbage_text_layer", "suggest": "exclude", "signal": signal(text)}
    sig = signal(NAV_TOKENS.sub("", text))
    page = row["pdf_page"]
    if sig < NAV_ONLY_SIGNAL:
        kind, suggest = "nav_only", "exclude"
    elif sig < DIVIDER_SIGNAL and DIVIDER.match(text):
        kind, suggest = "divider", "exclude"
    elif sig < EDGE_SIGNAL and CAPTION.match(text):
        kind, suggest = "figure_caption", "keep"  # the figure or table itself carries the content
    elif sig < EMPTY_SIGNAL:
        kind, suggest = "almost_empty", "exclude"
    elif sig < EDGE_SIGNAL and page <= EDGE_PAGES:
        kind, suggest = "cover", "exclude"
    elif sig < EDGE_SIGNAL and page > last_page - EDGE_PAGES:
        kind, suggest = "back", "exclude"
    elif sig < SHORT_SIGNAL:
        kind, suggest = "short", "keep"
    else:
        return None
    return {"kind": kind, "suggest": suggest, "signal": sig}


def population_evidence(text: str, label: str) -> list[list[str]]:
    cleaned = pc.ORG_PHRASE.sub(" ", text)
    pattern = pc.POPULATION_STRONG.get(label)
    if not pattern:
        return []
    return [context(cleaned, *m.span(), 50) for m in list(pattern.finditer(cleaned))[:2]]


def scan_document(rows: list[dict], doc_type: str = "") -> tuple[list[dict], list[dict], list[dict]]:
    pages, personal, lowcontent = [], [], []
    last_page = max(r["pdf_page"] for r in rows)
    population = pc.population_for_document([r for r in rows])
    for row in rows:
        text = row.get("text") or ""
        pop = population[row["pdf_page"]]
        ok = indexable(row)
        mention = {label: s["hits"] for label, s in pop["scores"].items()} if ok and not pop["label"] else {}
        evidence = population_evidence(text, pop["label"]) if ok and pop["label"] and pop["label"] != "mixed" else []
        entry = {"p": row["pdf_page"], "indexable": ok, "chapter": pop["section"],
                 "suggest": pop["label"] if ok else None, "confidence": pop["confidence"] if ok else None,
                 "reasons": pop["reasons"] if ok else [], "evidence": evidence, "mention": mention,
                 "first": " ".join(text.split())[:110]}
        if ok:
            flagged = low_content(row, last_page)
            if flagged:
                lowcontent.append({"key": f"{row['document_id']}:p{row['pdf_page']}", "document_id": row["document_id"],
                                   "p": row["pdf_page"], "text": text[:500], **flagged})
            decision, name_class = decide_page(row, doc_type)
            entry["name_class"] = name_class
            if decision:
                personal.append(decision)
        pages.append(entry)
    return pages, personal, lowcontent


LOW_GROUPS = {
    "garbage_text_layer": ("ข้อความเสีย (รหัสฟอนต์แทนตัวอักษร)", "ข้อความในไฟล์เป็นรหัส /g94/g67… ถ้าเข้า index จะถูก embed เป็นขยะ",
                           [("exclude", "ตัดทั้งกลุ่ม"), ("reocr", "ส่ง OCR ใหม่ (ไม่เข้า index จนกว่าจะตรวจ)"), ("keep", "เก็บทั้งกลุ่ม (ไม่แนะนำ)")]),
    "nav_only": ("ปุ่มนำทางอย่างเดียว", "มีแต่คำอย่าง Contents / Next Page / กลับหน้าสารบัญ ไม่มีเนื้อหา", None),
    "almost_empty": ("แทบไม่มีข้อความ", "น้อยกว่า 30 ตัวอักษร", None),
    "divider": ("หน้าคั่นบท/ภาคผนวก", "มีแค่หัวข้อบทหรือภาคผนวก", None),
    "cover": ("ปก/หน้าชื่อเรื่อง", "หน้าต้นเล่มที่ข้อความน้อย ชื่อเอกสารมีใน metadata อยู่แล้ว", None),
    "back": ("ปกหลัง/ท้ายเล่ม", "หน้าท้ายเล่มที่ข้อความน้อย เช่น ข้อมูลติดต่อหน่วยงาน", None),
}
DEFAULT_LOW_ACTIONS = [("exclude", "ตัดทั้งกลุ่ม"), ("keep", "เก็บทั้งกลุ่ม")]
SAMPLES_PER_GROUP = 6
SAMPLE_DPI = 70


def spread(items: list[dict], n: int) -> list[dict]:
    """Pick n items evenly across the list ordered by document and page, so samples cover different documents."""
    items = sorted(items, key=lambda i: (i["document_id"], i["p"]))
    if len(items) <= n:
        return items
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]


def render_page(pdf: Path, page: int, out: Path) -> bool:
    """Render one PDF page to PNG with pdftoppm; False when it is unavailable or fails (the page still works without images)."""
    if not shutil.which("pdftoppm"):
        return False
    stem = out.with_suffix("")
    result = subprocess.run(["pdftoppm", "-png", "-r", str(SAMPLE_DPI), "-singlefile", "-f", str(page), "-l", str(page),
                             str(pdf), str(stem)], capture_output=True)
    return result.returncode == 0 and out.exists()


def build_groups(lowcontent: list[dict], personal: list[dict], raw: Path, out_dir: Path) -> list[dict]:
    """Groups of pages with a suggested action, each with a few rendered samples, so a person can judge a whole group."""
    spec = []
    for kind, (label, why, actions) in LOW_GROUPS.items():
        items = [i for i in lowcontent if i["kind"] == kind and i["suggest"] == "exclude"]
        spec.append({"id": f"lc:{kind}", "source": "lc", "kind": kind, "label": label, "why": why, "items": items,
                     "actions": actions or DEFAULT_LOW_ACTIONS})
    by_group = {g: [p for p in personal if p["group"] == g] for g in ("case", "name_list", "contact_personal")}
    spec.append({"id": "pd:name_list", "source": "pd", "kind": "name_list", "label": "หน้ารายชื่อบุคคลทั้งหน้า (คณะทำงาน/ผู้ทรงคุณวุฒิ)",
                 "why": "ทั้งหน้าเป็นรายชื่อ ไม่ใช่เนื้อหาทางคลินิก · ตัดออก หรือแท็กเป็นรายชื่อบุคคล (PDPA) เก็บไว้ในระบบแต่ไม่ให้ค้น",
                 "items": by_group["name_list"],
                 "actions": [("exclude", "ตัดออกทั้งกลุ่ม"), ("tag", "แท็กเป็นรายชื่อบุคคล (เก็บ ไม่ index)"), ("keep", "เก็บทั้งกลุ่ม")]})
    spec.append({"id": "pd:contact_personal", "source": "pd", "kind": "contact_personal",
                 "label": "อีเมล/เบอร์/เลขประจำตัวที่เป็นของบุคคล",
                 "why": "ระบบเห็นว่าเป็นของบุคคล (มือถือ, อีเมลฟรีใกล้ชื่อบุคคล) ลบเฉพาะค่านั้น เนื้อหาหน้ายังอยู่ · ตัวที่คำนวณว่าเป็นของหน่วยงานเก็บไว้แล้ว",
                 "items": by_group["contact_personal"], "actions": [("redact", "ลบค่าที่ธงไว้ทั้งกลุ่ม"), ("keep", "เก็บทั้งกลุ่ม")]})
    spec.append({"id": "pd:case", "source": "pd", "kind": "case", "label": "เคสผู้ป่วย (กรณีศึกษา)",
                 "why": "บรรยายเคสพร้อมอายุ/ที่อยู่/อาชีพ/ครอบครัว/ผลตรวจ แทนข้อมูลระบุตัวด้วยแท็ก ผลตรวจและกระบวนการพยาบาลยังอยู่",
                 "items": by_group["case"],
                 "actions": [("redact", "แทนข้อมูลระบุตัวด้วยแท็ก (อายุ/ที่อยู่/อาชีพ/ที่พัก)"), ("exclude", "ตัดทั้งกลุ่ม"),
                             ("keep", "เก็บทั้งกลุ่ม")]})
    img_dir = out_dir / "img"
    groups = []
    for g in spec:
        if not g["items"]:
            continue
        samples = []
        for item in spread(g["items"], SAMPLES_PER_GROUP):
            name = item["key"].replace(":", "__") + ".png"
            img_dir.mkdir(parents=True, exist_ok=True)
            pdf = raw / item["document_id"] / "source.pdf"
            ok = pdf.exists() and ((img_dir / name).exists() or render_page(pdf, item["p"], img_dir / name))
            text = item.get("text") or item.get("preview") or ""
            samples.append({"key": item["key"], "p": item["p"], "document_id": item["document_id"], "pdf": item.get("pdf"),
                            "img": f"img/{name}" if ok else None, "text": text[:260]})
        groups.append({"id": g["id"], "source": g["source"], "kind": g["kind"], "label": g["label"], "why": g["why"],
                       "actions": [{"id": a, "label": t} for a, t in g["actions"]],
                       "keys": [i["key"] for i in g["items"]],
                       "documents": len({i["document_id"] for i in g["items"]}), "samples": samples})
    return groups


def load_doc_types(manifest: Path) -> dict[str, str]:
    if not manifest.exists():
        return {}
    records = (json.loads(x) for x in manifest.read_text(encoding="utf-8").split("\n") if x.strip())
    return {r["document_id"]: r.get("document_type", "") for r in records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True, help="folder with <document_id>/source.pdf for page links")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST, help="documents.jsonl, for document types")
    parser.add_argument("--review-id", default="page-tags-v7")
    args = parser.parse_args(argv)

    doc_types = load_doc_types(args.manifest)
    docs, personal, lowcontent, counts = [], [], [], Counter()
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        pages, found, low = scan_document(rows, doc_types.get(folder.name, ""))
        personal.extend(found)
        lowcontent.extend(low)
        suggested = sum(1 for p in pages if p["suggest"])
        counts.update(population_suggested=suggested, population_mention_only=sum(1 for p in pages if p["mention"]))
        counts.update(f"name_class_{p['name_class']}" for p in pages if p.get("name_class"))
        if suggested:
            pdf = args.raw / folder.name / "source.pdf"
            docs.append({"document_id": folder.name,
                         "pdf": Path(os.path.relpath(pdf, args.out)).as_posix() if pdf.exists() else None,
                         "suggested_pages": suggested, "pages": pages})
    docs.sort(key=lambda d: -d["suggested_pages"])
    # Relative links work both from file:// and from a local server whose root is the data folder.
    pdfs = {d.name: Path(os.path.relpath(d / "source.pdf", args.out)).as_posix()
            for d in args.raw.iterdir() if (d / "source.pdf").exists()}
    for item in personal + lowcontent:
        item["pdf"] = pdfs.get(item["document_id"])
    counts.update(f"personal_{i['group']}" for i in personal)
    counts.update(f"low_{i['kind']}" for i in lowcontent)
    groups = build_groups(lowcontent, personal, args.raw, args.out)
    payload = {"review_id": args.review_id, "corpus_version": args.corpus.name, "docs": docs, "personal": personal,
               "lowcontent": lowcontent, "groups": groups}
    args.out.mkdir(parents=True, exist_ok=True)
    template = (Path(__file__).with_name("page_tag_review.html")).read_text(encoding="utf-8")
    out = args.out / "page_tags.html"
    out.write_text(template.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")),
                   encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(out), "documents_with_population_suggestions": len(docs), **dict(sorted(counts.items()))},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
