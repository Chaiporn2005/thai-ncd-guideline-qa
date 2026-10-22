"""Fusion functions, Thai tokenizer modes and the BM25 wrapper."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ncdqa.retrieval import fusion  # noqa: E402
from ncdqa.retrieval.bm25 import BM25Index  # noqa: E402
from ncdqa.retrieval.thai_tokens import tokenize  # noqa: E402


class Fusion(unittest.TestCase):
    def test_rrf_formula_and_order(self):
        out = dict(fusion.rrf([["a", "b", "c"], ["b", "a", "d"]], k=60))
        self.assertAlmostEqual(out["a"], 1 / 61 + 1 / 62)
        self.assertAlmostEqual(out["b"], 1 / 62 + 1 / 61)
        self.assertAlmostEqual(out["d"], 1 / 63)
        self.assertEqual(fusion.rrf([["a", "b"]], 60, top=1)[0][0], "a")

    def test_rrf_only_depends_on_ranks(self):
        self.assertEqual(fusion.rrf([["x", "y"], ["y", "x"]]), fusion.rrf([["x", "y"], ["y", "x"]]))

    def test_convex_endpoints_equal_each_ranker(self):
        dense = [("a", 0.9), ("b", 0.5), ("c", 0.1)]
        lexical = [("c", 30.0), ("b", 10.0), ("d", 2.0)]
        self.assertEqual([d for d, _ in fusion.convex(dense, lexical, 1.0)][:3], ["a", "b", "c"])
        self.assertEqual([d for d, _ in fusion.convex(dense, lexical, 0.0)][:2], ["c", "b"])  # the rest tie at 0

    def test_convex_gives_missing_documents_zero_from_that_list(self):
        out = dict(fusion.convex([("a", 1.0), ("b", 0.0)], [("c", 5.0), ("d", 1.0)], 0.5))
        self.assertAlmostEqual(out["a"], 0.5)
        self.assertAlmostEqual(out["c"], 0.5)
        self.assertAlmostEqual(out["b"], 0.0)


class Tokens(unittest.TestCase):
    def test_default_newmm_breaks_latin_terms_and_latin_mode_keeps_them(self):
        self.assertNotIn("hba1c", tokenize("ตรวจ HbA1c ทุกสามเดือน", "newmm"))
        self.assertIn("hba1c", tokenize("ตรวจ HbA1c ทุกสามเดือน", "newmm_latin"))
        self.assertIn("mg/dl", tokenize("น้อยกว่า 70 mg/dL", "newmm_latin"))

    def test_extra_dictionary_word_stays_whole(self):
        text = "ยาเมทฟอร์มินลดน้ำตาล"
        self.assertNotIn("เมทฟอร์มิน", tokenize(text, "newmm_latin"))
        self.assertIn("เมทฟอร์มิน", tokenize(text, "newmm_dict", ("เมทฟอร์มิน",)))

    def test_char_ngrams_cover_thai_runs(self):
        self.assertEqual(tokenize("ไตวาย", "char3"), ["ไตว", "ตวา", "วาย"])
        self.assertEqual(tokenize("ไต", "char3"), ["ไต"])


class Bm25(unittest.TestCase):
    def test_ranks_the_matching_unit_first_and_ignores_unknown_terms(self):
        docs = [["เบาหวาน", "น้ำตาล"], ["ความดัน", "สูง"], ["ไต", "วาย"]]
        index = BM25Index(["d1", "d2", "d3"], docs, 1.5, 0.75)
        self.assertEqual(index.top(["ความดัน", "ไม่มีคำนี้"], 3)[0][0], "d2")
        self.assertEqual(index.top(["ไม่มีเลย"], 3), [])


if __name__ == "__main__":
    unittest.main()
