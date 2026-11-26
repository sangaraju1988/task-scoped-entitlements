"""Claude adapter with the same .chat() interface as tse.llm.LLM, used for the exploratory 'Haiku-5.5 as
inference model' variant. Structured output via output_config.format (JSON schema); cost is recorded in the
same ledger as agent runs and the same spend cap applies."""
import json, time
from .agents.claude_react import client, record, spent_usd, cap_usd, BudgetExceeded

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["tables", "columns", "filters"], "properties": {
    "tables": {"type": "array", "items": {"type": "string"}},
    "columns": {"type": "array", "items": {"type": "string"}},
    "filters": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                           "required": ["table", "column", "op", "value"], "properties": {
        "table": {"type": "string"}, "column": {"type": "string"}, "op": {"type": "string"},
        "value": {"anyOf": [{"type": "string"}, {"type": "number"}, {"type": "array", "items": {"type": "string"}}]}}}}}}


class ClaudeLLM:
    def __init__(self, model="claude-haiku-5-5"):
        self.model = model
        self.calls = []

    def chat(self, messages, tools=None, fmt=None, max_tokens=4000):
        if spent_usd() >= cap_usd():
            raise BudgetExceeded("API spend cap reached")
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        t0 = time.perf_counter()
        r = client().messages.create(model=self.model, max_tokens=max_tokens, system=system, messages=msgs,
                                     output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
        record(self.model, r.usage, "inference")
        self.calls.append({"prompt_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                           "latency_s": time.perf_counter() - t0})
        text = next((b.text for b in r.content if b.type == "text"), "")
        return {"content": text}
