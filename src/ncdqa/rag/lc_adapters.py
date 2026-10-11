"""Thin LangChain adapters (langchain-core only) around the project's own retriever and cached LLM client (Track C).

Why adapters and not LangChain's own chains: the retriever and the LLM client are already measured (Track B's frozen settings, a request cache that makes
runs repeatable). The adapters expose them through the standard `BaseRetriever` / `BaseChatModel` interfaces, so the graph nodes talk to the same
interfaces any LangChain component would, while the behaviour and the cache stay exactly what was evaluated. No tracing service is used.
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.retrievers import BaseRetriever

ROLES = {SystemMessage: "system", HumanMessage: "user", AIMessage: "assistant"}


def to_dicts(messages: list[BaseMessage]) -> list[dict]:
    return [{"role": ROLES[type(m)], "content": m.content} for m in messages]


def to_messages(dicts: list[dict]) -> list[BaseMessage]:
    cls = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
    return [cls[d["role"]](content=d["content"]) for d in dicts]


class GuidelineRetriever(BaseRetriever):
    """Wraps `Retriever.search(query, variant, k)`; every hit dict travels in `Document.metadata["hit"]` so nothing is lost."""
    retriever: Any
    variant: str = "B"
    k: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return [Document(page_content=h["text"], metadata={"hit": h}) for h in self.retriever.search(query, self.variant, self.k)]


class CachedChat(BaseChatModel):
    """Wraps `LLMClient.complete` (request cache, fixed sampling settings). Cache hit, usage and finish reason come back in `response_metadata`."""
    client: Any
    max_tokens: int = 1000

    @property
    def _llm_type(self) -> str:
        return "ncdqa-cached-client"

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        resp = self.client.complete(to_dicts(messages), max_tokens=self.max_tokens)
        meta = {"cached": resp.cached, "usage": resp.usage, "prompt_hash": resp.prompt_hash, "finish_reason": resp.finish_reason, "latency_s": resp.latency_s}
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=resp.text, response_metadata=meta))])
