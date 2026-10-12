"""Rule-based input guards (decisions G1 personal data and G3 scope; owner chose "rules only", 2026-10-11; the rules themselves are AI-suggested).

A guard is a callable `question -> None | {"block": True, "category", "reason", "message"}`; the pipeline stops before retrieval and before any LLM call when one blocks
(src/ncdqa/rag/pipeline.py). Nothing here calls a model, so the guard runs before any text leaves the machine (decision H2).
  G1  personal identifiers: a valid Thai national ID (13 digits with the check digit), Thai phone numbers, e-mail addresses, hospital numbers (HN/AN),
      and a title + first name + surname. The question is refused and the user is asked to retype it without them. The matched text is never echoed or logged.
      Health numbers on their own (a lab value, an age) do not identify anyone and pass as ordinary questions, as proposed in the decision paper.
  G3  scope: a request that the system prescribe, set a dose for, or diagnose a named or first-person patient is refused ("see a clinician"); general knowledge questions
      about what the guidelines say are not. Words that signal an acute emergency get a message to call 1669.
Known limits (stated, not hidden): Thai personal names without a title are not detected; the scope rules are patterns, not understanding, so a rephrased request can pass
and an odd general question can be refused; both error rates are measured on a silver set (scripts/eval_input_guard.py). The silver labels were written by the AI that
wrote the rules and no human reviewed them.
"""

from __future__ import annotations

import re

Verdict = dict

EMERGENCY_MESSAGE = "ถ้ามีอาการฉุกเฉิน (เช่น เจ็บหน้าอก หายใจไม่ออก หมดสติ ชัก อ่อนแรงเฉียบพลัน) โทร 1669 หรือไปโรงพยาบาลทันที ระบบนี้ตอบเพื่อการศึกษาและช่วยในภาวะฉุกเฉินไม่ได้"
CLINICIAN_MESSAGE = "ระบบนี้ไม่วินิจฉัย ไม่สั่งหรือปรับขนาดยาเฉพาะราย กรุณาปรึกษาแพทย์หรือเภสัชกร คุณถามความรู้ทั่วไปจากแนวทางเวชปฏิบัติได้"
PII_MESSAGE = "คำถามนี้มีข้อมูลที่ระบุตัวบุคคลได้ ({what}) เพื่อความเป็นส่วนตัวระบบไม่ประมวลผล กรุณาพิมพ์คำถามใหม่โดยไม่ใส่ข้อมูลดังกล่าว"

