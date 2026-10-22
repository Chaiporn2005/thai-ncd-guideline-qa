"""ReAct agent with native tool calling, written as a LangGraph StateGraph (Track C). Same tools, prompt and final check as react_agent.py (both use react_core.py).

    START -> guard -> agent --(tool calls and rounds left)--> tools --> agent ...
                 |         \\--(text reply, or the round limit)--> finalize -> END
                 \\-- refused -> finalize

The agent node asks the model; the tools node runs the tool calls; a conditional edge sends the flow back to the agent while there are tool calls and rounds left. At the
limit the agent node asks for a final answer without tools. This is the structure of LangGraph's prebuilt ReAct agent, written out so the cache, the tools, the validator and
the trace are exactly those of the plain version: a difference in results against react_agent.py can only come from orchestration.
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ncdqa.llm.tool_llm import ToolLLM

from . import react_core as core
from .pipeline import Guard, config_hash


class State(TypedDict, total=False):
    question: str
    messages: list[dict]
    rounds: int
    final: str
    finish_reason: str | None
    status: str
    guard: dict
    usages: list[dict]
    cached: list[bool]
    path: list[str]
    error: str
    nudge: bool
    nudged: bool
    selecting: bool
    converged: bool


class GraphReactAgent:
    def __init__(self, retriever, client, cfg: dict, guards: list[Guard] | None = None):
        self.retriever, self.cfg, self.guards = retriever, cfg, guards or []
        self.llm = ToolLLM.from_client(client)
        self.config_id = f'{cfg["id"]}-{config_hash(cfg)}'
        self.s = core.agent_settings(cfg)
        self._box: core.ToolBox | None = None          # one question at a time per agent object
        self.graph = self._build()

    def _guard(self, s: State) -> dict:
        for g in self.guards:
            v = g(s["question"])
            if v and v.get("block"):
                return {"status": "refused_input", "guard": v, "path": s["path"] + ["guard"]}
        return {"path": s["path"] + ["guard"]}

    def _agent(self, s: State) -> dict:
        force = s["rounds"] >= self.s["max_steps"] or s.get("selecting", False)
        messages = s["messages"] + ([{"role": "user", "content": core.force_message(self._box)}] if force else [])
        try:
            r = self.llm.chat(messages, None if force else core.TOOLS, self.s["max_tokens"])
        except Exception as err:
            return {"status": "llm_error", "error": type(err).__name__, "path": s["path"] + ["agent"]}
        msg = r["message"]
        calls = [] if force else (msg.get("tool_calls") or [])[:core.MAX_CALLS_PER_ROUND]
        out: dict[str, Any] = {"usages": s["usages"] + [r["usage"]], "cached": s["cached"] + [r["cached"]], "path": s["path"] + ["agent"], "messages": messages}
        out["nudge"] = False
        if calls:
            out["messages"] = messages + [{**msg, "tool_calls": calls}]
        elif self.s["search_first"] and not self._box.steps and not s.get("nudged") and not force:     # answered or abstained without searching: ask once for a search
            out.update(nudge=True, nudged=True, path=s["path"] + ["agent", "nudge"], messages=messages + [{"role": "assistant", "content": msg.get("content") or ""},
                                                                                                      {"role": "user", "content": core.NUDGE}])
        elif not force and core.needs_final_call(self._box):      # a voluntary answer, but more evidence was seen than may be cited: ask again with the selected ids
            out.update(nudge=True, selecting=True, path=s["path"] + ["agent", "select"], messages=s["messages"])
        else:
            out.update(final=msg.get("content") or "", finish_reason=r["finish_reason"])
        return out

    def _tools(self, s: State) -> dict:
        calls = s["messages"][-1]["tool_calls"]
        outputs = [self._box.run(c) for c in calls]
        rounds = s["rounds"] + 1
        if self._box.converged:                       # the last search brought nothing new: stop searching, answer next
            rounds = max(rounds, self.s["max_steps"])
        return {"messages": s["messages"] + core.tool_messages(calls, outputs), "rounds": rounds, "path": s["path"] + ["tools"]}

    def _after_guard(self, s: State) -> str:
        return "finalize" if s.get("status") == "refused_input" else "agent"

    def _after_agent(self, s: State) -> str:
        if s.get("status") == "llm_error" or "final" in s:
            return "finalize"
        return "agent" if s.get("nudge") else "tools"

    def _finalize(self, s: State) -> dict:
        return {"path": s["path"] + ["finalize"]}

    def _build(self):
        g = StateGraph(State)
        for name, fn in (("guard", self._guard), ("agent", self._agent), ("tools", self._tools), ("finalize", self._finalize)):
            g.add_node(name, fn)
        g.add_edge(START, "guard")
        g.add_conditional_edges("guard", self._after_guard, {"agent": "agent", "finalize": "finalize"})
        g.add_conditional_edges("agent", self._after_agent, {"tools": "tools", "agent": "agent", "finalize": "finalize"})
        g.add_edge("tools", "agent")
        g.add_edge("finalize", END)
        return g.compile()

    def answer(self, question: str, retrieved: list[dict] | None = None) -> dict:
        self._box = core.new_box(self.retriever, self.cfg, question)
        t0 = time.perf_counter()
        messages = core.start_messages(question)
        path: list[str] = []
        if self.s["seed"]:
            messages = messages + core.seed_messages(self._box, question)
            path.append("seed")
        s = self.graph.invoke({"question": question, "messages": messages, "rounds": 0, "usages": [], "cached": [], "path": path},
                              {"recursion_limit": 6 * (self.s["max_steps"] + 2)})
        if s.get("status") == "refused_input":
            return core.make_result(self.config_id, question, "refused_input", {"guard": s["guard"], "react_path": s["path"]})
        trace = core.trace_summary(self._box, s.get("usages", []), s.get("cached", []), time.perf_counter() - t0)
        if s.get("status") == "llm_error":
            return core.make_result(self.config_id, question, "llm_error", {**trace, "llm_error": s["error"], "react_path": s["path"]})
        status, notes, extra = core.finish(s["final"], s["finish_reason"], self._box, self.cfg["prompt"]["layers"])
        trace.update(notes)
        trace.update(raw_output=s["final"], finish_reason=s["finish_reason"], react_path=s["path"], forced_final=s["rounds"] >= self.s["max_steps"], selected_final=s.get("selecting", False), rounds=s["rounds"])
        return core.make_result(self.config_id, question, status, trace, extra)
