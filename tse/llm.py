"""Minimal LLM client (Ollama native /api/chat). Records model digest, token counts and latency per call."""
from __future__ import annotations
import json, time, urllib.request
from . import config

_DIGESTS = {}


def model_digest(model: str) -> str:
    if model not in _DIGESTS:
        try:
            tags = json.load(urllib.request.urlopen(config.OLLAMA_URL + "/api/tags", timeout=30))
            _DIGESTS.update({m["name"]: m["digest"][:12] for m in tags["models"]})
        except Exception:
            pass
    return _DIGESTS.get(model, "unknown")


class LLM:
    def __init__(self, model: str, temperature: float = 0.0, seed: int = 0, num_ctx: int = 12288, timeout: int = 600):
        self.model, self.temperature, self.seed, self.num_ctx, self.timeout = model, temperature, seed, num_ctx, timeout
        self.calls = []  # per-call usage records

    def chat(self, messages, tools=None, fmt=None, max_tokens=768):
        body = {"model": self.model, "messages": messages, "stream": False, "think": False,
                "options": {"temperature": self.temperature, "seed": self.seed, "num_ctx": self.num_ctx,
                            "num_predict": max_tokens}}
        if tools:
            body["tools"] = tools
        if fmt:
            body["format"] = fmt
        t0 = time.perf_counter()
        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(config.OLLAMA_URL + "/api/chat", json.dumps(body).encode(),
                                             {"Content-Type": "application/json"})
                r = json.load(urllib.request.urlopen(req, timeout=self.timeout))
                break
            except Exception as e:  # transient server errors
                last = e
                time.sleep(2 + 3 * attempt)
        else:
            raise RuntimeError(f"LLM call failed: {last}")
        self.calls.append({"prompt_tokens": r.get("prompt_eval_count", 0), "output_tokens": r.get("eval_count", 0),
                           "latency_s": time.perf_counter() - t0})
        return r["message"]

    def usage(self):
        return {"n_calls": len(self.calls), "prompt_tokens": sum(c["prompt_tokens"] for c in self.calls),
                "output_tokens": sum(c["output_tokens"] for c in self.calls),
                "llm_latency_s": round(sum(c["latency_s"] for c in self.calls), 3)}
