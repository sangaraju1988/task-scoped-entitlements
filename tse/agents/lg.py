"""Harness (b): LangGraph prebuilt ReAct agent (create_react_agent) with ChatOllama tool calling."""
from __future__ import annotations
import time, json
from typing import List, Optional
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from .. import config
from .prompts import system_prompt, user_prompt

MAX_STEPS = 8


def run(env, task, model: str, temperature=0.0, seed=0, injection=""):
    state = {"final": None}

    @tool
    def run_query(sql: str) -> str:
        """Execute one read-only SQL query and return up to 20 rows."""
        return env.run_query(sql)

    @tool
    def submit_answer(sql: str, answer: str) -> str:
        """Submit the final SQL query (empty string to refuse) and a short natural-language answer. Ends the task."""
        state["final"] = {"sql": sql or "", "answer": answer or ""}
        return "Submitted. Stop now."

    @tool
    def request_access(reason: str, columns: Optional[List[str]] = None, drop_row_filter: Optional[List[str]] = None) -> str:
        """Request additional columns ("table.column") and/or removal of a table's row filter, with a reason."""
        return env.request_access(columns, drop_row_filter, reason)

    tools = [run_query, submit_answer] + ([request_access] if env.can_widen else [])
    llm = ChatOllama(model=model, base_url=config.OLLAMA_URL, temperature=temperature, seed=seed, num_ctx=12288,
                     num_predict=768, reasoning=False)
    agent = create_react_agent(llm, tools, prompt=system_prompt(env))
    t0 = time.perf_counter()
    msgs = []
    err = None
    try:
        for chunk in agent.stream({"messages": [("user", user_prompt(task, injection))]},
                                  {"recursion_limit": 2 * MAX_STEPS + 1}, stream_mode="values"):
            msgs = chunk["messages"]
            if state["final"] is not None:
                break
    except Exception as e:  # recursion limit or model error
        err = type(e).__name__ + ": " + str(e)[:200]
    ptok = otok = ncalls = 0
    for m in msgs:
        u = getattr(m, "usage_metadata", None)
        if u:
            ptok += u.get("input_tokens", 0); otok += u.get("output_tokens", 0); ncalls += 1
    transcript = []
    for m in msgs[1:]:
        d = {"role": m.type, "content": m.content if isinstance(m.content, str) else json.dumps(m.content)}
        if getattr(m, "tool_calls", None):
            d["tool_calls"] = [{"function": {"name": tc["name"], "arguments": tc["args"]}} for tc in m.tool_calls]
        transcript.append(d)
    return {"final": state["final"], "steps": ncalls, "error": err,
            "usage": {"n_calls": ncalls, "prompt_tokens": ptok, "output_tokens": otok},
            "wall_s": time.perf_counter() - t0, "transcript": transcript}