_ID_CANDIDATE = re.compile(r"(?<!\d)(?:\d[\s-]?){12}\d(?!\d)")
_PHONE = re.compile(r"(?<!\d)(?:0[689]\d[\s-]?\d{3}[\s-]?\d{4}|0[2-7]\d?[\s-]?\d{3}[\s-]?\d{4})(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_HN = re.compile(r"(?:\bHN\b|\bAN\b|เลข\s*HN|เลขที่ผู้ป่วย|เลขประจำตัวผู้ป่วย)\s*[:：]?\s*\d{3,}", re.I)
_NAME = re.compile(r"(?:นางสาว|น\.ส\.|นาย|นาง)\s*[ก-๙]{2,}\s+[ก-๙]{2,}")

_FIRST_PERSON = r"(?:ผม|ฉัน|ดิฉัน|หนู|คุณแม่|คุณพ่อ|แม่ผม|พ่อผม|แม่ฉัน|พ่อฉัน|คนไข้ของ)"
_DIRECTIVE = [
    re.compile(r"(?:สั่งยา|จ่ายยา|วินิจฉัย).{0,20}?(?:ให้)?\s*" + _FIRST_PERSON),
    re.compile(r"(?:บอก|ช่วยบอก|วินิจฉัย)\s*(?:ว่า)?\s*" + _FIRST_PERSON + r".{0,25}(?:เป็น|ระยะ|โรค)"),
    re.compile(_FIRST_PERSON + r".{0,30}(?:ควร|ต้อง|ให้).{0,12}(?:ฉีด|กิน|ทาน|หยุด|เพิ่ม|ลด)(?:ยา|อินซูลิน).{0,20}(?:กี่|เท่าไร|เท่าไหร่|ไหม|หรือไม่)"),
    re.compile(r"(?:ฉีด|กิน)(?:ยา)?.{0,15}กี่หน่วย.{0,15}" + _FIRST_PERSON),
    re.compile(r"\bprescribe\b", re.I),
    re.compile(r"\bdiagnose\s+(?:me|my|him|her)\b", re.I),
    re.compile(r"\bhow (?:many|much)\b.{0,40}\bshould I (?:take|inject|use)\b", re.I),
]
_EMERGENCY_SYMPTOM = re.compile(r"เจ็บหน้าอก|หายใจไม่ออก|หมดสติ|ไม่รู้สึกตัว|ชักเกร็ง|แขนขาอ่อนแรง|ปากเบี้ยว|พูดไม่ชัด|ซึมลง|ใจสั่นมาก")
_URGENT = re.compile(r"ตอนนี้|เดี๋ยวนี้|กำลัง|เมื่อกี้|ฉุกเฉิน|ด่วน")


def thai_id_valid(digits: str) -> bool:
    """13 digits whose last digit is the Thai national ID check digit."""
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(int(digits[i]) * (13 - i) for i in range(12))
    return (11 - total % 11) % 10 == int(digits[12])


def _block(category: str, reason: str, message: str) -> Verdict:
    return {"block": True, "category": category, "reason": reason, "message": message}


def pii_guard(question: str) -> Verdict | None:
    for m in _ID_CANDIDATE.finditer(question):
        if thai_id_valid(re.sub(r"\D", "", m.group())):
            return _block("pii_national_id", "valid Thai national ID", PII_MESSAGE.format(what="เลขบัตรประชาชน"))
    if _PHONE.search(question):
        return _block("pii_phone", "phone number", PII_MESSAGE.format(what="เบอร์โทรศัพท์"))
    if _EMAIL.search(question):
        return _block("pii_email", "e-mail address", PII_MESSAGE.format(what="อีเมล"))
    if _HN.search(question):
        return _block("pii_hn", "hospital number", PII_MESSAGE.format(what="เลขผู้ป่วย HN/AN"))
    if _NAME.search(question):
        return _block("pii_name", "title + first name + surname", PII_MESSAGE.format(what="ชื่อ-นามสกุล"))
    return None


def scope_guard(question: str) -> Verdict | None:
    if _EMERGENCY_SYMPTOM.search(question) and _URGENT.search(question):
        return _block("emergency", "acute symptom with urgency words", EMERGENCY_MESSAGE)
    if any(p.search(question) for p in _DIRECTIVE):
        return _block("individual_directive", "asks the system to prescribe, dose or diagnose for a person", CLINICIAN_MESSAGE)
    return None


def default_guards() -> list:
    """Order matters: personal data first (nothing else should look at it), then scope."""
    return [pii_guard, scope_guard]


def mask_pii(question: str) -> tuple[str, list[str]]:
    """G1 option B (owner's choice, 2026-10-12): replace personal identifiers with a placeholder and answer the rest. Returns (masked question, categories found);
    the matched text itself is never kept or logged. Same detectors as pii_guard (valid national ID, phone, e-mail, HN/AN, title + first name + surname); a number that is
    only a lab value or an age passes untouched. Limit: a Thai name without a title is not found, and masking does not make the remaining health details anonymous."""
    found: list[str] = []
    out = question

    def sub(rx, label, cat, check=None):
        nonlocal out
        def repl(m):
            if check and not check(m.group()):
                return m.group()
            if cat not in found:
                found.append(cat)
            return label
        out = rx.sub(repl, out)

    sub(_ID_CANDIDATE, "[เลขบัตรประชาชน]", "national_id", lambda t: thai_id_valid(re.sub(r"\D", "", t)))
    sub(_PHONE, "[เบอร์โทร]", "phone")
    sub(_EMAIL, "[อีเมล]", "email")
    sub(_HN, "[เลขผู้ป่วย]", "hn")
    sub(_NAME, "[ชื่อบุคคล]", "name")
    return out, found


class MaskingPipeline:
    """Masks personal identifiers (G1 = B) before any retrieval or LLM call, then runs the inner pipeline on the masked question. The original text is not passed on, not stored
    in the result and not logged; the result's trace records only the categories that were masked."""

    def __init__(self, inner):
        self.inner = inner
        self.config_id = getattr(inner, "config_id", "") + "+mask"

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def answer(self, question: str, retrieved=None) -> dict:
        masked, cats = mask_pii(question)
        result = self.inner.answer(masked, retrieved=retrieved)
        result["question"] = masked
        if cats:
            result.setdefault("trace", {})["pii_masked"] = cats
        return result


def demo_guards() -> list:
    """G1 = B and G3 as chosen: personal data is masked (MaskingPipeline), so only the scope guard blocks. `default_guards()` (block on personal data) is kept because the earlier
    evaluations used it."""
    return [scope_guard]
