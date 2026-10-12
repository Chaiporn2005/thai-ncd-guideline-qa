import json
import unittest

from ncdqa.rag import demo_support


class DemoSupport(unittest.TestCase):
    def test_check_environment_rows_have_the_fields_a_user_needs(self):
        rows = demo_support.check_environment()
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(set(r), {"name", "ok", "detail", "fix"})
            if not r["ok"]:
                self.assertTrue(r["fix"], f'{r["name"]} fails without telling the user how to fix it')
        text = demo_support.render_check(rows)
        self.assertNotIn("TYPHOON_API_KEY=", text.replace("TYPHOON_API_KEY=` ", ""))       # the key's value is never printed

    def test_showcase_file_is_well_formed(self):
        items = demo_support.load_showcase()
        self.assertGreaterEqual(len(items), 8)
        for s in items:
            self.assertTrue(s["label"] and s["question"] and s["expect"])
        json.dumps(items, ensure_ascii=False)

    def test_serialize_never_returns_the_raw_input_and_handles_each_status(self):
        units = {"c1": {"document_id": "d", "pdf_page_start": 3, "pdf_page_end": 4, "text": "ข้อความหลักฐาน" * 100}}
        answered = {"status": "answered", "answer": "a [S1]", "question": "masked question", "citations": [{"id": "S1"}],
                    "trace": {"evidence": {"S1": "c1"}, "pii_masked": ["phone"], "usage": {"total_tokens": 5}, "dropped_claims": [{"reason": "r"}]}}
        out = demo_support.serialize(answered, units)
        self.assertEqual(out["masked"], ["phone"])
        self.assertEqual(out["evidence"][0]["pages"], "3-4")
        self.assertLessEqual(len(out["evidence"][0]["text"]), 700)
        refused = {"status": "refused_input", "answer": None, "citations": [], "trace": {"guard": {"category": "injection_pattern", "message": "m"}}}
        self.assertEqual(demo_support.serialize(refused)["guard"]["category"], "injection_pattern")
        blocked = {"status": "blocked_output", "answer": None, "citations": [], "output_guard": {"category": "x", "message": "m"}, "trace": {}}
        self.assertEqual(demo_support.serialize(blocked)["output_guard"]["message"], "m")


if __name__ == "__main__":
    unittest.main()
