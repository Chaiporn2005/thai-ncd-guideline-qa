"""Applying a person's review decisions: only ticked edits, exact matches, safe defaults."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "apply_review_decisions", Path(__file__).resolve().parents[1] / "scripts/apply_review_decisions.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

ROWS = [
    {"document_id": "d", "pdf_page": 1, "status": "ocr_unreviewed", "text_source": "ocr", "text": "FPG > 126 มก./ดล.", "human_review": {"outcome": "pass"}},
    {"document_id": "d", "pdf_page": 2, "status": "ocr_unreviewed", "text_source": "ocr", "text": "Insulard", "human_review": {"outcome": "pass"}},
    {"document_id": "d", "pdf_page": 3, "status": "garbled", "text_source": "ocr", "text": "ข้อความดี", "human_review": {"outcome": "reject"}},
    {"document_id": "d", "pdf_page": 4, "status": "ocr_unreviewed", "text_source": "ocr", "text": "x", "human_review": {"outcome": "pass"}},
    {"document_id": "d", "pdf_page": 5, "status": "ok", "text_source": "pdf_text_repaired", "text": "ปกติ", "human_review": None},
]


def run(tmp: Path, decisions: list[dict]) -> int:
    src = tmp / "src" / "d"
    src.mkdir(parents=True)
    (src / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in ROWS), encoding="utf-8")
    (src / "normalization.json").write_text(json.dumps({"pages_jsonl_sha256": "x"}), encoding="utf-8")
    (tmp / "dec.json").write_text(json.dumps({"review_id": "t", "decisions": decisions}, ensure_ascii=False), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return tool.main(["--source", str(tmp / "src"), "--decisions", str(tmp / "dec.json"), "--reviewer", "tester",
                          "--proposer", "agent", "--out", str(tmp / "out")])


def rows(tmp: Path):
    return [json.loads(x) for x in (tmp / "out/d/pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]


class Decisions(unittest.TestCase):
    def test_accept_reject_later_and_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            code = run(tmp, [
                {"key": "d:p1", "page": "accept", "accepted_edits": [{"old": "> 126", "new": "≥ 126"}]},
                {"key": "d:p2", "page": "reject", "accepted_edits": []},
                {"key": "d:p3", "page": "accept", "accepted_edits": []},
                {"key": "d:p4", "page": "later", "accepted_edits": []}])
            self.assertEqual(code, 0)
            r = rows(tmp)
            self.assertEqual((r[0]["text"], r[0]["human_review"]["outcome"]), ("FPG ≥ 126 มก./ดล.", "fix"))
            self.assertEqual(r[0]["text_before_review_edits"], "FPG > 126 มก./ดล.")
            self.assertEqual((r[1]["status"], r[1]["human_review"]["outcome"]), ("garbled", "reject"))
            self.assertEqual((r[2]["status"], r[2]["human_review"]["outcome"]), ("ocr_unreviewed", "pass"))
            self.assertEqual(r[3]["human_review"]["outcome"], "pending")
            self.assertEqual(r[4], ROWS[4])

    def test_removal_supersedes_edit_inside_it(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            code = run(tmp, [{"key": "d:p1", "page": "accept", "accepted_edits": [
                {"old": "126", "new": "127", "kind": "number"},
                {"old": " > 126 มก.", "new": "", "kind": "remove"}]}])
            self.assertEqual((code, rows(tmp)[0]["text"]), (0, "FPG/ดล."))

    def test_edits_sharing_only_context_both_apply(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            code = run(tmp, [{"key": "d:p1", "page": "accept", "accepted_edits": [
                {"old": "FPG > 1", "new": "FBG > 1", "kind": "word"},
                {"old": "> 126 มก", "new": "> 127 มก", "kind": "number"}]}])
            self.assertEqual((code, rows(tmp)[0]["text"]), (0, "FBG > 127 มก./ดล."))

    def test_ambiguous_edit_fails(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            with self.assertRaises(tool.DecisionError):
                run(tmp, [{"key": "d:p1", "page": "accept", "accepted_edits": [{"old": " ", "new": "_"}]}])


if __name__ == "__main__":
    unittest.main()
