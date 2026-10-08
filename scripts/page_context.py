"""Context features for corpus pages: which population a page is about, whether it is a list of people,
and whether a phone number or e-mail belongs to an organisation or to a person.

A bare keyword hit is a weak signal ("children" in a drug caution does not make an adult page paediatric,
and one author name on a leaflet is not a name list). Every judgement here combines several signals from the
page and from its section, returns the reasons, and keeps weak cases as "ambiguous" for a person to decide.
Rules are deliberately simple and explainable; they are evaluated in tests/test_page_context.py and in
docs/page_context_evaluation.md against chapters whose population is known from the table of contents.
"""

from __future__ import annotations

import re

THAI = "ก-๙"

# ---------------------------------------------------------------- population

POPULATION_STRONG = {
    "pediatric": re.compile(
        r"เด็กและวัยรุ่น|เบาหวานในเด็ก|ผู้ป่วยเด็ก|เด็กอายุ|วัยเด็ก|เด็กเล็ก|เด็กโต|ทารก|วัยรุ่น|"
        r"pediatric|paediatric|children|adolescen|อายุ\s*(?:น้อยกว่า|<)\s*1[0-9]\s*ปี", re.I),
    "pregnancy": re.compile(
        r"หญิงตั้งครรภ์|หญิงมีครรภ์|ผู้ป่วยที่ตั้งครรภ์|ขณะตั้งครรภ์|ขณะมีครรภ์|ก่อนตั้งครรภ์|การตั้งครรภ์|ครรภ์เป็นพิษ|"
        r"ทารกในครรภ์|หลังคลอด|ให้นมบุตร|ให้นมลูก|เบาหวานขณะตั้งครรภ์|GDM|gestational|pregnan|breastfeed", re.I),
    "elderly": re.compile(
        r"ผู้สูงอายุ|สูงวัย|geriatric|elderly|older adult|frailty|ภาวะเปราะบาง|"
        r"อายุ\s*(?:มากกว่า|มากกว่าหรือเท่ากับ|ตั้งแต่|≥|>)\s*(?:60|65|70|75|80)\s*ปี", re.I),
}
# Organisation names and specialties contain the same words ("สมาคมต่อมไร้ท่อเด็กและวัยรุ่นไทย") but say nothing about the audience.
ORG_PHRASE = re.compile(
    r"(?:สมาคม|ราชวิทยาลัย|ชมรม|ภาควิชา|สาขาวิชา|หน่วย|คลินิก|ศูนย์|สถาบัน)[ก-๙ ]{0,25}?(?:เด็ก|กุมาร|สูงอายุ|ผู้สูงวัย)[ก-๙]*|"
    r"(?:กุมารเวช|กุมารแพทย์|เวชศาสตร์ผู้สูงอายุ|สูตินรี|ต่อมไร้ท่อเด็ก)[ก-๙]*")
SECTION_START = re.compile(r"^\s*(?:บทที่|ตอนที่|ส่วนที่|Chapter|Part)\s*\d+|^\s*(?:หมวด|ภาคผนวก)\s*\S*\d*")
CHAPTER_REFERENCES = re.compile(r"(?:บทที่|Chapter)\s*\d+")
# Phrases that make a mention an exception or caution inside adult content.
CAUTION = re.compile(r"ห้ามใช้|หลีกเลี่ยง|ข้อห้าม|ยกเว้น|ไม่ควรใช้|ไม่แนะนำให้ใช้|contraindicat", re.I)
REFERENCE_LINE = re.compile(
    r"^\s*\d{1,3}\.\s+.*(?:et al|doi|[A-Z][a-z]+ [A-Z]{1,3}[,.]|\b(?:19|20)\d{2};\s*\d+|\bDiabetes Care\b|\bLancet\b)", re.I)

DENSITY_MIN = 6.0      # strong hits per 1000 letters/digits for a page to be about the population on its own
STRONG_MIN = 4         # and at least this many strong hits
PARTIAL_DENSITY = 3.0  # between this and DENSITY_MIN the page mixes adult content with population-specific parts
PARTIAL_MIN = 3
TITLE_CHARS = 120      # a chapter heading is judged on its title, not on the paragraph after it


def signal(text: str) -> int:
    return len(re.findall(r"[ก-๙A-Za-z0-9]", text))


def section_heading(text: str) -> str | None:
    """Heading of a chapter/part that starts on this page; cross-references in body text do not count."""
    if SECTION_START.match(text) and len(CHAPTER_REFERENCES.findall(text)) < 3:
        return " ".join(text[:220].split())[:160]
    return None


def is_reference_page(text: str) -> bool:
    """A page that mostly lists cited papers: terms in titles describe the cited work, not the audience."""
    return sum(1 for ln in text.split("\n") if REFERENCE_LINE.search(ln)) >= 2


