"""Fixed answer pipeline (decision H1 option A, still the owner's to confirm):

    question -> input guards -> retrieve -> evidence gate -> prompt -> LLM -> validate -> answer | abstain

Every step writes into the returned trace, so a run can be logged, scored and compared (ablation over the prompt layers).
Input guards (PII, scope: decisions G1/G3) are plain callables passed in; none are installed until the owner decides.
The model has no tools: the only side effect of any text it reads is the text it returns (least privilege).

    from ncdqa.rag.pipeline import load_pipeline
    p = load_pipeline()                    # Retriever + Typhoon client from configs/rag/generate_v1.json
    result = p.answer("ค่า HbA1c เป้าหมายในผู้ป่วยเบาหวานคือเท่าไร")
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable

from . import prompt as prompt_mod
from .validate import validate

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs/rag/generate_v1.json"
Guard = Callable[[str], "dict | None"]   # returns {"block": True, "reason": ...} to stop the question before any LLM call


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


class Pipeline:
    def __init__(self, retriever, client, cfg: dict, guards: list[Guard] | None = None):
        self.retriever, self.client, self.cfg, self.guards = retriever, client, cfg, guards or []
        self.config_id = f'{cfg["id"]}-{config_hash(cfg)}'

    def _result(self, question: str, status: str, trace: dict, **extra) -> dict:
        return {"question": question, "status": status, "answer": extra.pop("answer", None), "citations": extra.pop("citations", []),
                "config_id": self.config_id, "trace": trace, **extra}

    def answer(self, question: str, retrieved: list[dict] | None = None) -> dict:
        """`retrieved` lets a harness inject hits (cached retrieval, or a test copy with a planted instruction)."""
        cfg, layers, trace = self.cfg, self.cfg["prompt"]["layers"], {}
        for guard in self.guards:
            verdict = guard(question)
            if verdict and verdict.get("block"):
                trace["guard"] = verdict
                return self._result(question, "refused_input", trace)

        t0 = time.perf_counter()
        hits = retrieved if retrieved is not None else self.retriever.search(question, cfg["retrieval"]["variant"], cfg["retrieval"]["k"])
        trace["retrieval_s"] = round(time.perf_counter() - t0, 3)
        trace["hits"] = [{"rank": h["rank"], "chunk_id": h["chunk_id"], "score": h["score"], "injection_flags": h["injection_flags"]} for h in hits]
        if cfg.get("flagged_chunks") == "exclude":
            hits = [h for h in hits if not h["injection_flags"]]
        floor = cfg["abstain"].get("min_top_score")
        if not hits or (floor is not None and hits[0]["score"] < floor):
            return self._result(question, "abstained_no_evidence", trace)

        messages, evidence = prompt_mod.build_messages(question, hits, layers)
        trace["prompt_version"] = cfg["prompt"]["version"]
        trace["evidence"] = {sid: h["chunk_id"] for sid, h in evidence.items()}   # S-id -> chunk id, so a metric can re-read the exact context
        try:
            resp = self.client.complete(messages, max_tokens=cfg["llm"]["max_tokens"])
        except Exception as err:  # report the error type only: transport messages can echo request details
            trace["llm_error"] = type(err).__name__
            return self._result(question, "llm_error", trace)
        trace.update(prompt_hash=resp.prompt_hash, cached=resp.cached, usage=resp.usage, llm_s=resp.latency_s,
                     finish_reason=resp.finish_reason, raw_output=resp.text)

        status, notes, extra = interpret(resp.text, resp.finish_reason, evidence, layers, question)
        trace.update(notes)
        return self._result(question, status, trace, **extra)


def interpret(raw: str, finish_reason: str | None, evidence: dict[str, dict], layers: dict, question: str | None = None) -> tuple[str, dict, dict]:
    """The step after the model has answered: parse, validate and shape the answer. Shared by the plain pipeline and the graph version.
    Returns (status, trace notes, extra result fields: answer / claims / citations)."""
    if not layers.get("schema", True):     # free-text mode: nothing to parse or cite; the text is the answer
        text = raw.strip()
        return ("answered" if text else "abstained_model"), {}, {"answer": text or None}
    checked = ({sid: {**h, "text": prompt_mod.shown_text(h, layers)} for sid, h in evidence.items()} if layers.get("evidence_header") else evidence)   # validate against what the model saw
    v = validate(raw, checked, check_claims=layers.get("validator", True), check_tokens=layers.get("validator_tokens", False),
                 question=question if (layers.get("validator_question_numbers", False) or layers.get("validator_population", False)) else None,
                 own_numbers=layers.get("validator_question_numbers", False), reattribute=layers.get("validator_reattribute", False),
                 drop_denials=layers.get("validator_drop_denials", False), population=layers.get("validator_population", False))
    notes: dict = {"dropped_claims": v.dropped}
    if v.repaired:
        notes["repaired_claims"] = v.repaired
    if not v.parsed:
        notes["problem"] = v.problem
        return ("truncated" if finish_reason == "length" else "parse_error"), notes, {}
    if v.abstain:
        return "abstained_model", notes, {}
    if not v.kept:
        return "abstained_validator", notes, {}
    used = sorted({s for c in v.kept for s in c["cite"]}, key=lambda s: int(s[1:]))
    citations = [{"id": s, "chunk_id": evidence[s]["chunk_id"], "document_id": evidence[s]["document_id"],
                  "edition_id": evidence[s]["edition_id"], "pdf_pages": prompt_mod.pages(evidence[s])} for s in used]
    text = " ".join(f'{c["text"]} [{",".join(c["cite"])}]' for c in v.kept)
    return "answered", notes, {"answer": text, "claims": v.kept, "citations": citations}


def load_pipeline(config: Path = DEFAULT_CONFIG, retriever=None, client=None, guards: list[Guard] | None = None) -> Pipeline:
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
    return Pipeline(retriever, client, cfg, guards)
