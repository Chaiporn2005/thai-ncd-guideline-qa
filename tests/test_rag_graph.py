"""The LangGraph version of the answer pipeline: same answers as the plain pipeline, plus a bounded recover loop. Fake retriever and LLM, no network."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncdqa.llm.client import LLMResponse  # noqa: E402
from ncdqa.rag.graph import GraphPipeline  # noqa: E402
from ncdqa.rag.lc_adapters import CachedChat, GuidelineRetriever  # noqa: E402
from ncdqa.rag.pipeline import Pipeline  # noqa: E402

CFG = json.loads((ROOT / "configs/rag/generate_v1.json").read_text(encoding="utf-8"))


def hit(rank, text, score=0.9, flags=()):
    return {"rank": rank, "chunk_id": f"c{rank}", "score": score, "document_id": "DOC", "edition_id": "2566", "pdf_page_start": 10, "pdf_page_end": 11,
            "text": text, "injection_flags": list(flags)}


HITS = [hit(1, "เป้าหมาย HbA1c น้อยกว่า 7 เปอร์เซ็นต์"), hit(2, "ความดัน 130/80")]
GOOD = json.dumps({"abstain": False, "claims": [{"text": "HbA1c น้อยกว่า 7", "cite": ["S1"]}]}, ensure_ascii=False)


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits

    def search(self, q, variant, k):
        return self.hits[:k]


class ScriptedLLM:
    """Returns the scripted replies in order: each is text or (text, finish_reason)."""
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, messages, **kw):
        self.calls.append(messages)
        r = self.replies[min(len(self.calls), len(self.replies)) - 1]
        text, finish = (r, "stop") if isinstance(r, str) else r
        return LLMResponse(text, "fake", "fake", False, "h", {}, None, finish, 0.0)


def cfg_with(retries=0, **patch):
    cfg = copy.deepcopy(CFG)
    cfg["recover"] = {"max_retries": retries}
    cfg.update(patch)
    return cfg


def graph(llm, retries=0, hits=HITS, guards=None, cfg=None):
    return GraphPipeline(FakeRetriever(hits), llm, cfg or cfg_with(retries), guards)


class SameAsThePlainPipeline(unittest.TestCase):
    def check(self, reply, hits=HITS):
        g = graph(ScriptedLLM(reply), hits=hits).answer("q?")
        p = Pipeline(FakeRetriever(hits), ScriptedLLM(reply), cfg_with(0)).answer("q?")
        for key in ("status", "answer", "citations", "claims"):
            self.assertEqual(g.get(key), p.get(key), key)
        return g

    def test_answered(self):
        g = self.check(GOOD)
        self.assertEqual(g["status"], "answered")
        self.assertEqual(g["trace"]["graph_path"], ["guard", "retrieve", "generate", "check", "finalize"])
        self.assertEqual(g["trace"]["evidence"], {"S1": "c1", "S2": "c2"})

    def test_abstained_and_invalid_claims(self):
        self.assertEqual(self.check('{"abstain": true, "claims": []}')["status"], "abstained_model")
        self.assertEqual(self.check(json.dumps({"claims": [{"text": "HbA1c น้อยกว่า 9", "cite": ["S1"]}]}, ensure_ascii=False))["status"], "abstained_validator")
        self.assertEqual(self.check("ไม่ใช่ JSON")["status"], "parse_error")

    def test_no_hits_never_calls_the_model(self):
        llm = ScriptedLLM(GOOD)
        r = graph(llm, hits=[]).answer("q?")
        self.assertEqual((r["status"], llm.calls), ("abstained_no_evidence", []))
        self.assertEqual(r["trace"]["graph_path"], ["guard", "retrieve", "finalize"])

    def test_guard_blocks_before_retrieval(self):
        llm = ScriptedLLM(GOOD)
        r = graph(llm, guards=[lambda q: {"block": True, "reason": "pii"}]).answer("q?")
        self.assertEqual((r["status"], r["trace"]["graph_path"], llm.calls), ("refused_input", ["guard", "finalize"], []))

    def test_injected_hits_are_used_instead_of_retrieval(self):
        llm = ScriptedLLM(GOOD)
        graph(llm, hits=[]).answer("q?", retrieved=HITS)
        self.assertEqual(len(llm.calls), 1)


class Recover(unittest.TestCase):
    def test_one_retry_fixes_a_broken_reply_and_shows_the_model_its_own_reply(self):
        llm = ScriptedLLM("ไม่ใช่ JSON", GOOD)
        r = graph(llm, retries=1).answer("q?")
        self.assertEqual(r["status"], "answered")
        self.assertEqual(r["trace"]["graph_path"], ["guard", "retrieve", "generate", "check", "recover", "generate", "check", "finalize"])
        self.assertEqual(r["trace"]["recovered_from"], "parse_error")
        second = llm.calls[1]
        self.assertEqual([m["role"] for m in second[-2:]], ["assistant", "user"])
        self.assertEqual(second[-2]["content"], "ไม่ใช่ JSON")

    def test_truncated_reply_asks_for_a_shorter_answer(self):
        llm = ScriptedLLM(('{"abstain": false, "claims": [', "length"), GOOD)
        r = graph(llm, retries=1).answer("q?")
        self.assertEqual((r["status"], r["trace"]["recovered_from"]), ("answered", "truncated"))
        self.assertIn("สั้นลง", llm.calls[1][-1]["content"])

    def test_the_loop_is_bounded(self):
        llm = ScriptedLLM("เสีย", "เสียอีก", GOOD)
        r = graph(llm, retries=1).answer("q?")
        self.assertEqual((r["status"], len(llm.calls)), ("parse_error", 2))

    def test_default_has_no_retry(self):
        llm = ScriptedLLM("เสีย", GOOD)
        r = graph(llm, retries=0).answer("q?")
        self.assertEqual((r["status"], len(llm.calls)), ("parse_error", 1))

    def test_a_valid_abstention_is_not_retried(self):
        llm = ScriptedLLM('{"abstain": true, "claims": []}', GOOD)
        self.assertEqual((graph(llm, retries=1).answer("q?")["status"], len(llm.calls)), ("abstained_model", 1))


class Adapters(unittest.TestCase):
    def test_retriever_keeps_the_hit_dict(self):
        docs = GuidelineRetriever(retriever=FakeRetriever(HITS), variant="B", k=1).invoke("q")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].metadata["hit"]["chunk_id"], "c1")
        self.assertEqual(docs[0].page_content, HITS[0]["text"])

    def test_chat_passes_roles_and_returns_cache_metadata(self):
        llm = ScriptedLLM("ตอบ")
        reply = CachedChat(client=llm, max_tokens=50).invoke([("system", "ระบบ"), ("human", "ถาม")])
        self.assertEqual([m["role"] for m in llm.calls[0]], ["system", "user"])
        self.assertEqual((reply.content, reply.response_metadata["cached"], reply.response_metadata["finish_reason"]), ("ตอบ", False, "stop"))


if __name__ == "__main__":
    unittest.main()
