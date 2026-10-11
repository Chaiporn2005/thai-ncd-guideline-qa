"""Input guards: personal data and scope. Rules only, no model, no network."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.rag import guards  # noqa: E402


def make_id(first12: str) -> str:
    total = sum(int(first12[i]) * (13 - i) for i in range(12))
    return first12 + str((11 - total % 11) % 10)


class Pii(unittest.TestCase):
    def test_valid_national_id_is_blocked_with_or_without_separators(self):
        n = make_id("110170020345")
        self.assertTrue(guards.thai_id_valid(n))
        for text in (f"เลขบัตร {n} เป็นเบาหวานไหม", f"{n[0]}-{n[1:5]}-{n[5:10]}-{n[10:12]}-{n[12]}"):
            self.assertEqual(guards.pii_guard(text)["category"], "pii_national_id")

    def test_a_13_digit_number_with_a_wrong_check_digit_is_not_an_id(self):
        n = make_id("110170020345")
        bad = n[:12] + str((int(n[12]) + 1) % 10)
        self.assertIsNone(guards.pii_guard(f"รหัสอ้างอิง {bad}"))

    def test_phone_email_hn_and_name(self):
        self.assertEqual(guards.pii_guard("โทร 081-234-5678 ได้ไหม")["category"], "pii_phone")
        self.assertEqual(guards.pii_guard("ติดต่อ somchai@example.com")["category"], "pii_email")
        self.assertEqual(guards.pii_guard("ผู้ป่วย HN 1234567 ควรกินยาอะไร")["category"], "pii_hn")
        self.assertEqual(guards.pii_guard("นายสมชาย ใจดี เป็นเบาหวาน")["category"], "pii_name")

    def test_the_matched_text_is_never_echoed(self):
        n = make_id("110170020345")
        v = guards.pii_guard(f"{n} เบาหวาน")
        self.assertNotIn(n, json_text(v))

    def test_health_numbers_alone_pass(self):
        for text in ("HbA1c 8.2 สูงไหมตามแนวทาง", "ผู้ใหญ่อายุ 55 ปี ความดัน 150/95 ตามแนวทางจัดเป็นระดับไหน", "ค่า eGFR 38 อยู่ระยะใดของโรคไตเรื้อรัง"):
            self.assertIsNone(guards.pii_guard(text))


def json_text(v):
    import json
    return json.dumps(v, ensure_ascii=False)


class Scope(unittest.TestCase):
    def test_individual_directives_are_refused(self):
        for text in ("ผมเป็นเบาหวาน ช่วยสั่งยาอินซูลินให้ผมว่าคืนนี้ฉีดกี่หน่วย", "ช่วยวินิจฉัยฉันหน่อย ฉันเป็นโรคอะไร", "Please prescribe insulin for my father",
                     "Can you diagnose me from these symptoms", "ผมควรเพิ่มยาเมตฟอร์มินเป็นกี่เม็ดดี"):
            v = guards.scope_guard(text)
            self.assertTrue(v and v["category"] == "individual_directive", text)

    def test_general_knowledge_questions_pass(self):
        for text in ("แนวทางแนะนำให้เริ่มยาอินซูลินเมื่อใดในเบาหวานชนิดที่ 2", "ขนาดยา metformin เริ่มต้นสำหรับผู้ใหญ่ตามแนวทางคือเท่าไร",
                     "ผู้ป่วยโรคไตเรื้อรังระยะ 4 ควรจำกัดโซเดียมวันละกี่มิลลิกรัม", "อาการเจ็บหน้าอกจากโรคหลอดเลือดหัวใจแตกต่างจากกรดไหลย้อนอย่างไร",
                     "What does the guideline say about statin use in the elderly"):
            self.assertIsNone(guards.scope_guard(text), text)

    def test_emergency_needs_a_symptom_and_urgency(self):
        v = guards.scope_guard("แม่ผมเจ็บหน้าอกอยู่ตอนนี้ต้องทำอย่างไร")
        self.assertEqual(v["category"], "emergency")
        self.assertIn("1669", v["message"])
        self.assertIsNone(guards.scope_guard("อาการเจ็บหน้าอกพบได้ในโรคใดบ้าง"))


class Chain(unittest.TestCase):
    def test_pii_is_checked_before_scope_and_the_pipeline_contract_holds(self):
        n = make_id("110170020345")
        first = next(v for v in (g(f"ช่วยสั่งยาให้ผม บัตร {n}") for g in guards.default_guards()) if v)
        self.assertEqual(first["category"], "pii_national_id")
        self.assertTrue(all(first.get(k) for k in ("block", "category", "reason", "message")))


if __name__ == "__main__":
    unittest.main()
