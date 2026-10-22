"""Mechanical checks on agent-drafted questions."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("vsq", Path(__file__).resolve().parents[2] / "scripts/validate_silver_questions.py")
vsq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vsq)

PAGE = "ผู้ป่วยเบาหวานชนิดที่ 2 ควรมีเป้าหมายระดับน้ำตาลสะสม HbA1c น้อยกว่า 7 เปอร์เซ็นต์ ในผู้ใหญ่ส่วนใหญ่"
TEXTS = {("d", 5): PAGE}
FRAME = {"frame_id": "f001"}


def draft(**kw):
    base = {"frame_id": "f001", "question": "เป้าหมายค่าน้ำตาลสะสมของคนเป็นเบาหวานชนิดสองควรเท่าไร", "answer": "ต่ำกว่า 7%",
            "type": "number_unit", "answerable": True,
            "evidence": [{"document_id": "d", "pdf_page": 5, "quote": "HbA1c น้อยกว่า 7 เปอร์เซ็นต์ ในผู้ใหญ่"}]}
    base.update(kw)
    return base


class Silver(unittest.TestCase):
    def problems(self, **kw):
        return vsq.check(draft(**kw), FRAME, TEXTS)

    def test_clean_draft_passes(self):
        self.assertEqual(self.problems(), [])

    def test_quote_must_be_exact_and_long_enough(self):
        self.assertTrue(any("exact substring" in p for p in self.problems(
            evidence=[{"document_id": "d", "pdf_page": 5, "quote": "HbA1c ต่ำกว่า 7 เปอร์เซ็นต์ในผู้ใหญ่ส่วนใหญ่"}])))
        self.assertTrue(any("length" in p for p in self.problems(
            evidence=[{"document_id": "d", "pdf_page": 5, "quote": "HbA1c"}])))

    def test_copying_the_page_is_a_lexical_leak(self):
        self.assertTrue(any("shares" in p for p in self.problems(question="ผู้ป่วยเบาหวานชนิดที่ 2 ควรมีเป้าหมายระดับน้ำตาลสะสม HbA1c เท่าไร")))

    def test_references_and_contacts_are_rejected(self):
        self.assertTrue(any("refers" in p for p in self.problems(question="ตามตารางนี้ ค่าเป้าหมายคือเท่าไร")))
        self.assertTrue(any("phone" in p for p in self.problems(answer="โทร 081-234-5678")))

    def test_garbled_thai_is_rejected(self):
        self.assertTrue(any("garbled" in p for p in self.problems(question="???????????? ESA ???????")))

    def test_unanswerable_needs_null_answer_and_false_flag(self):
        self.assertEqual(self.problems(type="unanswerable", answerable=False, answer=None), [])
        self.assertTrue(self.problems(type="unanswerable", answerable=True))

    def test_multi_page_needs_two_evidence_pages(self):
        self.assertTrue(any("needs 2" in p for p in self.problems(type="multi_page")))


if __name__ == "__main__":
    unittest.main()
