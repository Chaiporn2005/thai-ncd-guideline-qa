"""The answer pipeline as a LangGraph state machine (Track C).

    START -> guard -> retrieve -> generate -> check -> finalize -> END
                 \\_ refused        \\_ no evidence /       \\_ recover -> generate     (parse_error / truncated, at most `recover.max_retries` times)

Why a graph here and not just a framework wrapper: the plain pipeline in pipeline.py is linear and has no way to *recover*. The reliability stack of course
slide L13 p46 is Constrain -> Validate -> Recover -> Escalate; the plain pipeline does the first, second and last. The graph adds the third as a bounded
conditional loop: when the model's reply is not the required JSON (or was cut off), it is shown its own reply and asked to answer again, once. Nothing else
differs: the same prompt builder, the same `interpret()` (parse + validate + citations), the same cached LLM client and the same result dict, so a graph run
can be scored by the same scripts. With `recover.max_retries = 0` (the default in configs/rag/generate_v1.json) the graph gives the plain pipeline's answers.
The node path is written to `trace["graph_path"]`, a local audit trail (no tracing service).
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from . import prompt as prompt_mod
from .lc_adapters import CachedChat, GuidelineRetriever, to_dicts, to_messages
from .pipeline import ROOT, DEFAULT_CONFIG, Guard, config_hash, interpret

RETRY_FEEDBACK = {
    "parse_error": "คำตอบก่อนหน้าไม่ใช่ JSON ตามรูปแบบที่กำหนด ตอบใหม่เป็น JSON อย่างเดียวตามรูปแบบเดิม",
    "truncated": "คำตอบก่อนหน้ายาวเกินและถูกตัดกลางคัน ตอบใหม่ให้สั้นลง (ไม่เกิน 2 claim) เป็น JSON อย่างเดียวตามรูปแบบเดิม",
}


class State(TypedDict, total=False):
    question: str
    retrieved: list[dict] | None
    hits: list[dict]
    evidence: dict[str, dict]
    messages: list[dict]
    raw: str
    finish_reason: str | None
    attempt: int
    status: str
    extra: dict
    trace: dict
    path: list[str]


class GraphPipeline:
    def __init__(self, retriever, client, cfg: dict, guards: list[Guard] | None = None):
        self.cfg, self.guards = cfg, guards or []
        self.config_id = f'{cfg["id"]}-{config_hash(cfg)}'
        self.max_retries = cfg.get("recover", {}).get("max_retries", 0)
        self.retriever = GuidelineRetriever(retriever=retriever, variant=cfg["retrieval"]["variant"], k=cfg["retrieval"]["k"])
        self.chat = CachedChat(client=client, max_tokens=cfg["llm"]["max_tokens"])
        self.graph = self._build()

    # ---- nodes -------------------------------------------------------------------------------------------------------------------------
    def _guard(self, s: State) -> dict:
        for g in self.guards:
            verdict = g(s["question"])
            if verdict and verdict.get("block"):
                return {"status": "refused_input", "trace": {**s["trace"], "guard": verdict}, "path": s["path"] + ["guard"]}
        return {"path": s["path"] + ["guard"]}

    def _retrieve(self, s: State) -> dict:
        t0 = time.perf_counter()
        if s.get("retrieved") is not None:
            hits = s["retrieved"]
        else:
            hits = [d.metadata["hit"] for d in self.retriever.invoke(s["question"])]
        trace = {**s["trace"], "retrieval_s": round(time.perf_counter() - t0, 3),
                 "hits": [{"rank": h["rank"], "chunk_id": h["chunk_id"], "score": h["score"], "injection_flags": h["injection_flags"]} for h in hits]}
        if self.cfg.get("flagged_chunks") == "exclude":
            hits = [h for h in hits if not h["injection_flags"]]
        floor = self.cfg["abstain"].get("min_top_score")
        out: dict = {"hits": hits, "trace": trace, "path": s["path"] + ["retrieve"]}
        if not hits or (floor is not None and hits[0]["score"] < floor):
            out["status"] = "abstained_no_evidence"
        return out

    def _generate(self, s: State) -> dict:
        trace = dict(s["trace"])
        if s.get("attempt", 0) == 0:
            messages, evidence = prompt_mod.build_messages(s["question"], s["hits"], self.cfg["prompt"]["layers"])
            trace["prompt_version"] = self.cfg["prompt"]["version"]
            trace["evidence"] = {sid: h["chunk_id"] for sid, h in evidence.items()}
        else:
            messages, evidence = s["messages"], s["evidence"]
        try:
            reply: AIMessage = self.chat.invoke(to_messages(messages))
        except Exception as err:  # report the error type only: transport messages can echo request details
            trace["llm_error"] = type(err).__name__
            return {"status": "llm_error", "trace": trace, "path": s["path"] + ["generate"]}
        m = reply.response_metadata
        trace.update(prompt_hash=m["prompt_hash"], cached=m["cached"], usage=m["usage"], llm_s=m["latency_s"], finish_reason=m["finish_reason"], raw_output=reply.content)
        return {"messages": messages, "evidence": evidence, "raw": reply.content, "finish_reason": m["finish_reason"], "trace": trace, "path": s["path"] + ["generate"]}

    def _check(self, s: State) -> dict:
        status, notes, extra = interpret(s["raw"], s["finish_reason"], s["evidence"], self.cfg["prompt"]["layers"], s.get("question"))
        return {"status": status, "extra": extra, "trace": {**s["trace"], **notes}, "path": s["path"] + ["check"]}

    def _recover(self, s: State) -> dict:
        feedback = RETRY_FEEDBACK[s["status"]]
        messages = s["messages"] + [{"role": "assistant", "content": s["raw"]}, {"role": "user", "content": feedback}]
        trace = {**s["trace"], "recovered_from": s["status"], "first_raw_output": s["raw"]}
        return {"messages": messages, "attempt": s.get("attempt", 0) + 1, "status": "", "trace": trace, "path": s["path"] + ["recover"]}

    def _finalize(self, s: State) -> dict:
        return {"path": s["path"] + ["finalize"]}

    # ---- edges -------------------------------------------------------------------------------------------------------------------------
    def _after_guard(self, s: State) -> str:
        return "finalize" if s.get("status") == "refused_input" else "retrieve"

    def _after_retrieve(self, s: State) -> str:
        return "finalize" if s.get("status") == "abstained_no_evidence" else "generate"

    def _after_generate(self, s: State) -> str:
        return "finalize" if s.get("status") == "llm_error" else "check"

    def _after_check(self, s: State) -> str:
        retry = s["status"] in RETRY_FEEDBACK and s.get("attempt", 0) < self.max_retries
        return "recover" if retry else "finalize"

    def _build(self):
        g = StateGraph(State)
        for name, fn in (("guard", self._guard), ("retrieve", self._retrieve), ("generate", self._generate), ("check", self._check),
                         ("recover", self._recover), ("finalize", self._finalize)):
            g.add_node(name, fn)
        g.add_edge(START, "guard")
        g.add_conditional_edges("guard", self._after_guard, {"retrieve": "retrieve", "finalize": "finalize"})
        g.add_conditional_edges("retrieve", self._after_retrieve, {"generate": "generate", "finalize": "finalize"})
        g.add_conditional_edges("generate", self._after_generate, {"check": "check", "finalize": "finalize"})
        g.add_conditional_edges("check", self._after_check, {"recover": "recover", "finalize": "finalize"})
        g.add_edge("recover", "generate")
        g.add_edge("finalize", END)
        return g.compile()

    # ---- public contract (same as Pipeline.answer) ---------------------------------------------------------------------------------------
    def answer(self, question: str, retrieved: list[dict] | None = None) -> dict:
        s: State = self.graph.invoke({"question": question, "retrieved": retrieved, "trace": {}, "path": [], "attempt": 0, "extra": {}})
        extra = dict(s.get("extra", {}))
        trace = {**s["trace"], "graph_path": s["path"]}
        return {"question": question, "status": s["status"], "answer": extra.pop("answer", None), "citations": extra.pop("citations", []),
                "config_id": self.config_id, "trace": trace, **extra}


def load_graph_pipeline(config=DEFAULT_CONFIG, retriever=None, client=None, guards: list[Guard] | None = None) -> GraphPipeline:
    import json
    from ncdqa.llm.client import LLMClient, load_providers
    from ncdqa.llm.env import load_env
    cfg = json.loads(config.read_text(encoding="utf-8"))
    if client is None:
        load_env()
        llm = cfg["llm"]
        provider = load_providers(ROOT / llm["providers_file"])[llm["provider"]]
        client = LLMClient(provider, ROOT / llm["cache_dir"] / f'{llm["provider"]}.jsonl')
    if retriever is None:
        from ncdqa.retrieval.search import Retriever
        retriever = Retriever()
    return GraphPipeline(retriever, client, cfg, guards)
