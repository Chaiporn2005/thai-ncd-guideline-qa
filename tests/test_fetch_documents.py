"""Offline probes for data integrity and access restrictions; no publisher requests."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from pypdf import PdfWriter

spec = importlib.util.spec_from_file_location("fetch_documents", Path(__file__).resolve().parents[1] / "scripts/fetch_documents.py")
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


def pdf_bytes(width=100):
    writer = PdfWriter()
    writer.add_blank_page(width=width, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class FetchIntegrity(unittest.TestCase):
    def test_html_login_page_is_not_saved_as_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "document"
            with self.assertRaises(ValueError):
                fetch.store_pdf(dest, b"<html>Sign in</html>")
            self.assertFalse((dest / "source.pdf").exists())

    def test_changed_download_preserves_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "document"
            original = pdf_bytes(100)
            fetch.store_pdf(dest, original)
            with self.assertRaises(ValueError):
                fetch.store_pdf(dest, pdf_bytes(200))
            self.assertEqual((dest / "source.pdf").read_bytes(), original)

    def test_cache_avoids_network_and_requires_manifest_hash_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = fetch.store_pdf(Path(tmp) / "example", pdf_bytes())
            with patch.object(fetch, "urlopen", side_effect=AssertionError("network forbidden")):
                result = fetch.fetch_one({"document_id": "example", "sha256": meta["sha256"]}, "https://example.org/doc.pdf", tmp, 30, 1024 * 1024, {})
                self.assertEqual(result["network_attempts"], 0)
                with self.assertRaises(ValueError):
                    fetch.fetch_one({"document_id": "example", "sha256": "0" * 64}, "https://example.org/doc.pdf", tmp, 30, 1024 * 1024, {})

    def test_denial_is_not_retried_or_followed_by_another_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            error = HTTPError("https://example.org/doc.pdf", 403, "Forbidden", {}, None)
            with patch.object(fetch, "urlopen", side_effect=error) as get:
                with self.assertRaises(HTTPError):
                    fetch.fetch_one({"document_id": "example"}, "https://example.org/doc.pdf", tmp, 30, 1024 * 1024, {})
                self.assertEqual(get.call_count, 1)
            self.assertFalse((Path(tmp) / "example/source.pdf").exists())

    def test_unsafe_ids_and_credentials_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ["../outside", "E:/outside", "a/b", "", ".."]:
                with self.assertRaises(ValueError):
                    fetch.safe_path(tmp, name)
        with self.assertRaises(ValueError):
            fetch.public_url("https://secret:token@example.org/doc.pdf")


if __name__ == "__main__":
    unittest.main()