def is_contents_page(text: str) -> bool:
    return "สารบัญ" in text[:200] or len(CHAPTER_REFERENCES.findall(text)) >= 4


# In a title the plain word names the audience ("อาหารสำหรับเด็กระดับประถม"); in body text it is only a passing word.
TITLE_TERMS = {
    "pediatric": re.compile(r"เด็ก|วัยรุ่น|ทารก|ปฐมวัย|pediatric|paediatric|children|adolescen", re.I),
    "pregnancy": re.compile(r"ตั้งครรภ์|มีครรภ์|ให้นมบุตร|หลังคลอด|pregnan|gestational", re.I),
    "elderly": re.compile(r"สูงอายุ|สูงวัย|geriatric|elderly|older adult", re.I),
}


def title_population(heading: str) -> str | None:
    """Population named by a chapter/part title: exactly one population -> that one; none or several -> None."""
    cleaned = ORG_PHRASE.sub(" ", heading[:TITLE_CHARS])
    found = [label for label, pattern in TITLE_TERMS.items() if pattern.search(cleaned)]
    return found[0] if len(found) == 1 else None


def page_population_scores(text: str) -> dict:
    """Per-population evidence for one page: strong hits, density per 1000 letters, hits that are cautions."""
    cleaned = ORG_PHRASE.sub(" ", text)
    sig = max(signal(cleaned), 1)
    out = {}
    for label, pattern in POPULATION_STRONG.items():
        hits = list(pattern.finditer(cleaned))
        if not hits:
            continue
        caution = sum(1 for m in hits if CAUTION.search(cleaned[max(0, m.start() - 60):m.end() + 60]))
        out[label] = {"hits": len(hits), "density": round(len(hits) * 1000 / sig, 1), "caution": caution}
    return out


def page_population(text: str) -> tuple[str | None, list[str], dict]:
    """(label or None, reasons, scores) from the page's own text.

    pediatric / pregnancy / elderly   the page is mostly about that population (enough dense, specific terms)
    mixed                             adult content with population-specific parts, or two populations at once
    None                              a passing mention, a caution inside adult content, a reference list or contents page
    """
    scores = page_population_scores(text)
    if is_reference_page(text) or is_contents_page(text):
        return None, [], scores
    specific, partial = [], []
    for label, s in scores.items():
        if s["caution"] >= s["hits"]:
            continue
        if s["hits"] >= STRONG_MIN and s["density"] >= DENSITY_MIN:
            specific.append((s["hits"], label))
        elif s["hits"] >= PARTIAL_MIN and s["density"] >= PARTIAL_DENSITY:
            partial.append((s["hits"], label))
    if len(specific) == 1 and not partial:
        label = specific[0][1]
        s = scores[label]
        return label, [f"พบคำเฉพาะกลุ่ม {s['hits']} ครั้ง (ความหนาแน่น {s['density']}/1000 ตัวอักษร)"], scores
    if specific or partial:
        names = ", ".join(lab for _, lab in sorted(specific + partial, reverse=True))
        return "mixed", [f"หน้าปนกันระหว่างเนื้อหาทั่วไปกับส่วนเฉพาะกลุ่ม: {names}"], scores
    return None, [], scores


def population_for_document(rows: list[dict]) -> dict[int, dict]:
    """Population suggestion per page of one document: the page's own evidence plus the chapter it sits in.

    A chapter whose title names one population gives that population to all its pages, also to pages that are
    short or are the chapter's reference list; a page that is strongly about another population keeps its own label.
    """
    result: dict[int, dict] = {}
    section_label, section_title = None, None
    for row in sorted(rows, key=lambda r: r["pdf_page"]):
        text = row.get("text") or ""
        heading = section_heading(text)
        if heading:
            section_label, section_title = title_population(heading), heading
        label, reasons, scores = page_population(text)
        confidence = "medium"
        if section_label and signal(text) > 0:
            if label in (None, "mixed"):
                label, reasons, confidence = section_label, [f"อยู่ในบทที่ชื่อบอกกลุ่มนี้: {section_title[:70]}"], "high"
            elif label == section_label:
                confidence = "high"
            else:
                reasons.append(f"ต่างจากบทที่อยู่ ({section_label}) จึงใช้หลักฐานของหน้าเอง")
        result[row["pdf_page"]] = {"label": label, "confidence": confidence if label else None, "reasons": reasons,
                                   "section": section_title, "scores": scores}
    return result


# ---------------------------------------------------------------- people

TITLES = (r"ศาสตราจารย์|รองศาสตราจารย์|ผู้ช่วยศาสตราจารย์|นายแพทย์|แพทย์หญิง|ทันตแพทย์หญิง|ทันตแพทย์|เภสัชกรหญิง|เภสัชกร|"
          r"พยาบาลวิชาชีพ|นางสาว|นาย|นาง|น\.ส\.|ด\.ช\.|ด\.ญ\.|ศ\.|รศ\.|ผศ\.|ดร\.|นพ\.|พญ\.|ทพ\.|ทพญ\.|ภก\.|ภญ\.|พว\.|อ\.")
