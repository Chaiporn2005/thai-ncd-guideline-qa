"""Guardrails added for the OWASP Top 10 for LLM Applications (2025) cases of the Track C harness (AI-suggested; the owner decides what ships, see docs/owasp_guardrails.md).

Where each guard sits and which OWASP risk it answers (details and the honest gaps are in docs/owasp_guardrails.md):
  input   injection_input_guard  LLM01 Prompt Injection: patterns of the well-known direct attacks (EN/TH). Weak by nature (a rephrased attack passes); a cheap first filter.
  input   length_guard           LLM10 Unbounded Consumption: a question longer than `max_chars` is refused before retrieval and before any LLM call.
  tool    GuardedRetriever       LLM06 Excessive Agency / LLM08 Vector weaknesses: what a search tool may take and give back: query length cap, the document filter must look like an id,
                                 chunks the scanner flagged are dropped before the model reads them.
  output  check_output           LLM05 Improper Output Handling (HTML, script, markdown image/link, URL not in the evidence), LLM07 System Prompt Leakage (our own prompt text in
                                 the answer), LLM02 Sensitive Information Disclosure (personal identifiers in the answer that are not in the evidence). An answer that violates is withheld, not repaired.
  wrap    GuardedPipeline        applies check_output to any pipeline (plain, LangGraph, ReAct) without changing the frozen pipelines.
Nothing here calls a model. Known limits are stated in the docs, not hidden: pattern guards miss rephrasings, a poisoned chunk that looks like normal guideline text passes every guard here.
"""

from __future__ import annotations

import re

from . import guards as g
from . import prompt as prompt_mod

MAX_QUESTION_CHARS = 800
MAX_QUERY_CHARS = 300
ANSWER_BLOCKED_MESSAGE = "ระบบไม่แสดงคำตอบนี้เพราะตรวจพบเนื้อหาที่ไม่ปลอดภัยในผลลัพธ์ (เช่น ลิงก์/โค้ด/ข้อมูลส่วนบุคคล/ข้อความภายในระบบ) กรุณาถามใหม่หรือปรึกษาแพทย์หรือเภสัชกร"
INPUT_BLOCKED_MESSAGE = "คำถามนี้มีรูปแบบที่คล้ายคำสั่งให้ระบบทำนอกขอบเขต ระบบตอบได้เฉพาะคำถามความรู้จากแนวทางเวชปฏิบัติ NCD กรุณาพิมพ์คำถามใหม่"
LENGTH_MESSAGE = "คำถามยาวเกินไป ({n} ตัวอักษร เกิน {m}) กรุณาสรุปให้สั้นลง"

_INJECTION_INPUT = [
    re.compile(r"\b(?:ignore|disregard|forget|override)\b.{0,30}\b(?:previous|prior|above|earlier|all|your)\b.{0,20}\b(?:instructions?|rules?|prompts?|guidelines?)\b", re.I | re.S),
    re.compile(r"\byou are now\b|\bdeveloper mode\b|\bjailbreak\b|\bDAN\b", re.I),
    re.compile(r"\b(?:reveal|show|print|repeat|display|translate)\b.{0,30}\b(?:system prompt|your (?:instructions|rules|prompt)|the words above|text above)\b", re.I | re.S),
    re.compile(r"\[\s*(?:system|developer|admin)[^\]]{0,20}\]|</?\s*(?:system|evidence|question|observation|instructions?)\s*>", re.I),
    re.compile(r"\bbase64\b.{0,40}\b(?:decode|do what)\b|\b(?:decode|do what)\b.{0,40}\bbase64\b", re.I | re.S),
    re.compile(r"(?:ละเว้น|เพิกเฉย|ไม่ต้องสนใจ|ลืม).{0,14}(?:คำสั่ง|กฎ|ข้อกำหนด|ที่ผ่านมา)"),
    re.compile(r"สมมติ(?:ว่า)?\s*(?:คุณ|เธอ|ตัวเอง).{0,20}(?:เป็น|คือ).{0,40}(?:ไม่มี(?:ข้อจำกัด|กฎ)|ทำได้ทุกอย่าง)"),
    re.compile(r"คำสั่งระบบ|พรอมต์ระบบ|system\s*prompt|โหมดนักพัฒนา|ข้อความที่อยู่ก่อนหน้านี้ทั้งหมด"),
]
_MARKUP = [
    ("html_tag", re.compile(r"<\s*/?\s*[a-zA-Z!][^>]{0,200}>")),
    ("markdown_image", re.compile(r"!\[[^\]]*\]\([^)]*\)")),
    ("script_scheme", re.compile(r"(?:javascript|vbscript|data)\s*:", re.I)),
    ("markdown_link", re.compile(r"\[[^\]]+\]\(\s*(?:https?:|//)[^)]*\)", re.I)),
]
_URL = re.compile(r"(?:https?://|www\.)[^\s)\]>\"'<]+", re.I)


