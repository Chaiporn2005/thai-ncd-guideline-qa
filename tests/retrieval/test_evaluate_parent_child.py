"""Metrics, relevance rule, paired bootstrap and the child -> parent mapping."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ncdqa.retrieval import evaluate as ev  # noqa: E402
from ncdqa.retrieval.dense import DenseIndex  # noqa: E402
from ncdqa.retrieval.parent_child import ParentChildIndex, build_parent_map  # noqa: E402


def unit(cid, start, end, text, edition="e1", doc="d", cs=0, ce=100):
    return {"chunk_id": cid, "document_id": doc, "edition_id": edition, "pdf_page_start": start, "pdf_page_end": end,
            "char_start": cs, "char_end": ce, "text": text}


EVID = {"document_id": "d", "edition_id": "e1", "pdf_page": 5, "quote": "HbA1c น้อยกว่า 7 เปอร์เซ็นต์"}


class Relevance(unittest.TestCase):
    def test_needs_edition_page_and_quote(self):
        good = unit("a", 5, 5, "ควร HbA1c น้อยกว่า 7 เปอร์เซ็นต์ ในผู้ใหญ่")
        self.assertTrue(ev.covers(good, EVID))
        self.assertFalse(ev.covers({**good, "edition_id": "e2"}, EVID))
        self.assertFalse(ev.covers({**good, "pdf_page_start": 6, "pdf_page_end": 6}, EVID))
        self.assertFalse(ev.covers({**good, "text": "ข้อความอื่นทั้งหมด"}, EVID))

    def test_whitespace_and_a_cut_through_the_quote_are_tolerated(self):
        self.assertTrue(ev.covers(unit("a", 5, 5, "HbA1c  น้อยกว่า\n7 เปอร์เซ็นต์"), EVID))
        self.assertTrue(ev.covers(unit("a", 5, 5, "...HbA1c น้อยกว่า 7 เปอร์"), EVID))  # chunk ends inside the quote, first half present


class Metrics(unittest.TestCase):
    def test_recall_hit_and_mrr_for_one_and_two_evidence_items(self):
        e2 = {**EVID, "pdf_page": 6, "quote": "ความดันโลหิตเป้าหมายต่ำกว่า 130"}
        ranked = [unit("x", 1, 1, "ไม่เกี่ยว"), unit("y", 5, 5, "HbA1c น้อยกว่า 7 เปอร์เซ็นต์"),
                  unit("z", 6, 6, "ความดันโลหิตเป้าหมายต่ำกว่า 130")]
        one = ev.score_question(ranked, [EVID], [1, 3])
        self.assertEqual((one["recall@1"], one["recall@3"], one["mrr@3"]), (0.0, 1.0, 0.5))
        two = ev.score_question(ranked, [EVID, e2], [2, 3])
        self.assertEqual((two["recall@2"], two["hit@2"], two["recall@3"]), (0.5, 1.0, 1.0))

    def test_mrr_is_zero_without_a_hit_inside_k(self):
        self.assertEqual(ev.score_question([unit("x", 1, 1, "ไม่เกี่ยว")], [EVID], [5])["mrr@5"], 0.0)


class Bootstrap(unittest.TestCase):
    def test_paired_difference_counts_and_interval(self):
        a = {f"q{i}": 0.0 for i in range(20)}
        b = {f"q{i}": 1.0 if i < 15 else 0.0 for i in range(20)}
        r = ev.paired_bootstrap(a, b, n=300)
        self.assertEqual((r["n"], r["b_better"], r["a_better"], r["ties"]), (20, 15, 0, 5))
        self.assertGreater(r["ci95"][0], 0.3)


class ParentChild(unittest.TestCase):
    def setUp(self):
        self.parents = [unit("P1", 1, 1, "", cs=0, ce=400), unit("P2", 1, 2, "", cs=400, ce=300), unit("P3", 3, 3, "", cs=0, ce=500)]
        self.children = [unit("c1", 1, 1, "", cs=0, ce=100), unit("c2", 1, 1, "", cs=380, ce=450),
                         unit("c3", 2, 2, "", cs=100, ce=200), unit("c4", 3, 3, "", cs=250, ce=350)]

    def test_child_belongs_to_the_parent_holding_its_start(self):
        m = build_parent_map(self.children, self.parents)
        self.assertEqual([m[c] for c in ("c1", "c2", "c3", "c4")], ["P1", "P1", "P2", "P3"])

    def test_search_returns_deduplicated_parents_with_best_child_score(self):
        vectors = np.array([[1, 0], [0.9, 0.1], [0, 1], [0.1, 0.9]], dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        index = ParentChildIndex(DenseIndex(vectors, ["c1", "c2", "c3", "c4"]), build_parent_map(self.children, self.parents))
        hits = index.search(np.array([[1.0, 0.0]], dtype=np.float32), k=3)[0]
        self.assertEqual([h[0] for h in hits], ["P1", "P3", "P2"])  # c1,c2 -> P1; c4 -> P3 beats c3 -> P2 for this query
        self.assertEqual(hits[0][0], "P1")
        self.assertEqual(hits[0][2], "c1")
        self.assertEqual(len({h[0] for h in hits}), len(hits))


if __name__ == "__main__":
    unittest.main()