NAME = re.compile(rf"(?<![{THAI}])(?:(?:{TITLES})\s?)+[{THAI}]{{2,}}[ \t]+[{THAI}]{{2,}}")
AFFILIATION = re.compile(r"คณะ|มหาวิทยาลัย|โรงพยาบาล|ภาควิชา|สาขาวิชา|สถาบัน|กรม|กอง|สำนัก|สมาคม|ศูนย์|วิทยาลัย|ราชวิทยาลัย|"
                         r"ชมรม|มูลนิธิ|Hospital|University|Faculty|Department|Institute")
ROLE = re.compile(r"ที่ปรึกษา|ประธาน|กรรมการ|เลขานุการ|บรรณาธิการ|ผู้ทรงคุณวุฒิ|ผู้จัดทำ|คณะทำงาน|คณะผู้จัดทำ|รายนาม|"
                  r"กิตติกรรมประกาศ|ผู้เขียน|ผู้นิพนธ์|ผู้ประสานงาน|ผู้ร่วมจัดทำ|ผู้พิจารณา")
CREDIT = re.compile(r"จัดทำโดย|เรียบเรียง|ออกแบบ|ภาพประกอบ|จัดพิมพ์|ผู้เขียน|เรียบเรียงโดย|ข้อมูลโดย|ตรวจทานโดย|พิมพ์ที่")
# A heading that introduces a list of people. Plain "คณะกรรมการ"/"คณะทำงาน" are left out: they are also organisation names.
LIST_HEADING = re.compile(r"รายนาม|คณะผู้จัดทำ|ผู้ทรงคุณวุฒิ|กิตติกรรมประกาศ|คณะที่ปรึกษา|คณะอนุกรรมการ|ผู้ร่วมจัดทำ")
LIST_HEADING_MIN_RATIO = 0.4   # share of list-like lines when at least two titled names are found
LIST_HEADING_UNTITLED_RATIO = 0.6  # names without titles are not detected, so a stricter share is required
LEAFLET_TYPES = {"patient_education", "poster"}

LIST_MIN_NAMES = 5
LIST_MIN_RATIO = 0.5
CREDIT_MAX_NAMES = 5


def person_lines(text: str) -> dict:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    names, listy = [], 0
    for ln in lines:
        found = [m.group(0) for m in NAME.finditer(ln)]
        names.extend(" ".join(n.split()) for n in found)
        if found or AFFILIATION.search(ln) or ROLE.search(ln):
            listy += 1
    return {"lines": len(lines), "listy": listy, "names": names, "distinct": len(set(names)),
            "ratio": round(listy / len(lines), 2) if lines else 0.0,
            "roles": len(ROLE.findall(text)), "credit_words": len(CREDIT.findall(text))}


def _list_heading_page(text: str, f: dict) -> bool:
    if not LIST_HEADING.search(text[:120]) or f["lines"] < 5:
        return False
    return f["ratio"] >= (LIST_HEADING_MIN_RATIO if f["distinct"] >= 2 else LIST_HEADING_UNTITLED_RATIO)


def name_page_class(text: str, doc_type: str) -> tuple[str, list[str], dict]:
    """Classify how personal names appear on a page.

    name_list     most of the page lists people (committee, reviewers, contributors): decide cut / tag / keep
    name_partial  a list of people sits inside a page that also has other content: decide redact / cut / keep
    credits       a few names that credit the people who made a leaflet or infographic: keep, searchable
    mention       one to three names inside normal content (a cited author, a speaker): keep
    none          no personal names
    """
    f = person_lines(text)
    n, ratio = f["distinct"], f["ratio"]
    if n == 0 and not _list_heading_page(text, f):
        return "none", [], f
    reasons = [f"ชื่อบุคคล {n} ชื่อ, {int(ratio * 100)}% ของบรรทัดเป็นชื่อ/สังกัด/ตำแหน่ง"]
    leaflet = doc_type in LEAFLET_TYPES
    if _list_heading_page(text, f):
        return "name_list", reasons + ["หัวข้อหน้าเป็นรายนามคณะทำงาน/ผู้ทรงคุณวุฒิ"], f
    if n >= LIST_MIN_NAMES and ratio >= LIST_MIN_RATIO:
        if leaflet and n <= CREDIT_MAX_NAMES + 3 and f["credit_words"]:
            return "credits", reasons + ["แผ่นพับ/สื่อประชาชนที่ระบุผู้จัดทำ"], f
        return "name_list", reasons, f
    if n >= 3 and ratio >= 0.7 and f["roles"]:
        return "name_list", reasons + ["มีคำระบุตำแหน่ง/คณะทำงาน"], f
    if n >= LIST_MIN_NAMES:
        return "name_partial", reasons + ["รายชื่อปนอยู่กับเนื้อหาอื่นในหน้า"], f
    if n <= CREDIT_MAX_NAMES and (leaflet or f["credit_words"]):
        return "credits", reasons + ["ระบุผู้จัดทำ/ผู้เขียน"], f
    return "mention", reasons, f


