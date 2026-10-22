"""The .env loader returns names only, lets the real environment win and understands quotes and export."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ncdqa.llm.env import is_set, load_env  # noqa: E402


class Env(unittest.TestCase):
    def setUp(self):
        for n in ("T_KEY_A", "T_KEY_B", "T_KEY_C", "T_EMPTY"):
            os.environ.pop(n, None)

    def test_loads_names_never_values_and_respects_existing_environment(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text('# comment\nT_KEY_A=alpha\nexport T_KEY_B="beta value"\nT_KEY_C=\'gamma\'\nT_EMPTY=\nnot a line\n', encoding="utf-8")
            os.environ["T_KEY_A"] = "from-shell"
            names = load_env(p)
            self.assertEqual(sorted(names), ["T_KEY_B", "T_KEY_C"])
            self.assertEqual(os.environ["T_KEY_A"], "from-shell")
            self.assertEqual(os.environ["T_KEY_B"], "beta value")
            self.assertEqual(os.environ["T_KEY_C"], "gamma")
            self.assertFalse(is_set("T_EMPTY"))
            self.assertNotIn("beta value", "".join(names))

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(load_env(Path(tempfile.gettempdir()) / "definitely-missing.env"), [])


if __name__ == "__main__":
    unittest.main()
