"""Harness (a) for Claude models: manual tool-use loop on the Anthropic Messages API (official SDK).

Same system prompt, tools and step budget as the Ollama ReAct harness (tse/agents/react.py).
* Prompt caching: automatic top-level cache_control (the stable prefix = tools + system prompt with schema,
  then the growing transcript, is reused across turns).
* Thinking: model default (adaptive); effort fixed explicitly to EFFORT for every condition. These models
  reject non-default sampling parameters, so no temperature/seed is sent (decoding is not seed-controllable).
* Cost: computed from response.usage and appended to a global ledger; a hard cap (TSE_API_CAP_USD,
  default 95) raises BudgetExceeded before any request that would start after the cap is reached.
* Refusals (stop_reason == "refusal") end the run and are recorded; no server-side model fallback is used,
  because a fallback model would confound the per-model comparison.
"""
from __future__ import annotations
import json, os, time, threading
import anthropic
from .. import config
from .prompts import system_prompt, tools_for, user_prompt

MAX_STEPS = 8
EFFORT = "medium"
# USD per million tokens: (input, 5-min cache write, cache read, output) - Anthropic pricing page, 2026-11-26
PRICES = {"claude-haiku-5-5": (0.10, 0.125, 0.01, 0.50), "claude-sonnet-5-5": (2.00, 2.50, 0.10, 10.00)}
LEDGER = os.path.join(config.RESULTS, "api_spend.jsonl")
_lock = threading.Lock()


class BudgetExceeded(RuntimeError):
    pass


def spent_usd():
    if not os.path.exists(LEDGER):
        return 0.0
    return sum(json.loads(l)["usd"] for l in open(LEDGER))


def cap_usd():
    return float(os.environ.get("TSE_API_CAP_USD", "95"))


def cost_of(model, u):
    pin, pw, pr, pout = PRICES[model]
    return ((u.input_tokens or 0) * pin + (u.cache_creation_input_tokens or 0) * pw +
            (u.cache_read_input_tokens or 0) * pr + (u.output_tokens or 0) * pout) / 1e6


def record(model, u, tag):
    usd = cost_of(model, u)
    with _lock:
        with open(LEDGER, "a") as f:
            f.write(json.dumps({"t": time.time(), "model": model, "tag": tag, "usd": usd,
                                "input": u.input_tokens, "cache_write": u.cache_creation_input_tokens,
                                "cache_read": u.cache_read_input_tokens, "output": u.output_tokens}) + "\n")
    return usd


_client = None
def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=6)  # SDK retries 408/409/429/5xx with backoff
    return _client


def to_anthropic_tools(tools):
    return [{"name": t["function"]["name"], "description": t["function"]["description"],
             "input_schema": t["function"]["parameters"]} for t in tools]


def run(env, task, model: str, temperature=0.0, seed=0, injection=""):
    if spent_usd() >= cap_usd():
        raise BudgetExceeded(f"API spend cap reached (${cap_usd():.2f})")
    c = client()
    tools = to_anthropic_tools(tools_for(env))
    system = system_prompt(env)
    msgs = [{"role": "user", "content": user_prompt(task, injection)}]
    final, steps, usd = None, 0, 0.0
    ptok = otok = cread = cwrite = 0
    stop = None
    t0 = time.perf_counter()
    transcript = []
    while steps < MAX_STEPS:
        steps += 1
        r = c.messages.create(model=model, max_tokens=8000, system=system, tools=tools, messages=msgs,
                              cache_control={"type": "ephemeral"}, output_config={"effort": EFFORT})
        usd += record(model, r.usage, task["task_id"])
        ptok += r.usage.input_tokens or 0; otok += r.usage.output_tokens or 0
        cread += r.usage.cache_read_input_tokens or 0; cwrite += r.usage.cache_creation_input_tokens or 0
        stop = r.stop_reason
        msgs.append({"role": "assistant", "content": r.content})  # thinking blocks passed back unchanged
        transcript.append({"role": "assistant", "content": " ".join(b.text for b in r.content if b.type == "text"),
                           "tool_calls": [{"function": {"name": b.name, "arguments": b.input}} for b in r.content if b.type == "tool_use"]})
        if stop == "refusal":
            break
        uses = [b for b in r.content if b.type == "tool_use"]
        if not uses:
            break
        results = []
        for b in uses:
            args = b.input if isinstance(b.input, dict) else {}
            if b.name == "run_query":
                out = env.run_query(str(args.get("sql", "")))
            elif b.name == "request_access":
                out = env.request_access(args.get("columns"), args.get("drop_row_filter"), args.get("reason", ""))
            elif b.name == "submit_answer":
                final = {"sql": str(args.get("sql", "") or ""), "answer": str(args.get("answer", "") or "")}
                out = "Submitted."
            else:
                out = f"ERROR: unknown tool {b.name}"
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            transcript.append({"role": "tool", "tool_name": b.name, "content": out})
        msgs.append({"role": "user", "content": results})  # all results of one turn in one message
        if final is not None:
            break
    return {"final": final, "steps": steps, "stop_reason": stop, "wall_s": time.perf_counter() - t0,
            "usage": {"n_calls": steps, "prompt_tokens": ptok, "output_tokens": otok, "cache_read": cread,
                      "cache_write": cwrite, "usd": usd},
            "transcript": transcript}
