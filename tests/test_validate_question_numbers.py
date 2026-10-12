import json
import unittest

from ncdqa.rag.validate import validate

EVIDENCE = {"S1": {"text": "ปรับลดขนาดยา metformin เมื่อ eGFR น้อยกว่า 45 มล./นาที"}}


def raw(text):
    return json.dumps({"abstain": False, "claims": [{"text": text, "cite": ["S1"]}]}, ensure_ascii=False)


class QuestionNumbers(unittest.TestCase):
    def test_number_from_the_question_is_allowed_only_with_the_option(self):
        claim = raw("ผู้ป่วยระยะ 3 ปรับลดขนาดยาเมื่อ eGFR น้อยกว่า 45")
        self.assertEqual(len(validate(claim, EVIDENCE).kept), 0)
        self.assertEqual(len(validate(claim, EVIDENCE, question="ระยะ 3 ใช้ยาขนาดเท่าไร").kept), 1)

    def test_a_number_that_is_neither_in_the_evidence_nor_the_question_is_still_dropped(self):
        claim = raw("ผู้ป่วยระยะ 3 ปรับลดขนาดยาเหลือ 500 มก.")
        v = validate(claim, EVIDENCE, question="ระยะ 3 ใช้ยาขนาดเท่าไร")
        self.assertEqual(v.kept, [])
        self.assertIn("500", v.dropped[0]["reason"])


if __name__ == "__main__":
    unittest.main()
