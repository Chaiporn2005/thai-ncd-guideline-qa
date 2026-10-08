"""OCR proposal validation: coverage, unique matches and verdict contracts."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "validate_ocr_proposals", Path(__file__).resolve().parents[1] / "scripts/validate_ocr_proposals.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

PAGE = {"key": "d:p1", "document_id": "d", "pdf_page": 1, "group": "g", "image": "img/a.png"}
TEXT = {"d:p1": "FPG > 126 มก./ดล. และ HbA1c > 6.5 และ HbA1c"}


def result(**over):
    row = {"key": "d:p1", "group": "g", "verdict": "fixed", "missing": "", "notes": "", "zoom_used": False,
           "edits": [{"old": "FPG > 126", "new": "FPG ≥ 126", "kind": "sign", "confidence": "high",
                      "evidence": "image shows ≥", "occurrences": 1}]}
    row.update(over)
    return row


class Validate(unittest.TestCase):
    def errors(self, row, pages=None):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "img").mkdir()
            (root / "img/a.png").write_bytes(b"x")
            return tool.check(pages or [PAGE], [row], TEXT, root)

    def test_valid_result_passes(self):
        self.assertEqual(self.errors(result()), [])

    def test_old_text_must_occur_exactly_once(self):
        row = result()
        row["edits"][0]["old"] = "HbA1c"
        self.assertTrue(any("occurs 2 times" in e for e in self.errors(row)))
        row["edits"][0]["old"] = "ไม่มีในหน้า"
        self.assertTrue(any("occurs 0 times" in e for e in self.errors(row)))

    def test_remove_edits_need_an_empty_new_text(self):
        row = result()
        row["edits"][0].update(kind="remove", new="x")
        self.assertTrue(any("remove edits" in e for e in self.errors(row)))

    def test_verdict_contracts(self):
        self.assertTrue(any("content_missing without" in e for e in self.errors(result(verdict="content_missing", edits=[]))))
        self.assertTrue(any("fixed must have edits" in e for e in self.errors(result(edits=[]))))
        self.assertTrue(any("unknown verdict" in e for e in self.errors(result(verdict="great"))))

    def test_missing_pages_are_reported(self):
        pages = [PAGE, dict(PAGE, key="d:p2")]
        self.assertTrue(any("do not match" in e for e in self.errors(result(), pages)))


if __name__ == "__main__":
    unittest.main()
