"""Prompts and output checks for LLM query rewriting / expansion (Track B, optional step before retrieval).

Three modes, each from the literature, so the comparison says which idea helps here:
* rewrite   few-shot rewrite of a colloquial question into the formal wording of guidelines (the problem to solve: users ask in
            everyday Thai, the guidelines are written formally). Output replaces the query.
* hyde      zero-shot hypothetical answer passage (HyDE, Gao et al. 2022, arXiv 2212.10496). The passage may contain mistakes; the
            retriever only uses its words/embedding, never shows it to the user.
* q2d       few-shot pseudo-passage appended to the original query (query2doc, Wang et al. 2023, arXiv 2303.07678: 4 few-shot
            examples, one passage per query; dense input = query [SEP] passage; BM25 input = the query repeated 5 times, then the
            passage, "n=5 is a generally good value" (their words)). `Q2D_QUERY_REPEATS` and `Q2D_SHOTS_PAPER` record those numbers.
The few-shot examples below are generic public-health wording written for this module, not taken from the corpus or from any
dev/test question (`examples_overlap` checks that against a question file).

Safeguards: a question that carries an e-mail, a phone number or a 13-digit id is never sent to a model; a rewrite must keep every
number and Latin term of the original (otherwise the original is used); outputs are cut to a length limit and stripped of markup.
"""

from __future__ import annotations

import re

SYSTEM = {
    "rewrite": ("คุณช่วยเตรียมคำค้นสำหรับระบบค้นหาแนวทางเวชปฏิบัติโรคไม่ติดต่อเรื้อรังของไทย (เบาหวาน ความดันโลหิตสูง ไขมันในเลือด โรคไต) "
                "หน้าที่: เขียนคำถามของผู้ใช้ใหม่ให้เป็นภาษาทางการที่เอกสารแนวทางน่าจะใช้ โดยคงความหมายเดิมทุกอย่าง "
                "กติกา: คงตัวเลข หน่วย ชื่อยา ชื่อการตรวจ และคำอังกฤษเดิมไว้ครบ; ใส่ศัพท์อังกฤษทางการแพทย์ในวงเล็บได้ถ้าแน่ใจ; "
                "ห้ามเพิ่มข้อเท็จจริง ตัวเลข หรือโรคที่คำถามไม่ได้พูดถึง; ตอบเป็นประโยคเดียวภาษาไทย ไม่เกิน 150 ตัวอักษร ไม่มีคำอธิบายอื่น"),
    "hyde": ("คุณเป็นผู้ช่วยเขียนข้อความตัวอย่างสำหรับระบบค้นหาแนวทางเวชปฏิบัติโรคไม่ติดต่อเรื้อรังของไทย "
             "หน้าที่: เขียนย่อหน้าสั้น ๆ (ไม่เกิน 3 ประโยค ไม่เกิน 350 ตัวอักษร) ในน้ำเสียงของเอกสารแนวทางเวชปฏิบัติภาษาไทย ที่ตอบคำถามที่ให้ "
             "ถ้าไม่แน่ใจตัวเลขให้เขียนโดยไม่ระบุตัวเลข ห้ามใส่หัวข้อ รายการ หรือคำอธิบายนอกย่อหน้า"),
    "q2d": ("คุณเป็นผู้ช่วยเขียนข้อความตัวอย่างสำหรับระบบค้นหาแนวทางเวชปฏิบัติโรคไม่ติดต่อเรื้อรังของไทย "
            "หน้าที่: เขียนย่อหน้าสั้น ๆ (ไม่เกิน 2 ประโยค ไม่เกิน 300 ตัวอักษร) ที่เอกสารแนวทางน่าจะมีและตอบคำถามที่ให้ "
            "ใช้ศัพท์ทางการและเขียนเฉพาะสิ่งที่แน่ใจ ไม่ใส่ตัวเลขถ้าไม่แน่ใจ ไม่มีหัวข้อหรือรายการ"),
}

