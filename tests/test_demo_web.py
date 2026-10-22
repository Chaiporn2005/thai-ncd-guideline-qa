"""The demo web server: which requests it answers (local only) and which files it serves. No model is loaded."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_entry", ROOT / "demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class LocalOnly(unittest.TestCase):
    def test_local_hosts_pass(self):
        for host in ("127.0.0.1:8780", "localhost:8780", "[::1]:8780", "localhost"):
            self.assertTrue(demo.local_request_ok(host, None, 8780), host)

    def test_other_host_names_are_refused_even_when_they_resolve_to_this_machine(self):
        for host in ("evil.com", "evil.com:8780", "127.0.0.1.evil.com:8780", "", None):
            self.assertFalse(demo.local_request_ok(host, None, 8780), host)

    def test_cross_site_origin_is_refused(self):
        self.assertFalse(demo.local_request_ok("127.0.0.1:8780", "https://evil.com", 8780))
        self.assertFalse(demo.local_request_ok("127.0.0.1:8780", "http://localhost:9999", 8780))   # another local app is not this page
        self.assertFalse(demo.local_request_ok("127.0.0.1:8780", "null", 8780))
        self.assertTrue(demo.local_request_ok("127.0.0.1:8780", "http://127.0.0.1:8780", 8780))
        self.assertTrue(demo.local_request_ok("localhost:8780", "http://localhost:8780", 8780))


class StaticFiles(unittest.TestCase):
    def test_page_and_assets_are_served_with_their_types(self):
        for path, ctype in (("/", "text/html"), ("/app.js", "text/javascript"), ("/app.css", "text/css"), ("/assets/logo.svg", "image/svg+xml")):
            found = demo.static_file(path)
            self.assertIsNotNone(found, path)
            self.assertTrue(found[1].startswith(ctype), path)

    def test_nothing_outside_the_web_folder_or_of_another_type_is_served(self):
        for path in ("/../demo.py", "/%2e%2e/demo.py", "/..\\demo.py", "/demo.py", "/index.html/../../.env", "/missing.js", "/tokens.css/../../README.md"):
            self.assertIsNone(demo.static_file(path), path)


if __name__ == "__main__":
    unittest.main()
