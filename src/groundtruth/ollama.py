import os
import re
import time
from dataclasses import dataclass

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_client = httpx.Client(base_url=OLLAMA_URL, timeout=600)


@dataclass
class Completion:
    text: str
    prompt_tokens: int
    output_tokens: int
    latency_ms: float


def chat(model: str, system: str, user: str, json_mode: bool = False) -> Completion:
    """Deterministic chat call: temperature 0 and a fixed seed, so reruns of an experiment are comparable."""
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0, "seed": 42, "num_ctx": 8192},
    }
    if json_mode:
        body["format"] = "json"
    if model.startswith("qwen3"):
        body["think"] = False
    started = time.perf_counter()
    r = _client.post("/api/chat", json=body)
    r.raise_for_status()
    data = r.json()
    text = re.sub(r"<think>.*?</think>", "", data["message"]["content"], flags=re.S).strip()
    return Completion(text, data.get("prompt_eval_count", 0), data.get("eval_count", 0),
                      (time.perf_counter() - started) * 1000)


def chat_with_tools(model: str, system: str, user: str, tools: list[dict], run_tool, max_rounds: int = 6) -> tuple[Completion, list[str]]:
    """Native function calling: the model may call tools, we run them and send results back, until it answers."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    calls: list[str] = []
    prompt_tokens = output_tokens = 0
    started = time.perf_counter()
    for _ in range(max_rounds):
        body = {"model": model, "messages": messages, "tools": tools, "stream": False,
                "options": {"temperature": 0, "seed": 42, "num_ctx": 8192}}
        if model.startswith("qwen3"):
            body["think"] = False
        r = _client.post("/api/chat", json=body)
        r.raise_for_status()
        data = r.json()
        prompt_tokens += data.get("prompt_eval_count", 0)
        output_tokens += data.get("eval_count", 0)
        message = data["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            text = re.sub(r"<think>.*?</think>", "", message.get("content", ""), flags=re.S).strip()
            return Completion(text, prompt_tokens, output_tokens, (time.perf_counter() - started) * 1000), calls
        messages.append(message)
        for call in tool_calls:
            fn = call["function"]
            result = run_tool(fn["name"], fn.get("arguments") or {})
            calls.append(f"{fn.get('arguments', {}).get('expression', '')} = {result}")
            messages.append({"role": "tool", "content": result, "tool_name": fn["name"]})
    return Completion("I don't know based on the provided sources.", prompt_tokens, output_tokens,
                      (time.perf_counter() - started) * 1000), calls


def embed(model: str, texts: list[str]) -> list[list[float]]:
    r = _client.post("/api/embed", json={"model": model, "input": texts})
    r.raise_for_status()
    return r.json()["embeddings"]


def available() -> bool:
    try:
        return _client.get("/api/tags", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False
