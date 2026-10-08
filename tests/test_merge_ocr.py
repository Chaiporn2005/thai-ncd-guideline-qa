"""OCR merge: cleaning removes only model additions, versions are never overwritten."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("merge_ocr", Path(__file__).resolve().parents[1] / "scripts/merge_ocr.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

SHA = "c" * 64


class Clean(unittest.TestCase):
    def test_removes_model_additions_and_keeps_clinical_text(self):
        raw = ("# หัวข้อ\n<page_number>18</page_number>\nLDL-C &lt; 100 mg/dL &amp; HbA1c ≥ 6.5%\n\n\n\n"
               "<figure>\nภาพประกอบผู้ป่วย\n</figure>\nไม่ควรใช้ยา")
        text, figures, printed = tool.clean_ocr(raw)
        self.assertEqual(text, "# หัวข้อ\n\nLDL-C < 100 mg/dL & HbA1c ≥ 6.5%\n\nไม่ควรใช้ยา")
        self.assertEqual((figures, printed), (["ภาพประกอบผู้ป่วย"], "18"))


class Merge(unittest.TestCase):
    def make_source(self, root: Path):
        doc = root / "src" / "doc-a"
        doc.mkdir(parents=True)
        rows = [{"document_id": "doc-a", "source_sha256": SHA, "pdf_page": 1, "text": "ปกติ", "status": "ok",
                 "text_source": "pdf_text_repaired", "removed_edge_lines": [], "human_review": None},
                {"document_id": "doc-a", "source_sha256": SHA, "pdf_page": 2, "text": "", "status": "empty",
                 "text_source": "pdf_text_repaired", "removed_edge_lines": [], "human_review": None}]
        (doc / "pages.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        (doc / "normalization.json").write_text(json.dumps({"document_id": "doc-a", "pages_jsonl_sha256": "x",
                                                            "status_counts": {"ok": 1, "empty": 1}}), encoding="utf-8")
        ocr = root / "ocr"
        ocr.mkdir()
        hit = {"document_id": "doc-a", "pdf_page": 2, "source_sha256": SHA, "outcome": "ocr_done",
               "ocr_markdown": "ข้อความจากภาพ", "model": "typhoon-ocr", "task_type": "v1.5", "typhoon_ocr_version": "0.4.1"}
        (ocr / "shard-0-of-1.jsonl").write_text(json.dumps(hit, ensure_ascii=False) + "\n", encoding="utf-8")

    def run_tool(self, root: Path) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return tool.main(["--source", str(root / "src"), "--ocr-dir", str(root / "ocr"), "--out", str(root / "out")])

    def test_merge_marks_ocr_pages_unreviewed_and_copies_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_source(root)
            self.assertEqual(self.run_tool(root), 0)
            rows = [json.loads(x) for x in (root / "out/doc-a/pages.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual((rows[0]["status"], rows[0]["text"]), ("ok", "ปกติ"))
            self.assertEqual((rows[1]["status"], rows[1]["text_source"], rows[1]["text"]),
                             ("ocr_unreviewed", "ocr", "ข้อความจากภาพ"))
            summary = json.loads((root / "out/doc-a/normalization.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status_counts"], {"ocr_unreviewed": 1, "ok": 1})

    def test_reocr_page_loses_its_exclusion_but_stays_unreviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_source(root)
            path = root / "src/doc-a/pages.jsonl"
            rows = [json.loads(x) for x in path.read_text(encoding="utf-8").split("\n") if x.strip()]
            rows[1].update(status="garbled", needs_ocr=True, text="/g1/g2/g3",
                           index_exclusion={"reason": "awaiting_reocr", "decided_by": "t", "decided_at": "2026-10-08"})
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
            self.assertEqual(self.run_tool(root), 0)
            out = [json.loads(x) for x in (root / "out/doc-a/pages.jsonl").read_text(encoding="utf-8").split("\n") if x.strip()]
            self.assertEqual((out[1]["status"], out[1]["human_review"]), ("ocr_unreviewed", None))
            self.assertNotIn("needs_ocr", out[1])
            self.assertNotIn("index_exclusion", out[1])
            self.assertEqual(out[1]["reocr"]["previous_pdf_text_status"], "garbled")
            self.assertEqual(out[1]["pre_normalization_text"], "/g1/g2/g3")

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_source(root)
            (root / "out").mkdir()
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_tool(root)

    def test_ocr_on_different_bytes_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_source(root)
            shard = root / "ocr/shard-0-of-1.jsonl"
            shard.write_text(shard.read_text(encoding="utf-8").replace(SHA, "d" * 64), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.run_tool(root)


if __name__ == "__main__":
    unittest.main()
