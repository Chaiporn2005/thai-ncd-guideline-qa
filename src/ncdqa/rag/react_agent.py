"""ReAct agent with native tool calling, written as a plain Python loop (Track C). Same tools, prompt and final check as react_graph.py (both use react_core.py).

    agent = ReactAgent(retriever, client, cfg)          # client: an LLMClient; its provider and cache location are reused (the cache file gets the suffix _tools)
    result = agent.answer("...")                        # the same result dict as Pipeline.answer; trace has tool_steps, hits, evidence, usage

Loop: ask the model with the tools; if it calls tools, run them (at most 3 per round), append the results and ask again; if it answers in text, that is the final reply.
After `max_steps` rounds of tool calls the model is told to answer now without tools. `retrieved` is accepted for interface compatibility and ignored: the agent searches itself.
"""

from __future__ import annotations

import time

from ncdqa.llm.tool_llm import ToolLLM

from . import react_core as core
from .pipeline import Guard, config_hash


class ReactAgent:
    def __init__(self, retriever, client, cfg: dict, guards: list[Guard] | None = None):
        self.retriever, self.cfg, self.guards = retriever, cfg, guards or []
        self.llm = ToolLLM.from_client(client)
        self.config_id = f'{cfg["id"]}-{config_hash(cfg)}'
        self.s = core.agent_settings(cfg)

    def answer(self, question: str, retrieved: list[dict] | None = None) -> dict:
        for g in self.guards:
            v = g(question)
            if v and v.get("block"):
                return core.make_result(self.config_id, question, "refused_input", {"guard": v, "react_path": ["guard"]})
        box = core.new_box(self.retriever, self.cfg, question)
        messages, usages, cached, path = core.start_messages(question), [], [], ["guard"]
        final, finish_reason, nudged = "", None, False
        if self.s["seed"]:
            messages = messages + core.seed_messages(box, question)
            path.append("seed")
        t0 = time.perf_counter()
        rounds, selecting = 0, False                 # rounds of tool calls (a nudge or the final answer is not a round); selecting: final answer asked for with the selected evidence
        while True:
            force = rounds >= self.s["max_steps"] or selecting
            if force:
                messages = messages + [{"role": "user", "content": core.force_message(box)}]
            try:
                r = self.llm.chat(messages, None if force else core.TOOLS, self.s["max_tokens"])
            except Exception as err:  # report the error type only: transport messages can echo request details
                trace = core.trace_summary(box, usages, cached, time.perf_counter() - t0)
                return core.make_result(self.config_id, question, "llm_error", {**trace, "llm_error": type(err).__name__, "react_path": path})
            usages.append(r["usage"])
            cached.append(r["cached"])
            msg = r["message"]
            calls = [] if force else (msg.get("tool_calls") or [])[:core.MAX_CALLS_PER_ROUND]
            path.append("agent")
            if calls:
                outputs = [box.run(c) for c in calls]
                path.append("tools")
                rounds += 1
                if box.converged:                    # the last search brought nothing new: stop searching, answer next
                    rounds = max(rounds, self.s["max_steps"])
                messages = messages + [{**msg, "tool_calls": calls}] + core.tool_messages(calls, outputs)
                continue
            if self.s["search_first"] and not box.steps and not nudged and not force:     # the model answered or abstained without searching: ask once for a search
                nudged = True
                messages = messages + [{"role": "assistant", "content": msg.get("content") or ""}, {"role": "user", "content": core.NUDGE}]
                path.append("nudge")
                continue
            if not force and core.needs_final_call(box):      # a voluntary answer, but more evidence was seen than may be cited: ask again with the selected ids
                selecting = True
                path.append("select")
                continue
            final, finish_reason = msg.get("content") or "", r["finish_reason"]
            break
        status, notes, extra = core.finish(final, finish_reason, box, self.cfg["prompt"]["layers"])
        trace = {**core.trace_summary(box, usages, cached, time.perf_counter() - t0), **notes, "raw_output": final, "finish_reason": finish_reason,
                 "react_path": path + ["finalize"], "forced_final": rounds >= self.s["max_steps"], "selected_final": selecting, "rounds": rounds}
        return core.make_result(self.config_id, question, status, trace, extra)
