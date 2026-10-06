"""Typhoon OCR runner: sharding, resume, rate-limit retry and key handling, with the API mocked."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
import unittest.mock
from pathlib import Path

spec = importlib.util.spec_from_file_location("ocr_typhoon", Path(__file__).resolve().parents[1] / "scripts/ocr_typhoon.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

PAGES = [{"document_id": "doc-a", "pdf_page": n, "normalized_status": "empty", "source_sha256": "a" * 64,
          "pdf_path": "unused.pdf"} for n in range(1, 6)]
KEY = "secret-test-key-123"


class RateLimitError(Exception):
    status_code = 429


def run(folder: Path, *extra: str, ocr=None, env=None):
    out = io.StringIO()
    patches = [unittest.mock.patch.object(tool, "select_pages", return_value=(list(PAGES), [])),
               unittest.mock.patch.object(tool, "MIN_INTERVAL_S", 0),
               unittest.mock.patch.object(tool.time, "sleep"),
               unittest.mock.patch.object(tool, "version", return_value="test"),
               unittest.mock.patch.dict(os.environ, env if env is not None else {"TYPHOON_OCR_API_KEY": KEY})]
    if ocr is not None:
        patches.append(unittest.mock.patch.object(tool, "ocr_page", side_effect=ocr))
    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        stack.enter_context(contextlib.redirect_stdout(out))
        code = tool.main(["--out-dir", str(folder), *extra])
    return code, out.getvalue()


def rows(folder: Path, name: str):
    return [json.loads(x) for x in (folder / name).read_text(encoding="utf-8").splitlines()]


class OcrRunner(unittest.TestCase):
    def test_shards_are_disjoint_and_cover_all_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            run(folder, "--shard", "0", "--num-shards", "2", ocr=lambda item, *a: f"text {item['pdf_page']}")
            run(folder, "--shard", "1", "--num-shards", "2", ocr=lambda item, *a: f"text {item['pdf_page']}")
            first = {r["pdf_page"] for r in rows(folder, "shard-0-of-2.jsonl")}
            second = {r["pdf_page"] for r in rows(folder, "shard-1-of-2.jsonl")}
            self.assertEqual((first, second), ({1, 3, 5}, {2, 4}))

    def test_resume_skips_done_pages_and_retries_failed_ones(self):
        calls = []

        def flaky(item, *args):
            calls.append(item["pdf_page"])
            if item["pdf_page"] == 3 and calls.count(3) == 1:
                raise ValueError("server error")
            return "ok"

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            code, _ = run(folder, "--shard", "0", "--num-shards", "1", ocr=flaky)
            self.assertEqual(code, 1)
            code, _ = run(folder, "--shard", "0", "--num-shards", "1", ocr=flaky)
            self.assertEqual(code, 0)
            self.assertEqual(calls, [1, 2, 3, 4, 5, 3])
            outcomes = [(r["pdf_page"], r["outcome"]) for r in rows(folder, "shard-0-of-1.jsonl")]
            self.assertIn((3, "failed"), outcomes)
            self.assertEqual(sum(1 for p, o in outcomes if o == "ocr_done"), 5)

    def test_rate_limit_is_retried_with_backoff(self):
        attempts = {"n": 0}

        def limited(item, *args):
            attempts["n"] += 1
            if attempts["n"] <= 2:
                raise RateLimitError("429")
            return "ok"

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            code, _ = run(folder, "--shard", "0", "--num-shards", "1", "--limit", "1", ocr=limited)
            row = rows(folder, "shard-0-of-1.jsonl")[0]
            self.assertEqual((code, row["outcome"], row["attempts"]), (0, "ocr_done", 3))

    def test_output_is_unreviewed_and_key_never_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            _, stdout = run(folder, "--shard", "0", "--num-shards", "1", "--limit", "2", ocr=lambda *a: "ok")
            text = (folder / "shard-0-of-1.jsonl").read_text(encoding="utf-8")
            self.assertNotIn(KEY, text + stdout)
            self.assertTrue(all(r["status"] == "ocr_unreviewed" for r in rows(folder, "shard-0-of-1.jsonl")))

    def test_missing_key_stops_before_any_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            ocr = unittest.mock.Mock()
            with self.assertRaises(SystemExit):
                with contextlib.redirect_stderr(io.StringIO()):
                    run(Path(tmp), "--shard", "0", "--num-shards", "1", ocr=ocr, env={"TYPHOON_OCR_API_KEY": ""})
            ocr.assert_not_called()

    def test_env_file_supplies_named_key_without_leaking_it(self):
        seen = []
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            env_file = folder / ".env"
            env_file.write_text("# comment\nTYPHOON_OCR_API_KEY_B='from-file-key'\nEMPTY=\n", encoding="utf-8")
            _, stdout = run(folder, "--shard", "0", "--num-shards", "1", "--limit", "1",
                            "--env-file", str(env_file), "--api-key-env", "TYPHOON_OCR_API_KEY_B",
                            ocr=lambda item, key, *a: seen.append(key) or "ok",
                            env={"TYPHOON_OCR_API_KEY_B": ""})
            self.assertEqual(seen, ["from-file-key"])
            self.assertNotIn("from-file-key", stdout + (folder / "shard-0-of-1.jsonl").read_text(encoding="utf-8"))

    def test_dry_run_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            ocr = unittest.mock.Mock()
            code, stdout = run(Path(tmp), "--shard", "1", "--num-shards", "2", "--dry-run", ocr=ocr)
            self.assertEqual((code, json.loads(stdout)["to_run"]), (0, 2))
            ocr.assert_not_called()


if __name__ == "__main__":
    unittest.main()
