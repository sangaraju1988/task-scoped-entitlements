"""Harness (a): plain function-calling ReAct loop over Ollama native tool calls.
Falls back to parsing a JSON tool call from message text for models that emit tools as text."""
from __future__ import annotations
import json, re, time
from ..llm import LLM
from .prompts import system_prompt, tools_for, user_prompt

MAX_STEPS = 8


def _parse_text_tool(content: str):
    m = re.search(r"\{.*\}", content or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    name = d.get("name") or d.get("tool")
    args = d.get("arguments") or d.get("parameters") or d.get("args") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if name in ("run_query", "submit_answer", "request_access"):
        return [{"function": {"name": name, "arguments": args}}]
    return None


def run(env, task, model: str, temperature=0.0, seed=0, injection=""):
    llm = LLM(model, temperature=temperature, seed=seed)
    msgs = [{"role": "system", "content": system_prompt(env)}, {"role": "user", "content": user_prompt(task, injection)}]
    tools = tools_for(env)
    final = None
    steps = 0
    nudged = False
    t0 = time.perf_counter()
    while steps < MAX_STEPS:
        steps += 1
        m = llm.chat(msgs, tools=tools)
        calls = m.get("tool_calls") or _parse_text_tool(m.get("content", ""))
        msgs.append({"role": "assistant", "content": m.get("content", ""), **({"tool_calls": m["tool_calls"]} if m.get("tool_calls") else {})})
        if not calls:
            if nudged:
                break
            nudged = True
            msgs.append({"role": "user", "content": "Please continue by calling one of the tools (run_query, submit_answer"
                         + (", request_access" if env.can_widen else "") + ")."})
            continue
        for call in calls[:1]:  # one action per step
            name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if name == "run_query":
                out = env.run_query(str(args.get("sql", "")))
            elif name == "request_access":
                out = env.request_access(args.get("columns"), args.get("drop_row_filter"), args.get("reason", ""))
            elif name == "submit_answer":
                final = {"sql": str(args.get("sql", "") or ""), "answer": str(args.get("answer", "") or "")}
                out = "Submitted."
            else:
                out = f"ERROR: unknown tool {name}"
            msgs.append({"role": "tool", "content": out, "tool_name": name})
        if final is not None:
            break
    return {"final": final, "steps": steps, "usage": llm.usage(), "wall_s": time.perf_counter() - t0,
            "transcript": msgs[1:]}
