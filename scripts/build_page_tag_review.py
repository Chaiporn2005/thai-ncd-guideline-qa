"""Build a local HTML page for a person to tag page populations and decide personal-data (PDPA) handling.

Scans every indexable page of a corpus version for
  * population cues (children/adolescents, pregnancy) and chapter headings, and proposes page ranges;
  * personal data: titled personal names, e-mail addresses, phone numbers, Thai citizen IDs (checksum-valid),
    HN/AN numbers. It also scans text kept beside the retrieval text (removed edge lines, pre-review text,
    OCR figure notes) because those stay in the stored page record.
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
from collections import Counter
from pathlib import Path

POPULATION_TERMS = {
    "pediatric": re.compile(r"เด็ก|วัยรุ่น|ทารก|ปฐมวัย|pediatric|paediatric|children|adolescen", re.I),
    "pregnancy": re.compile(r"ตั้งครรภ์|มีครรภ์|ขณะครรภ์|ให้นมบุตร|หลังคลอด|GDM|gestational|pregnan", re.I),
    "elderly": re.compile(r"ผู้สูงอายุ|สูงวัย|geriatric|elderly|older adult", re.I),
}
# Case narratives: a real (even unnamed) person's age, place, family and results together can identify them.
CASE_NARRATIVE = re.compile(r"กรณีศึกษา")
CASE_EXAMPLE = re.compile(r"ผู้ป่วย(?:ชาย|หญิง)\s*อายุ\s*\d+\s*ปี")
CASE_MIN_MENTIONS = 3
CHAPTER = re.compile(r"(?:บทที่|Chapter)\s*\d+")
CHAPTER_START = re.compile(r"^\s*(?:บทที่|Chapter)\s*\d+")
PART_DIVIDER = re.compile(r"หมวด|ภาคผนวก|\bPart\b", re.I)

THAI = "ก-๙"
TITLES = (r"ศาสตราจารย์|รองศาสตราจารย์|ผู้ช่วยศาสตราจารย์|นายแพทย์|แพทย์หญิง|ทันตแพทย์หญิง|ทันตแพทย์|"
          r"เภสัชกรหญิง|เภสัชกร|นางสาว|นาย|นาง|น\.ส\.|ด\.ช\.|ด\.ญ\.|ศ\.|รศ\.|ผศ\.|ดร\.|นพ\.|พญ\.|ทพ\.|ทพญ\.|"
          r"ภก\.|ภญ\.|พว\.|อ\.")
PERSONAL_PATTERNS = {
    "name": re.compile(rf"(?<![{THAI}])(?:(?:{TITLES})\s?)+[{THAI}]{{2,}}[ \t]+[{THAI}]{{2,}}"),
    "email": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "phone": re.compile(r"(?<![\d-])0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}(?![\d-])"),
    "citizen_id": re.compile(r"(?<![\d-])\d[- ]?\d{4}[- ]?\d{5}[- ]?\d{2}[- ]?\d(?![\d-])"),
    "hospital_number": re.compile(r"\b(?:HN|AN)\s*[:.]?\s*\d{4,}"),
}
# Pages that would only add noise (or nothing) as standalone retrieval units.
NAV_TOKENS = re.compile(r"Previous Page|Next Page|Previous Chapter|Next Chapter|Contents|HOME|กลับหน้าสารบัญ|บันทึก", re.I)
GLYPH_RUN = re.compile(r"(?:/g\s?\d+){3,}")  # font glyph ids left by a broken text layer, e.g. /g94/g67/g92
DIVIDER = re.compile(r"^\s*(?:บทที่|หมวด|ภาคผนวก|ตอนที่|ส่วนที่|Chapter|Part)", re.I)
CAPTION = re.compile(r"^\s*(?:รูปที่|ตารางที่|แผนภูมิที่|แผนภาพที่|ภาพที่|Figure|Fig\.|Table)", re.I)
NAV_ONLY_SIGNAL, EMPTY_SIGNAL, DIVIDER_SIGNAL, EDGE_SIGNAL, SHORT_SIGNAL = 15, 30, 80, 150, 100
EDGE_PAGES = 3  # cover zone: the first pages; the same count is checked from the end
GLYPH_SHARE = 0.3
FRONT_MATTER = re.compile(r"คณะผู้จัดทำ|คณะทำงาน|รายนาม|คณะกรรมการ|ที่ปรึกษา|บรรณาธิการ|กิตติกรรมประกาศ|ผู้ทรงคุณวุฒิ")
FREE_MAIL = re.compile(r"@(?:gmail|hotmail|yahoo|outlook|live|icloud)\.", re.I)
MOBILE = re.compile(r"^0[689]")
NAME_LIST_MIN = 4  # four or more personal names on one page reads as a list of people, not guideline content


def thai_id_valid(digits: str) -> bool:
    if len(digits) != 13 or digits.startswith(("978", "979")):  # ISBN-13 prefixes
        return False
    total = sum(int(d) * (13 - i) for i, d in enumerate(digits[:12]))
    return (11 - total % 11) % 10 == int(digits[12])


def indexable(row: dict) -> bool:
    review = row.get("human_review") or {}
    return row["status"] in ("ok", "ok_minor_issues") or (
        row["status"] in ("ocr_unreviewed", "degraded") and review.get("outcome") in ("pass", "fix"))


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


def personal_findings(row: dict) -> list[dict]:
    found = []
    for field, text in page_strings(row):
        for kind, pattern in PERSONAL_PATTERNS.items():
            for m in pattern.finditer(text):
                value = m.group(0)
                if kind == "citizen_id" and not thai_id_valid(re.sub(r"\D", "", value)):
                    continue
                found.append({"type": kind, "field": field, "value": value, "context": context(text, *m.span())})
    found.extend(case_findings(row.get("text") or ""))
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


def suggest_personal(findings: list[dict], text: str) -> tuple[str, list[bool], str]:
    """Return (page action, per-finding redact default, reason)."""
    if any(f["type"] == "case" for f in findings):
        return "exclude_page", [False] * len(findings), "บรรยายเคสผู้ป่วย (ข้อมูลสุขภาพรายบุคคล: อายุ/ที่อยู่/ครอบครัว/ผลตรวจ) — ถ้าเป็นเคสจริงควรตัดออก"
    names = {f["value"] for f in findings if f["type"] == "name" and f["field"] == "text"}
    if len(names) >= NAME_LIST_MIN or (len(names) >= 2 and FRONT_MATTER.search(text)):
        return "exclude_page", [False] * len(findings), f"รายชื่อบุคคล {len(names)} ชื่อ (หน้าคณะผู้จัดทำ/รายนาม)"
    redact = []
    for f in findings:
        if f["type"] in ("citizen_id", "hospital_number"):
            redact.append(True)
        elif f["type"] == "email":
            redact.append(bool(FREE_MAIL.search(f["value"])))
        elif f["type"] == "phone":
            redact.append(bool(MOBILE.match(f["value"])))
        else:
            redact.append(False)
    if any(redact):
        return "redact", redact, "มีข้อมูลติดต่อส่วนตัว (มือถือ/อีเมลส่วนตัว/เลขประจำตัว)"
    if any(f["type"] == "case_example" for f in findings):
        return "keep", redact, "ตัวอย่างผู้ป่วยในเนื้อหา (น่าจะสมมติ/ตัวอย่างการคำนวณ) — ตรวจว่าไม่ใช่เคสจริง"
    return "keep", redact, "ชื่อในเนื้อหา/ข้อมูลติดต่อหน่วยงาน"


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


def population_hits(text: str) -> dict:
    hits = {}
    for label, pattern in POPULATION_TERMS.items():
        matches = list(pattern.finditer(text))
        if matches:
            hits[label] = {"count": len(matches), "snippets": [context(text, *m.span(), 50) for m in matches[:3]]}
    return hits


def chapter_heading(text: str) -> str | None:
    """Heading of a chapter or part that starts on this page; cross-references inside body text do not count."""
    if CHAPTER_START.match(text) and len(CHAPTER.findall(text)) < 3:  # a table of contents lists many chapters
        return " ".join(text[:220].split())[:140]
    if len(text.strip()) < 80 and PART_DIVIDER.search(text):  # divider page between parts
        return " ".join(text.split())
    return None


def scan_document(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    pages, personal, lowcontent = [], [], []
    last_page = max(r["pdf_page"] for r in rows)
    chapter, chapter_label = None, None
    for row in rows:
        text = row.get("text") or ""
        heading = chapter_heading(text)
        if heading:
            chapter = heading
            chapter_label = next((label for label, p in POPULATION_TERMS.items() if p.search(heading)), None)
        hits = population_hits(text) if indexable(row) else {}
        pages.append({"p": row["pdf_page"], "indexable": indexable(row), "chapter": chapter,
                      "suggest": chapter_label if indexable(row) else None, "hits": hits,
                      "first": " ".join(text.split())[:110]})
        if indexable(row):
            flagged = low_content(row, last_page)
            if flagged:
                lowcontent.append({"key": f"{row['document_id']}:p{row['pdf_page']}", "document_id": row["document_id"],
                                   "p": row["pdf_page"], "text": text[:500], **flagged})
            findings = personal_findings(row)
            if findings:
                action, redact, reason = suggest_personal(findings, text)
                personal.append({"key": f"{row['document_id']}:p{row['pdf_page']}", "document_id": row["document_id"],
                                 "p": row["pdf_page"], "suggest": action, "redact": redact, "reason": reason,
                                 "findings": findings})
    return pages, personal, lowcontent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True, help="folder with <document_id>/source.pdf for page links")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--review-id", default="page-tags-v7")
    args = parser.parse_args(argv)

    docs, personal, lowcontent, counts = [], [], [], Counter()
    for folder in sorted(p for p in args.corpus.iterdir() if (p / "pages.jsonl").exists()):
        rows = [json.loads(x) for x in (folder / "pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
        pages, found, low = scan_document(rows)
        personal.extend(found)
        lowcontent.extend(low)
        hit_pages = sum(1 for p in pages if p["hits"] or p["suggest"])
        counts.update(population_pages=hit_pages, personal_pages=len(found))
        if hit_pages:
            pdf = args.raw / folder.name / "source.pdf"
            docs.append({"document_id": folder.name,
                         "pdf": Path(os.path.relpath(pdf, args.out)).as_posix() if pdf.exists() else None,
                         "hit_pages": hit_pages, "pages": pages})
    docs.sort(key=lambda d: -d["hit_pages"])
    # Relative links work both from file:// and from a local server whose root is the data folder.
    pdfs = {d.name: Path(os.path.relpath(d / "source.pdf", args.out)).as_posix()
            for d in args.raw.iterdir() if (d / "source.pdf").exists()}
    for item in personal + lowcontent:
        item["pdf"] = pdfs.get(item["document_id"])
    counts.update(Counter(f"{i['suggest']}" for i in personal))
    counts.update(Counter(f"low_{i['kind']}" for i in lowcontent))
    payload = {"review_id": args.review_id, "corpus_version": args.corpus.name, "docs": docs, "personal": personal,
               "lowcontent": lowcontent}
    args.out.mkdir(parents=True, exist_ok=True)
    template = (Path(__file__).with_name("page_tag_review.html")).read_text(encoding="utf-8")
    out = args.out / "page_tags.html"
    out.write_text(template.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")),
                   encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(out), "documents_with_population_cues": len(docs), **counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
