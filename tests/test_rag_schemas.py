"""Retrieval contract schemas (T16) on synthetic records; no publisher text, models or network."""
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "validate_rag_jsonl", Path(__file__).resolve().parents[1] / "scripts/validate_rag_jsonl.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

SHA = "a" * 64
COMMIT = "b" * 40

PAGE = {
    "document_id": "ht-guideline-2567", "source_sha256": SHA, "pdf_page": 42, "pdf_page_label": "38",
    "printed_page_number": None, "text": "เป้าหมายความดันโลหิต < 140/90 mmHg", "text_source": "pdf_text_repaired",
    "status": "ok", "removed_edge_lines": ["แนวทางการรักษาโรคความดันโลหิตสูง"], "human_review": None,
    "quality": {"garbled_characters": 0},
}

CHUNK = {
    "chunk_id": "ht-guideline-2567:p042-p043:003", "corpus_version": "normalized-v1",
    "chunk_config_id": "struct-512-ctx", "document_id": "ht-guideline-2567",
    "edition_id": "ht-guideline-2567-e1", "source_sha256": SHA, "pdf_page_start": 42, "pdf_page_end": 43,
    "pdf_page_label_start": "38", "char_start": 120, "char_end": 80,
    "section_path": ["บทที่ 3", "3.2 เป้าหมาย"], "chunk_type": "table_rows", "table_id": "ht-guideline-2567:t07",
    "text": "เป้าหมายความดันโลหิต < 140/90 mmHg", "header_text": "แนวทาง HT 2567 > บทที่ 3 > 3.2",
    "token_count": 37, "tokenizer": "intfloat/multilingual-e5-base", "source_page_statuses": ["ok", "ok"],
    "injection_flags": [], "primary_group": "HT", "disease_tags": ["HT"], "document_type": "clinical_guideline",
}

HIT = {"rank": 1, "chunk_id": CHUNK["chunk_id"], "score": 0.0325, "dense_rank": 2, "bm25_rank": 1,
       "document_id": "ht-guideline-2567", "edition_id": "ht-guideline-2567-e1",
       "pdf_page_start": 42, "pdf_page_end": 43}

RESULT = {"run_id": "20261012-test-B-k10", "qid": "q017", "variant": "B", "k": 10,
          "query": "ความดันเป้าหมายเท่าไร", "hits": [HIT],
          "latency_ms": {"embed_query": 41, "dense": 3, "bm25": 6, "fusion": 0, "total": 52}}

MANIFEST = {
    "run_id": "20261012-test-B-k10", "split": "test", "variant": "B", "k": 10, "git_commit": COMMIT,
    "git_dirty": False, "config_path": "configs/retrieval/variant_B.yaml", "config_sha256": SHA,
    "corpus_version": "normalized-v1", "corpus_inventory_sha256": SHA, "chunk_config_id": "struct-512-ctx",
    "chunks_sha256": SHA, "embedding_model": {"name": "intfloat/multilingual-e5-base", "revision": "abc123"},
    "bm25": {"tokenizer": "pythainlp.newmm"}, "fusion": {"method": "rrf", "k_rrf": 60}, "index_sha256": SHA,
    "questions_sha256": SHA, "results_sha256": SHA, "device": "cpu", "machine": "Intel Core Ultra 7 258V, 32 GB",
    "python": "3.12.11", "packages": {"torch": "2.14.1"}, "started_at": "2026-10-12T09:00:00+07:00",
    "finished_at": "2026-10-12T09:02:00+07:00", "n_questions": 25,
}

QUESTION = {
    "qid": "q017", "split": "test", "status": "gold", "question": "ความดันเป้าหมายสำหรับผู้ใหญ่ทั่วไปเท่าไร",
    "answer": "< 140/90 mmHg", "type": "number_unit", "answerable": True,
    "evidence": [{"document_id": "ht-guideline-2567", "edition_id": "ht-guideline-2567-e1", "pdf_page": 42,
                  "quote": "เป้าหมายความดันโลหิต < 140/90 mmHg"}],
    "generated_by": "agent-x", "reviewed_by": "reviewer", "review_date": "2026-10-10", "changes": None,
}


def run(kind: str, records, suffix: str = ".jsonl") -> tuple[int, dict]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"input{suffix}"
        if suffix == ".json":
            path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        else:
            path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main([kind, str(path)])
        return code, json.loads(out.getvalue())


def changed(record: dict, **updates) -> dict:
    item = copy.deepcopy(record)
    item.update(updates)
    return item


class ValidExamples(unittest.TestCase):
    def test_each_kind_accepts_its_example(self):
        for kind, records, suffix in [("page_input", [PAGE], ".jsonl"), ("chunk", [CHUNK], ".jsonl"),
                                      ("retrieval_result", [RESULT], ".jsonl"),
                                      ("run_manifest", MANIFEST, ".json"), ("question", [QUESTION], ".jsonl")]:
            with self.subTest(kind=kind):
                code, report = run(kind, records, suffix)
                self.assertEqual((code, report["problems"]), (0, []))

    def test_unanswerable_question(self):
        item = changed(QUESTION, qid="q018", answer=None, evidence=[], answerable=False, type="unanswerable")
        self.assertEqual(run("question", [item])[0], 0)