SHOTS = {
    "rewrite": [
        ("น้ำตาลต่ำต้องทำไง", "แนวทางการจัดการภาวะน้ำตาลในเลือดต่ำ (hypoglycemia) ในผู้ป่วยเบาหวาน"),
        ("กินเค็มมากไปเป็นอะไรไหม", "ผลเสียต่อสุขภาพจากการบริโภคโซเดียมมากเกินไป"),
        ("ไปหาหมอบ่อยแค่ไหนถ้าเป็นความดันสูง", "ความถี่ในการติดตามการรักษาของผู้ป่วยความดันโลหิตสูง"),
    ],
    "q2d": [
        ("ผักผลไม้วันละเท่าไหร่ดี", "คำแนะนำด้านโภชนาการกำหนดปริมาณผักและผลไม้ที่ควรบริโภคต่อวันเพื่อลดความเสี่ยงโรคไม่ติดต่อเรื้อรัง "
                                     "โดยแนะนำให้เลือกบริโภคผักและผลไม้ที่หลากหลายชนิดทุกวัน"),
        ("เบาหวานต้องตรวจเท้าไหม", "ผู้ป่วยเบาหวานควรได้รับการตรวจเท้าอย่างน้อยปีละครั้งเพื่อค้นหาปัจจัยเสี่ยงต่อการเกิดแผลที่เท้า "
                                    "และควรได้รับคำแนะนำการดูแลเท้าด้วยตนเอง"),
        ("วัดความดันที่บ้านควรทำตอนไหน", "การวัดความดันโลหิตที่บ้านควรวัดในท่านั่งหลังพักอย่างน้อยห้านาที "
                                         "และควรบันทึกค่าที่วัดได้เพื่อให้แพทย์ใช้ประกอบการปรับการรักษา"),
        ("ออกกำลังกายอะไรดีสำหรับคนเป็นโรคเรื้อรัง", "ผู้ป่วยโรคไม่ติดต่อเรื้อรังควรได้รับคำแนะนำให้ออกกำลังกายระดับปานกลางอย่างสม่ำเสมอ "
                                                       "โดยเลือกกิจกรรมที่เหมาะกับสภาพร่างกายและโรคประจำตัวของแต่ละบุคคล"),
    ],
}

PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b0\d{1,2}[- ]?\d{3}[- ]?\d{3,4}\b|\b\d{13}\b|\b\d{1}-\d{4}-\d{5}-\d{2}-\d\b")
KEEP_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[A-Za-z][A-Za-z0-9\-]+")
LIMITS = {"rewrite": 200, "hyde": 450, "q2d": 400}
REFUSAL = re.compile(r"ไม่เกี่ยวข้อง|ไม่สามารถ(?:ตอบ|ให้|เขียน)|ขออภัย|ไม่มีข้อมูล|ขอโทษ|I cannot|I can't|Sorry", re.I)


def messages(mode: str, question: str) -> list[dict]:
    out = [{"role": "system", "content": SYSTEM[mode]}]
    for q, a in SHOTS.get(mode, []):
        out += [{"role": "user", "content": f"คำถาม: {q}"}, {"role": "assistant", "content": a}]
    out.append({"role": "user", "content": f"คำถาม: {question}"})
    return out


def sendable(question: str) -> bool:
    """False when the question carries personal identifiers: it must not leave the machine."""
    return not PERSONAL.search(question)


def clean(text: str, mode: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^[\s\"'“”`*#>\-•\d.)]+", "", text.splitlines()[0] if mode == "rewrite" and text.strip() else text)
    text = re.sub(r"[*`#]+", "", text)
    text = re.sub(r"\s+", " ", text).strip().strip("\"'“”")
    return text[: LIMITS[mode]]


def preserves(original: str, rewritten: str) -> bool:
    """Every number and Latin term of the original appears in the rewrite (case-insensitive)."""
    low = rewritten.lower()
    return all(tok.lower() in low for tok in KEEP_TOKEN.findall(original))


def finalize(mode: str, original: str, raw: str | None) -> tuple[str, str]:
    """(query text to use, status). Status: ok | no_output | refusal | dropped_numbers | not_sent."""
    if raw is None:
        return original, "not_sent"
    text = clean(raw, mode)
    if not text:
        return original, "no_output"
    if REFUSAL.search(text):  # a refusal or an off-topic remark is not a rewrite
        return original, "refusal"
    if mode == "rewrite" and not preserves(original, text):
        return original, "dropped_numbers"
    return text, "ok"


def examples_overlap(questions: list[str], run: int = 20) -> list[str]:
    """Few-shot example texts that share a run of `run` characters with any question (should be empty)."""
    from difflib import SequenceMatcher
    shots = [t for pairs in SHOTS.values() for pair in pairs for t in pair]
    hits = []
    for s in shots:
        for q in questions:
            if SequenceMatcher(None, s, q, autojunk=False).find_longest_match(0, len(s), 0, len(q)).size >= run:
                hits.append(s)
                break
    return hits

Q2D_QUERY_REPEATS = 5   # Wang et al. 2023: BM25 query = original query x5 + pseudo-passage
Q2D_SHOTS_PAPER = 4     # Wang et al. 2023: k = 4 in-context examples
