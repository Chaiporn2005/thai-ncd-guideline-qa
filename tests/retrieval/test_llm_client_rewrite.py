"""LLM client (cache, determinism parameters, key handling) and the query-rewrite safeguards, without any network."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from ncdqa.llm.client import LLMClient, ProviderConfig, request_hash  # noqa: E402
from ncdqa.retrieval import query_rewrite as qr  # noqa: E402

CFG = ProviderConfig(name="fake", kind="openai_compatible", model="m1", base_url="https://x/v1", api_key_env="FAKE_KEY")
MSG = [{"role": "user", "content": "สวัสดี"}]


def fake_transport(calls):
    def post(url, headers, body, timeout):
        calls.append((url, headers, body))
        return {"model": "m1-2026", "choices": [{"message": {"content": "ตอบ"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1}, "system_fingerprint": "fp1"}
    return post


class Client(unittest.TestCase):
    def setUp(self):
        os.environ["FAKE_KEY"] = "secret-value"
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name) / "cache.jsonl"

    def tearDown(self):
        os.environ.pop("FAKE_KEY", None)
        self.tmp.cleanup()

    def test_deterministic_parameters_are_sent_and_second_call_is_cached(self):
        calls = []
        client = LLMClient(CFG, self.cache, fake_transport(calls))
        first, second = client.complete(MSG), client.complete(MSG)
        body = calls[0][2]
        self.assertEqual((body["temperature"], body["top_p"], body["seed"]), (0.0, 1.0, 20261010))
        self.assertEqual(len(calls), 1)
        self.assertFalse(first.cached)
        self.assertTrue(second.cached)
        self.assertEqual(first.text, second.text)

    def test_cache_survives_a_new_client_and_key_is_never_written(self):
        LLMClient(CFG, self.cache, fake_transport([])).complete(MSG)
        calls = []
        again = LLMClient(CFG, self.cache, fake_transport(calls)).complete(MSG)
        self.assertTrue(again.cached)
        self.assertEqual(calls, [])
        self.assertNotIn("secret-value", self.cache.read_text(encoding="utf-8"))

    def test_seed_is_left_out_when_the_provider_rejects_it(self):
        from dataclasses import replace
        calls = []
        LLMClient(replace(CFG, seed=None), None, fake_transport(calls), use_cache=False).complete(MSG)
        self.assertNotIn("seed", calls[0][2])

    def test_changing_a_parameter_changes_the_request_hash(self):
        client = LLMClient(CFG, self.cache, fake_transport([]))
        self.assertNotEqual(request_hash(CFG, MSG, client.params()), request_hash(CFG, MSG, client.params(temperature=0.7)))

    def test_bypassing_the_cache_calls_the_provider_each_time(self):
        calls = []
        client = LLMClient(CFG, None, fake_transport(calls), use_cache=False)
        client.complete(MSG)
        client.complete(MSG)
        self.assertEqual(len(calls), 2)

    def test_missing_key_and_cache_only_miss_fail_loudly(self):
        os.environ.pop("FAKE_KEY")
        with self.assertRaises(RuntimeError):
            LLMClient(CFG, None, fake_transport([])).complete(MSG)
        with self.assertRaises(KeyError):
            LLMClient(ProviderConfig(name="local", kind="cache_only", model="m"), None).complete(MSG)


class Rewrite(unittest.TestCase):
    def test_personal_identifiers_are_never_sendable(self):
        self.assertFalse(qr.sendable("โทร 081-234-5678 ปรึกษาเบาหวาน"))
        self.assertFalse(qr.sendable("เลขบัตร 1234567890123"))
        self.assertTrue(qr.sendable("ค่า HbA1c เป้าหมายคือเท่าไร"))

    def test_rewrite_must_keep_numbers_and_latin_terms(self):
        self.assertTrue(qr.preserves("HbA1c ต่ำกว่า 7 หมายถึงอะไร", "ความหมายของค่า HbA1c ที่ต่ำกว่า 7 เปอร์เซ็นต์"))
        self.assertFalse(qr.preserves("HbA1c ต่ำกว่า 7 หมายถึงอะไร", "ความหมายของค่าน้ำตาลสะสมที่ต่ำ"))
        self.assertEqual(qr.finalize("rewrite", "HbA1c 7 คืออะไร", "ค่าน้ำตาลสะสม")[1], "dropped_numbers")

    def test_clean_strips_markup_thinking_and_extra_lines(self):
        self.assertEqual(qr.clean("<think>x</think>\n**แนวทางการดูแลเท้า**\nคำอธิบาย", "rewrite"), "แนวทางการดูแลเท้า")
        self.assertLessEqual(len(qr.clean("ก" * 900, "hyde")), qr.LIMITS["hyde"])

    def test_messages_have_system_shots_and_the_question_last(self):
        m = qr.messages("rewrite", "ทดสอบ")
        self.assertEqual(m[0]["role"], "system")
        self.assertEqual(m[-1], {"role": "user", "content": "คำถาม: ทดสอบ"})
        self.assertEqual(len(m), 1 + 2 * len(qr.SHOTS["rewrite"]) + 1)  # system + (user, assistant) per shot + question
        self.assertEqual(len(qr.messages("hyde", "x")), 2)

    def test_a_refusal_is_not_used_as_a_query(self):
        self.assertEqual(qr.finalize("rewrite", "งานศพที่น่านเสิร์ฟอะไร", "ไม่เกี่ยวข้องกับแนวทางเวชปฏิบัติโรคไม่ติดต่อเรื้อรัง"),
                         ("งานศพที่น่านเสิร์ฟอะไร", "refusal"))

    def test_not_sent_keeps_the_original(self):
        self.assertEqual(qr.finalize("rewrite", "ถามอะไร", None), ("ถามอะไร", "not_sent"))


if __name__ == "__main__":
    unittest.main()
