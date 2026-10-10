"""Lenient relevance: unit spelling, numeric anchors, answer match, alt_evidence and that strict scores do not move."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ncdqa.retrieval import answer_match as am  # noqa: E402
from ncdqa.retrieval import evaluate as ev  # noqa: E402


def unit(cid, page, text, edition="e1", doc="d"):
    return {"chunk_id": cid, "document_id": doc, "edition_id": edition, "pdf_page_start": page, "pdf_page_end": page, "text": text}


QUESTION = "คนเป็นเบาหวานเจาะนิ้วแล้วได้ค่าน้ำตาลต่ำกว่าเท่าไรจึงเข้าข่ายน้ำตาลตก"
ANSWER = "ต่ำกว่า 70 มิลลิกรัม/เดซิลิตร"
GOLD = {"document_id": "d", "edition_id": "e1", "pdf_page": 1, "quote": "ระดับน้ำตาลในเลือดจากปลายนิ้ว มีค่าต่ำกว่า 70 มิลลิกรัม/เดซิลิตร"}
OTHER_DOC = unit("o", 9, "น้ำตาลในเลือดต่ำของผู้เป็นเบาหวานคือต่ำกว่า 70 มก./ดล. (3.9 mmol/L) ซึ่งเจาะปลายนิ้วตรวจได้", doc="x", edition="x1")
UNRELATED = unit("u", 3, "ความดันโลหิตสูง 70 มก./ดล. ไม่เกี่ยวกับน้ำตาล เรื่องเกลือโซเดียมและไตทั้งหมด", doc="y", edition="y1")
FILLER = ["น้ำตาลในเลือด เบาหวาน ผู้ป่วย เจาะนิ้ว", "ความดันโลหิตสูง เกลือ โซเดียม ไต", "ไขมันในเลือด คอเลสเตอรอล", OTHER_DOC["text"], UNRELATED["text"]]


class Units(unittest.TestCase):
    def test_spelling_variants_become_one_unit(self):
        for variant in ("70 มก./ดล.", "70 มก/ดล", "70 มิลลิกรัม/เดซิลิตร", "70 mg/dL", "๗๐ มิลลิกรัมต่อเดซิลิตร"):
            self.assertEqual(am.normalize(variant), "70mg/dl", variant)
        self.assertEqual(am.normalize("ร้อยละ 80"), "80%")
        self.assertEqual(am.normalize("1,350 มิลลิกรัม"), "1350mg")

    def test_anchors_ignore_weak_numbers_and_years(self):
        self.assertEqual([(a.number, a.unit) for a in am.anchors(ANSWER)], [("70", "mg/dl")])
        self.assertEqual(am.anchors("วันละ 3 ครั้ง")[0].unit, "ครั้ง")  # a single digit counts only with a unit
        self.assertEqual(am.anchors("ทำ 3 อย่าง"), [])
        self.assertEqual(am.anchors("ปี 2565"), [])
        self.assertEqual(am.anchors("ผู้ป่วยเบาหวาน"), [])
        self.assertEqual(am.anchors(None), [])


class Matcher(unittest.TestCase):
    def setUp(self):
        self.matcher = am.AnswerMatcher(FILLER * 3, min_overlap=0.1)

    def test_same_fact_in_other_document_matches(self):
        self.assertTrue(self.matcher.matches(ANSWER, QUESTION, OTHER_DOC["text"]))

    def test_number_alone_is_not_enough(self):
        self.assertFalse(self.matcher.matches(ANSWER, QUESTION, UNRELATED["text"]))

    def test_answer_without_a_number_never_matches(self):
        self.assertFalse(self.matcher.matches("ควรกินยาหลังอาหาร", QUESTION, OTHER_DOC["text"]))

    def test_number_must_come_with_its_unit(self):
        self.assertFalse(self.matcher.matches(ANSWER, QUESTION, "น้ำตาลเบาหวานเจาะนิ้ว 70 กรัม"))


class Lenient(unittest.TestCase):
    def setUp(self):
        self.matcher = am.AnswerMatcher(FILLER * 3, min_overlap=0.1)
        self.q = {"qid": "q1", "question": QUESTION, "answer": ANSWER, "evidence": [GOLD]}
        self.gold_unit = unit("g", 1, "ระดับน้ำตาลในเลือดจากปลายนิ้ว มีค่าต่ำกว่า 70 มิลลิกรัม/เดซิลิตร")

    def test_strict_is_unchanged_and_lenient_never_lower(self):
        ranked = [UNRELATED, OTHER_DOC, self.gold_unit]
        strict = ev.score_question(ranked, [GOLD], [1, 3])
        lenient = ev.score_lenient(ranked, self.q, [1, 3], self.matcher)
        self.assertEqual(strict["recall@1"], 0.0)
        self.assertEqual(strict["recall@3"], 1.0)
        self.assertEqual(lenient["lenient_recall@1"], 0.0)  # rank 1 is the unrelated chunk
        for key, value in strict.items():
            self.assertGreaterEqual(lenient["lenient_" + key], value, key)

    def test_answer_match_rescues_a_correct_chunk_from_another_document(self):
        ranked = [OTHER_DOC, UNRELATED]
        self.assertEqual(ev.score_question(ranked, [GOLD], [1])["recall@1"], 0.0)
        lenient = ev.score_lenient(ranked, self.q, [1, 3], self.matcher)
        self.assertEqual(lenient["lenient_recall@1"], 1.0)
        self.assertEqual(lenient["lenient_mrr@3"], 1.0)

    def test_alt_evidence_counts_without_an_answer_match(self):
        alt_unit = unit("a", 4, "ข้อความที่ซ้ำกับหลักฐานทุกตัวอักษร ระดับน้ำตาลในเลือดจากปลายนิ้ว มีค่าต่ำกว่า 70 มิลลิกรัม/เดซิลิตร", doc="z", edition="z1")
        alt = {"document_id": "z", "edition_id": "z1", "pdf_page": 4, "quote": GOLD["quote"], "kind": "duplicate"}
        q = {**self.q, "answer": "ตามที่กำหนด", "alt_evidence": [alt]}
        self.assertEqual(ev.score_lenient([alt_unit], q, [1], self.matcher)["lenient_recall@1"], 1.0)
        self.assertEqual(ev.score_lenient([alt_unit], self.q | {"answer": "ตามที่กำหนด"}, [1], self.matcher)["lenient_recall@1"], 0.0)

    def test_multi_page_question_gets_no_extra_credit(self):
        e2 = {**GOLD, "pdf_page": 2, "quote": "ข้อความหน้าที่สองของเอกสาร"}
        q = {**self.q, "evidence": [GOLD, e2]}
        lenient = ev.score_lenient([OTHER_DOC, self.gold_unit], q, [3], self.matcher)
        self.assertEqual(lenient["lenient_recall@3"], 0.5)  # only the first page is covered; OTHER_DOC does not help


if __name__ == "__main__":
    unittest.main()
