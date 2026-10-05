"""Local synthetic PDFs; no publisher PDFs or network calls are used."""
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import extract_pages as tool


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        # All fixtures and outputs stay inside this worker's assigned directory.
        fixture_root = Path(__file__).resolve().parent / "test_tmp"
        fixture_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="งาน-", dir=fixture_root)
        self.root = Path(self.temporary.name)
        self.raw = self.root / "raw"
        self.processed = self.root / "processed"

    def tearDown(self):
        self.temporary.cleanup()

    def pdf(self, doc_id="sample", texts=("Dose 70 mg/dL",), scan=False):
        folder = self.raw / doc_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "source.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(300, 200), invariant=True)
        for text in texts:
            if scan:
                image = Image.new("RGB", (600, 400), "white")
                draw = ImageDraw.Draw(image)
                draw.text((30, 60), text, fill="black", font_size=30)
                pdf.drawImage(ImageReader(image), 0, 0, width=300, height=200)
            elif text:
                pdf.drawString(20, 100, text)
            pdf.showPage()
        pdf.save()
        return path

    def extract(self, doc_id="sample", **options):
        return tool.extract_document({"document_id": doc_id, "title": "เอกสารสังเคราะห์สำหรับทดสอบ",
                                      "download_url": "https://example.invalid/source.pdf"},
                                     self.raw, self.processed, **options)

    def pages(self, doc_id="sample"):
        path = self.processed / doc_id / "pages.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def manifest(self, ids):
        path = self.root / "manifest.jsonl"
        path.write_text("".join(json.dumps({"document_id": item}) + "\n" for item in ids), encoding="utf-8")
        return path

    def cli(self, manifest, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tool.main(["--manifest", str(manifest), "--raw-dir", str(self.raw),
                              "--processed-dir", str(self.processed), *args])
        return code, json.loads(output.getvalue())

    def test_blank_middle_page_preserves_pdf_numbers_and_clinical_digits(self):
        source = self.pdf(texts=("Threshold 70 mg/dL", "", "Follow up 3 months"))
        result = self.extract()
        pages = self.pages()
        self.assertEqual([p["pdf_page"] for p in pages], [1, 2, 3])
        self.assertIn("70 mg/dL", pages[0]["text"])
        self.assertIn("3 months", pages[2]["text"])
        self.assertEqual(pages[1]["text"], "")
        self.assertEqual(pages[1]["image_references"], 0)
        self.assertIn("blank_or_vector_candidate", pages[1]["flags"])
        self.assertTrue(all(p["printed_page_number"] is None for p in pages))
        summary = result["summary"]
        self.assertEqual(summary["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(summary["pdf_pages"], 3)
        self.assertEqual(summary["processed_pages"], 3)
        self.assertEqual(summary["empty_text_pages"], 1)
        self.assertEqual(summary["extraction_status"], "needs_ocr")
        self.assertIsNone(summary["human_approval"])
        self.assertFalse(summary["clinical_or_layout_qa_performed"])

    def test_scanned_page_requires_review_and_does_not_run_optional_tools(self):
        self.pdf(texts=("Threshold 70 mg/dL",), scan=True)
        with patch.object(tool, "run_local", side_effect=AssertionError("Optional tool was called")):
            result = self.extract()
        page = self.pages()[0]
        self.assertEqual(page["text"], "")
        self.assertGreater(page["image_references"], 0)
        self.assertIn("image_only_candidate", page["flags"])
        self.assertIsNone(page["ocr_text"])
        self.assertIsNone(page["rendered_image"])
        self.assertEqual(result["summary"]["extraction_status"], "needs_ocr")

    def test_text_pdf_is_unreviewed_never_qa_passed(self):
        self.pdf()
        result = self.extract()
        self.assertEqual(result["summary"]["extraction_status"], "extracted_unreviewed")
        self.assertEqual(result["summary"]["empty_text_pages"], 0)
        self.assertIsNone(result["summary"]["human_approval"])
        saved = json.loads((self.processed / "sample" / "extraction.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["title"], "เอกสารสังเคราะห์สำหรับทดสอบ")

    def test_corrupt_pdf_fails_without_processed_artifact(self):
        source = self.pdf()
        source.write_bytes(b"not a PDF\x00\xff")
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract()
        self.assertEqual(raised.exception.code, "invalid_pdf")
        self.assertFalse((self.processed / "sample").exists())

    def test_encrypted_pdf_is_rejected_without_password_guessing(self):
        source = self.pdf()
        writer = PdfWriter()
        writer.append_pages_from_reader(PdfReader(str(source)))
        writer.encrypt("secret-password")
        buffer = io.BytesIO()
        writer.write(buffer)
        source.write_bytes(buffer.getvalue())
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract()
        self.assertEqual(raised.exception.code, "encrypted_pdf")
        self.assertFalse((self.processed / "sample").exists())

    def test_source_change_preserves_entire_previous_output(self):
        self.pdf(texts=("Original threshold 70 mg/dL",))
        self.extract()
        destination = self.processed / "sample"
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
        self.pdf(texts=("Changed threshold 90 mg/dL",))
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract()
        self.assertEqual(raised.exception.code, "source_hash_changed")
        self.assertEqual(before, {p.name: p.read_bytes() for p in destination.iterdir()})

    def test_wrong_pdf_under_same_id_fails_manifest_hash_check_before_extracting(self):
        source = self.pdf(texts=("Expected source 70 mg/dL",))
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        self.pdf(texts=("Different document 90 mg/dL",))
        with self.assertRaises(tool.ExtractionError) as raised:
            tool.extract_document({"document_id": "sample", "sha256": expected}, self.raw, self.processed)
        self.assertEqual(raised.exception.code, "manifest_hash_mismatch")
        self.assertFalse((self.processed / "sample").exists())
        matching = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        result = tool.extract_document({"document_id": "sample", "sha256": matching}, self.raw, self.processed)
        self.assertEqual(result["outcome"], "extracted")

    def test_same_bytes_reuses_cache_and_tampering_is_detected(self):
        self.pdf()
        self.extract()
        self.assertEqual(self.extract()["outcome"], "cached")
        page_path = self.processed / "sample" / "pages.jsonl"
        page_path.write_text('{"tampered":true}\n', encoding="utf-8")
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract()
        self.assertEqual(raised.exception.code, "cached_output_corrupt")
        self.assertIn("tampered", page_path.read_text(encoding="utf-8"))

    def test_changed_settings_are_not_silently_reused(self):
        self.pdf(texts=("Page one", "Page two"))
        self.extract(max_pages=1)
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract(max_pages=2)
        self.assertEqual(raised.exception.code, "configuration_changed")
        self.assertEqual(len(self.pages()), 1)

    def test_path_traversal_and_windows_reserved_names_are_rejected(self):
        for bad in ("../escape", "..", "a/b", "a\\b", "C:escape", "CON", "nul.pdf", "name.", "a ", None):
            with self.subTest(document_id=bad), self.assertRaises(tool.ExtractionError):
                self.extract(bad)
        self.assertFalse(self.processed.exists())

    def test_symlink_cannot_escape_raw_root(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.raw.mkdir()
        try:
            (self.raw / "sample").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Symlink creation not available on this host: {exc}")
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract()
        self.assertEqual(raised.exception.code, "path_escape")

    def test_page_and_source_size_caps(self):
        self.pdf(texts=("Page one", "Page two", "Page three"))
        result = self.extract(max_pages=2)
        self.assertEqual([p["pdf_page"] for p in self.pages()], [1, 2])
        self.assertTrue(result["summary"]["page_cap_applied"])
        self.assertFalse(result["summary"]["all_pdf_pages_processed"])
        self.pdf("large")
        with self.assertRaises(tool.ExtractionError) as raised:
            self.extract("large", max_bytes=10)
        self.assertEqual(raised.exception.code, "source_size_limit")
        self.assertFalse((self.processed / "large").exists())

    def test_explicit_empty_cohort_does_not_extract_everything(self):
        self.pdf()
        manifest = self.manifest(["sample"])
        cohort = self.root / "cohort.csv"
        cohort.write_text("document_id,notes\n", encoding="utf-8")
        code, result = self.cli(manifest, "--cohort", str(cohort))
        self.assertEqual(code, 0)
        self.assertEqual(result["results"], [])
        self.assertFalse(self.processed.exists())

    def test_missing_file_does_not_consume_document_cap_and_manifest_unchanged(self):
        self.pdf("present")
        manifest = self.manifest(["missing", "present", "third"])
        before = manifest.read_bytes()
        code, result = self.cli(manifest, "--max-documents", "1")
        self.assertEqual(code, 0)
        self.assertEqual([r["outcome"] for r in result["results"]],
                         ["missing_local_file", "extracted", "run_limit_reached"])
        self.assertEqual(result["attempted_present_documents"], 1)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(manifest.read_bytes(), before)

    def test_cli_total_page_budget_and_corrupt_document_error(self):
        self.pdf("first", texts=("One", "Two"))
        self.pdf("second", texts=("Three", "Four"))
        manifest = self.manifest(["first", "second"])
        code, result = self.cli(manifest, "--max-total-pages", "3")
        self.assertEqual(code, 0)
        self.assertEqual([r["summary"]["processed_pages"] for r in result["results"]], [2, 1])
        self.assertTrue(result["results"][1]["summary"]["page_cap_applied"])
        source = self.pdf("bad")
        source.write_bytes(b"%PDF-1.7\ntruncated")
        manifest = self.manifest(["bad"])
        code, result = self.cli(manifest)
        self.assertEqual(code, 1)
        self.assertEqual(result["results"][0]["error_code"], "invalid_pdf")
        self.assertFalse((self.processed / "bad").exists())

    def test_malformed_cohort_and_case_colliding_ids_are_selection_errors(self):
        manifest = self.manifest(["sample"])
        cohort = self.root / "cohort.csv"
        cohort.write_text("document_id,notes\n,empty ID\n", encoding="utf-8")
        code, result = self.cli(manifest, "--cohort", str(cohort))
        self.assertEqual(code, 2)
        self.assertEqual(result["error_code"], "unsafe_document_id")
        manifest = self.manifest(["Sample", "sample"])
        code, result = self.cli(manifest)
        self.assertEqual(code, 2)
        self.assertEqual(result["error_code"], "duplicate_document_id")

    def test_failed_render_attempts_consume_global_budget(self):
        self.pdf("first", texts=("One", "Two"), scan=True)
        self.pdf("second", texts=("Three",), scan=True)
        manifest = self.manifest(["first", "second"])
        with patch.object(tool.shutil, "which", return_value="local-tool"), patch.object(
                tool, "run_local", side_effect=tool.ExtractionError("optional_tool_failed", "Synthetic renderer failure")) as run:
            code, result = self.cli(manifest, "--render", "--max-total-render-pages", "1")
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["render_attempts"], 1)
        self.assertEqual(result["results"][0]["summary"]["rendered_pages"], 0)
        self.assertEqual(result["results"][1]["work_usage"]["render_attempts"], 0)

    def test_interruption_discards_staging_output(self):
        self.pdf("first", texts=("One", "Two"))
        self.pdf("second", texts=("Three",))
        manifest = self.manifest(["first", "second"])
        real_count = tool.image_count
        calls = 0

        def interrupt_staging(page):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt("Synthetic interruption")
            return real_count(page)

        # Interruptions intentionally propagate; staging still cleans up and no partial output appears.
        with patch.object(tool, "image_count", side_effect=interrupt_staging), self.assertRaises(KeyboardInterrupt):
            self.cli(manifest)
        self.assertFalse((self.processed / "first").exists())
        self.assertFalse((self.processed / "second").exists())

    @unittest.skipUnless(shutil.which("pdftoppm") and shutil.which("tesseract"), "Local rendering/OCR tools unavailable")
    def test_real_local_render_and_ocr_keep_original_scan_text_unreviewed(self):
        self.pdf(scan=True)
        result = self.extract(ocr=True, ocr_languages="eng", max_render_pages=1)
        page = self.pages()[0]
        self.assertEqual(page["text"], "")
        self.assertIn("image_only_candidate", page["flags"])
        self.assertTrue((self.processed / "sample" / page["rendered_image"]).is_file())
        self.assertIsInstance(page["ocr_text"], str)
        self.assertEqual(result["summary"]["ocr_pages"], 1)
        self.assertEqual(result["summary"]["extraction_status"], "needs_ocr")
        self.assertFalse(result["summary"]["clinical_or_layout_qa_performed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
