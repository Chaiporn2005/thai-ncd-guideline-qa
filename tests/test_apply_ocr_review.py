"""OCR review application: corrections are exact, unknown text fails, rejects are never indexable."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "apply_ocr_review", Path(__file__).resolve().parents[1] / "scripts/apply_ocr_review.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class Corrections(unittest.TestCase):
    def test_replacements_truncate_append_and_cleanup(self):
        text = "1\\. วัดด้วยเครื่องตรวจอัตราการเต้นหัวใจ 70 มก./ตล.\n![](image_of_x)\nภาพกิจกรรม ดังนี้ ชื่อที่แต่งขึ้น"
        entry = {"key": "k", "replacements": [["เครื่องตรวจอัตราการเต้นหัวใจ", "เครื่องตรวจวัดระดับน้ำตาลปลายนิ้ว"],
                                              ["มก./ตล.", "มก./ดล."]],
                 "truncate_after": "ภาพกิจกรรม ดังนี้", "append": "\nเพิ่ม"}
        self.assertEqual(tool.apply_corrections(text, entry),
                         "1. วัดด้วยเครื่องตรวจวัดระดับน้ำตาลปลายนิ้ว 70 มก./ดล.\nภาพกิจกรรม ดังนี้\nเพิ่ม")

    def test_missing_replacement_text_fails(self):
        with self.assertRaises(tool.ReviewError):
            tool.apply_corrections("abc", {"key": "k", "replacements": [["xyz", "q"]]})

    def test_duplicate_block_removed_once(self):
        text = "## A\n\nP\n\n## B\n\nP\n\n## C"
        entry = {"key": "k", "remove_duplicate_block": {"start": "## B\n\nP", "end": "## C", "keep": "## B\n\n"}}
        self.assertEqual(tool.apply_corrections(text, entry), "## A\n\nP\n\n## B\n\n## C")


class Apply(unittest.TestCase):
    def make(self, root: Path, entries):
        doc = root / "src" / "doc-a"
        doc.mkdir(parents=True)
        rows = [{"document_id": "doc-a", "pdf_page": 1, "status": "ok", "text": "ปกติ", "human_review": None},
                {"document_id": "doc-a", "pdf_page": 2, "status": "ocr_unreviewed", "text": "จอดาบวม", "human_review": None},
                {"document_id": "doc-a", "pdf_page": 3, "status": "ocr_unreviewed", "text": "บันทึก", "human_review": None}]
        (doc / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        (doc / "normalization.json").write_text(json.dumps({"pages_jsonl_sha256": "x"}), encoding="utf-8")
        review = {"reviewer": "tester", "review_method": "ai_assisted_visual_check", "human_confirmation": None,
                  "pages": entries}
        (root / "review.json").write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

    def run_tool(self, root: Path):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return tool.main(["--source", str(root / "src"), "--review", str(root / "review.json"),
                              "--out", str(root / "out")])

    def test_fix_and_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root, [{"key": "doc-a:p2", "outcome": "fix", "replacements": [["จอดา", "จอตา"]]},
                             {"key": "doc-a:p3", "outcome": "reject"}])
            self.assertEqual(self.run_tool(root), 0)
            rows = [json.loads(x) for x in (root / "out/doc-a/pages.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual((rows[1]["text"], rows[1]["status"], rows[1]["human_review"]["outcome"]),
                             ("จอตาบวม", "ocr_unreviewed", "fix"))
            self.assertEqual((rows[2]["status"], rows[2]["human_review"]["outcome"]), ("garbled", "reject"))
            self.assertEqual(rows[0]["human_review"], None)

    def test_every_ocr_page_needs_an_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make(root, [{"key": "doc-a:p2", "outcome": "pass"}])
            with self.assertRaises(SystemExit):
                self.run_tool(root)


if __name__ == "__main__":
    unittest.main()