def injection_input_guard(question: str) -> g.Verdict | None:
    if any(p.search(question) for p in _INJECTION_INPUT):
        return g._block("injection_pattern", "instruction-like text aimed at the system (known direct-attack pattern)", INPUT_BLOCKED_MESSAGE)
    return None


def length_guard(max_chars: int = MAX_QUESTION_CHARS):
    def guard(question: str) -> g.Verdict | None:
        if len(question) > max_chars:
            return g._block("input_too_long", f"{len(question)} characters", LENGTH_MESSAGE.format(n=len(question), m=max_chars))
        return None
    return guard


def owasp_input_guards() -> list:
    """Order: length first (cheapest, bounds the work every later guard does), then the existing personal-data and scope guards, then injection patterns."""
    return [length_guard(), *g.default_guards(), injection_input_guard]


def _pii_spans(text: str) -> list[str]:
    spans = [m.group() for m in g._ID_CANDIDATE.finditer(text) if g.thai_id_valid(re.sub(r"\D", "", m.group()))]
    for rx in (g._PHONE, g._EMAIL, g._HN, g._NAME):
        spans += [m.group() for m in rx.finditer(text)]
    return spans


def _norm(s: str) -> str:
    return re.sub(r"[\s-]", "", s)


def check_output(answer: str, evidence_text: str = "") -> dict | None:
    """None when the answer may be shown, else {"category", "owasp", "reason"}. `evidence_text`: the chunks the answer may legitimately repeat (a URL or number that is in
    the guideline itself is fine; one that only the model produced is not)."""
    if not answer:
        return None
    for name, rx in _MARKUP:
        m = rx.search(answer)
        if m and m.group() not in evidence_text:
            return {"category": f"markup:{name}", "owasp": "LLM05", "reason": "active content or markup in the answer"}
    for m in _URL.finditer(answer):
        if m.group().rstrip(".,") not in evidence_text:
            return {"category": "url_not_in_evidence", "owasp": "LLM05", "reason": "a link the evidence does not contain"}
    if any(marker in answer for marker in (prompt_mod.SYSTEM_BASE[:30], prompt_mod.RULES[:25], "(1) ตอบจากหลักฐาน S")):
        return {"category": "system_prompt_leak", "owasp": "LLM07", "reason": "text of the system prompt in the answer"}
    ev = _norm(evidence_text)
    for span in _pii_spans(answer):
        if _norm(span) not in ev:
            return {"category": "pii_in_answer", "owasp": "LLM02", "reason": "a personal identifier the evidence does not contain"}
    return None


class GuardedRetriever:
    """Wraps a retriever for the tools of an agent (and for the plain pipeline): search keeps the interface `search(query, variant, k, filters)`."""

    def __init__(self, inner, max_query_chars: int = MAX_QUERY_CHARS, drop_flagged: bool = True):
        self.inner, self.max_query_chars, self.drop_flagged = inner, max_query_chars, drop_flagged
        self.dropped = 0

    def search(self, query: str, variant: str, k: int, filters: dict | None = None) -> list[dict]:
        doc = (filters or {}).get("document_id")
        if doc is not None and not re.fullmatch(r"[A-Za-z0-9_.\-]{1,80}", str(doc)):
            filters = None                                    # a document filter must look like an id; anything else is ignored, not obeyed
        hits = self.inner.search(query[:self.max_query_chars], variant, k, filters)
        if self.drop_flagged:
            kept = [h for h in hits if not h.get("injection_flags")]
            self.dropped += len(hits) - len(kept)
            hits = [{**h, "rank": i} for i, h in enumerate(kept, 1)]
        return hits


class GuardedPipeline:
    """Output guard around any pipeline with `answer(question, retrieved=None) -> dict`. `evidence_text()` returns the clean text of the chunks of the current question."""

    def __init__(self, inner, evidence_text=lambda: ""):
        self.inner, self.evidence_text = inner, evidence_text
        self.config_id = getattr(inner, "config_id", "") + "+owasp"

    def answer(self, question: str, retrieved: list[dict] | None = None) -> dict:
        result = self.inner.answer(question, retrieved=retrieved)
        if result.get("status") != "answered":
            return result
        verdict = check_output(result.get("answer") or "", self.evidence_text())
        if verdict:
            result = {**result, "status": "blocked_output", "answer": None, "citations": [], "output_guard": {**verdict, "message": ANSWER_BLOCKED_MESSAGE}}
        return result
