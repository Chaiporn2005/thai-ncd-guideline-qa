"""The search() interface: needs the local index (data/index, not in git); skipped where it is missing."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
NEEDED = [ROOT / "data/index/chunks-v12-t512/chunks.jsonl", ROOT / "data/index/dense-bge-m3-t128-v12/vectors.npy"]


@unittest.skipUnless(all(p.exists() for p in NEEDED), "local v12 index not present")
class Search(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ncdqa.retrieval.search import Retriever
        cls.r = Retriever()

    def test_hits_carry_provenance_and_are_ranked(self):
        hits = self.r.search("ค่าความดันโลหิตเป้าหมายในผู้ป่วยเบาหวาน", "B", 5)
        self.assertEqual([h["rank"] for h in hits], [1, 2, 3, 4, 5])
        for key in ("chunk_id", "document_id", "edition_id", "pdf_page_start", "pdf_page_end", "text", "score", "injection_flags"):
            self.assertIn(key, hits[0])
        self.assertTrue(all(a["score"] >= b["score"] for a, b in zip(hits, hits[1:])))

    def test_filter_only_returns_matching_hits(self):
        hits = self.r.search("เบาหวานในเด็ก", "A", 5, filters={"population": "pediatric"})
        self.assertTrue(hits and all(h["population"] == "pediatric" for h in hits))

    def test_unknown_variant_is_refused(self):
        with self.assertRaises(ValueError):
            self.r.search("x", "Z")


if __name__ == "__main__":
    unittest.main()
