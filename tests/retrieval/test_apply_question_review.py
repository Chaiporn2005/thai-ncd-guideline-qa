"""Applying reviewers' decisions to silver questions."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("aqr", Path(__file__).resolve().parents[2] / "scripts/apply_question_review.py")
aqr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aqr)


def q(qid, answerable=True):
    return {"qid": qid, "split": "dev", "status": "silver", "question": "ถามอะไร", "answer": "ตอบ" if answerable else None,
            "type": "fact" if answerable else "unanswerable", "answerable": answerable, "evidence": [],
            "generated_by": "x", "reviewed_by": None, "review_date": None, "changes": None}


def export(*decisions, reviewer="เพื่อน", part="p"):
    return {"part_id": part, "reviewer": reviewer, "exported_at": "2026-10-11T08:00:00Z", "decisions": list(decisions)}


class Apply(unittest.TestCase):
    def test_accept_edit_reject_and_untouched(self):
        out, report = aqr.apply([q("q001"), q("q002"), q("q003"), q("q004")], [export(
            {"qid": "q001", "decision": "accept"},
            {"qid": "q002", "decision": "edit", "question": "ถามใหม่", "answer": "ตอบใหม่", "note": "คำตอบไม่ครบ"},
            {"qid": "q003", "decision": "reject", "note": "ไม่มีในหน้า"})])
        by = {r["qid"]: r for r in out}
        self.assertEqual((by["q001"]["status"], by["q001"]["reviewed_by"], by["q001"]["review_date"]), ("gold", "เพื่อน", "2026-10-11"))
        self.assertEqual((by["q002"]["status"], by["q002"]["question"], by["q002"]["answer"]), ("gold", "ถามใหม่", "ตอบใหม่"))
        self.assertIn("คำตอบไม่ครบ", by["q002"]["changes"])
        self.assertEqual(by["q003"]["status"], "rejected")
        self.assertEqual(by["q004"]["status"], "silver")
        self.assertEqual(report["still_silver"], ["q004"])

    def test_edit_or_reject_needs_a_note(self):
        with self.assertRaises(ValueError):
            aqr.apply([q("q001")], [export({"qid": "q001", "decision": "reject"})])

    def test_two_exports_deciding_one_question_stop_the_run(self):
        with self.assertRaises(ValueError):
            aqr.apply([q("q001")], [export({"qid": "q001", "decision": "accept"}), export({"qid": "q001", "decision": "accept"}, reviewer="อีกคน")])

    def test_answerable_edit_cannot_blank_the_answer(self):
        with self.assertRaises(ValueError):
            aqr.apply([q("q001")], [export({"qid": "q001", "decision": "edit", "answer": "", "note": "x"})])

    def test_unknown_question_and_missing_reviewer_are_refused(self):
        with self.assertRaises(ValueError):
            aqr.apply([q("q001")], [export({"qid": "q999", "decision": "accept"})])
        with self.assertRaises(ValueError):
            aqr.apply([q("q001")], [export({"qid": "q001", "decision": "accept"}, reviewer=" ")])


if __name__ == "__main__":
    unittest.main()