class PageInput(unittest.TestCase):
    def test_rejects_zero_page_and_unknown_status(self):
        self.assertEqual(run("page_input", [changed(PAGE, pdf_page=0)])[0], 1)
        self.assertEqual(run("page_input", [changed(PAGE, status="accepted")])[0], 1)

    def test_duplicate_page(self):
        code, report = run("page_input", [PAGE, PAGE])
        self.assertEqual(code, 1)
        self.assertIn("duplicate key", report["problems"][0])


class Chunk(unittest.TestCase):
    def test_page_order_and_id_prefix(self):
        code, report = run("chunk", [changed(CHUNK, pdf_page_end=41)])
        self.assertEqual(code, 1)
        self.assertTrue(any("before pdf_page_start" in p for p in report["problems"]))
        code, report = run("chunk", [changed(CHUNK, chunk_id="ht-guideline-2567:p040-p043:003")])
        self.assertTrue(any("chunk_id must start with" in p for p in report["problems"]))

    def test_single_page_offsets(self):
        item = changed(CHUNK, chunk_id="ht-guideline-2567:p042-p042:003", pdf_page_end=42)
        self.assertEqual(run("chunk", [item])[0], 1)

    def test_garbled_or_empty_pages_cannot_feed_chunks(self):
        self.assertEqual(run("chunk", [changed(CHUNK, source_page_statuses=["garbled"])])[0], 1)
        self.assertEqual(run("chunk", [changed(CHUNK, source_page_statuses=[])])[0], 1)

    def test_no_extra_fields(self):
        self.assertEqual(run("chunk", [changed(CHUNK, embedding=[0.1])])[0], 1)


class RetrievalResult(unittest.TestCase):
    def test_rank_gaps_duplicates_and_k(self):
        gap = changed(RESULT, hits=[HIT, changed(HIT, rank=3, chunk_id="x:p001-p001:000")])
        self.assertTrue(any("ranks must be 1..n" in p for p in run("retrieval_result", [gap])[1]["problems"]))
        dup = changed(RESULT, hits=[HIT, changed(HIT, rank=2)])
        self.assertTrue(any("duplicate chunk_id" in p for p in run("retrieval_result", [dup])[1]["problems"]))
        over = changed(RESULT, k=1, hits=[HIT, changed(HIT, rank=2, chunk_id="x:p001-p001:000")])
        self.assertTrue(any("more hits than k" in p for p in run("retrieval_result", [over])[1]["problems"]))

    def test_latency_total_required(self):
        self.assertEqual(run("retrieval_result", [changed(RESULT, latency_ms={"dense": 3})])[0], 1)


class RunManifest(unittest.TestCase):
    def test_requires_full_commit_and_known_split(self):
        self.assertEqual(run("run_manifest", changed(MANIFEST, git_commit="abc"), ".json")[0], 1)
        self.assertEqual(run("run_manifest", changed(MANIFEST, split="final"), ".json")[0], 1)


class Question(unittest.TestCase):
    def test_gold_needs_reviewer(self):
        self.assertEqual(run("question", [changed(QUESTION, reviewed_by=None)])[0], 1)

    def test_test_split_cannot_be_silver(self):
        self.assertEqual(run("question", [changed(QUESTION, status="silver", reviewed_by=None,
                                                  review_date=None)])[0], 1)

    def test_answerable_needs_evidence_and_not_unanswerable_type(self):
        self.assertEqual(run("question", [changed(QUESTION, evidence=[])])[0], 1)
        self.assertEqual(run("question", [changed(QUESTION, type="unanswerable")])[0], 1)

    def test_unanswerable_must_have_no_answer(self):
        item = changed(QUESTION, answerable=False, type="unanswerable", evidence=[])
        self.assertEqual(run("question", [item])[0], 1)


class JsonlLineBreaks(unittest.TestCase):
    def test_unicode_line_separator_inside_text_does_not_split_a_record(self):
        record = changed(PAGE, text="ก่อน หลัง\x0cจบ")
        code, report = run("page_input", [record], ".jsonl")
        self.assertEqual((code, report["problems"]), (0, []))

    def test_new_page_fields_are_accepted(self):
        record = changed(PAGE, status="figure_review", population="pediatric", index_exclusion={"reason": "low_content_cover"},
                         category={"tab": 2, "label": "x"})
        self.assertEqual(run("page_input", [record], ".jsonl")[0], 0)
        self.assertEqual(run("page_input", [changed(PAGE, population="adults")], ".jsonl")[0], 1)


class Inputs(unittest.TestCase):
    def test_unreadable_file_is_input_error(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(["chunk", "does/not/exist.jsonl"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