# ---------------------------------------------------------------- contacts

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\d-])0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}(?![\d-])")
ORG_WORDS = re.compile(r"กอง|กรม|สำนัก|ศูนย์|โรงพยาบาล|รพ\.|สมาคม|มูลนิธิ|คณะ|สถาบัน|หน่วยงาน|กระทรวง|ฝ่าย|งาน[ก-๙]|สายด่วน|"
                       r"call\s*center|ติดต่อสอบถาม|สอบถามข้อมูลเพิ่มเติม|ที่อยู่|ตั้งอยู่|Hospital|Department|Institute", re.I)
ADDRESS_WORDS = re.compile(r"แฟ็กซ์|โทรสาร|\bfax\b|ถนน|ซอย|แขวง|เขต|อำเภอ|จังหวัด|ตำบล|กรุงเทพ|รหัสไปรษณีย์|\b\d{5}\b", re.I)
ORG_DOMAIN = re.compile(r"@[\w.-]*\.(?:go\.th|ac\.th|or\.th|moph\.go\.th|ac\.uk|edu|org|gov)\b", re.I)
GENERIC_BOX = re.compile(r"^(?:info|contact|admin|office|secretary|ncd|clinic|elearning|hypertension|support|webmaster)[\w.]*@", re.I)
FREE_MAIL = re.compile(r"@(?:gmail|hotmail|yahoo|outlook|live|icloud)\.", re.I)
MOBILE = re.compile(r"^0[689]")
PERSON_CONTEXT = re.compile(r"Corresponding|ผู้นิพนธ์ประสานงาน|ผู้เขียนหลัก|ผู้ประสานงาน|ติดต่อคุณ|คุณ[ก-๙]{2,}|"
                            r"Author|E-?mail\s*:|ศ\.|รศ\.|ผศ\.|นพ\.|พญ\.|ดร\.|นาย|นางสาว|นาง", re.I)


def valid_phone(value: str) -> bool:
    """A real Thai number has 9-10 digits and does not start 00 (chart axes such as '00110 120' are not phones)."""
    digits = re.sub(r"\D", "", value)
    return len(digits) in (9, 10) and not digits.startswith("00")


def classify_contact(kind: str, value: str, context: str) -> tuple[str, str]:
    """('org'|'personal'|'ambiguous', reason) for a phone number or e-mail address from its surrounding text."""
    org, person, why_org, why_person = 0, 0, [], []
    if kind == "email":
        if ORG_DOMAIN.search(value):
            org += 2
            why_org.append("โดเมนหน่วยงาน")
        if GENERIC_BOX.search(value):
            org += 2
            why_org.append("กล่องจดหมายกลาง (info/ncd/clinic…)")
        if FREE_MAIL.search(value) and not GENERIC_BOX.search(value):
            person += 1
            why_person.append("อีเมลฟรี (gmail/hotmail…)")
    else:
        digits = re.sub(r"\D", "", value)
        if MOBILE.match(digits):
            person += 1
            why_person.append("เบอร์มือถือ")
        elif digits.startswith(("02", "03", "04", "05", "07")):
            org += 1
            why_org.append("เบอร์โทรศัพท์บ้าน/สำนักงาน")
    if ORG_WORDS.search(context):
        org += 1
        why_org.append("มีชื่อหน่วยงาน/คำว่าติดต่อสอบถามใกล้ ๆ")
    if len(ADDRESS_WORDS.findall(context)) >= 2:
        org += 1
        why_org.append("อยู่ในบล็อกที่อยู่/โทร/แฟกซ์ของหน่วยงาน")
    if PERSON_CONTEXT.search(context):
        person += 1
        why_person.append("มีชื่อบุคคล/ตำแหน่ง/ผู้นิพนธ์ประสานงานใกล้ ๆ")
    if person - org >= 1 and person >= 2:
        return "personal", "; ".join(why_person)
    if org - person >= 1 and org >= 2:
        return "org", "; ".join(why_org)
    parts = (["เข้าข้างบุคคล: " + ", ".join(why_person)] if why_person else []) + \
            (["เข้าข้างหน่วยงาน: " + ", ".join(why_org)] if why_org else [])
    return "ambiguous", "; ".join(parts) or "ไม่มีสัญญาณชัด"
