"""HTTP API for asking live questions. Experiment results are served to the dashboard as static files."""
from functools import cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import agent, ollama, rag
from .config import load_configs
from .retrieval import Retriever

app = FastAPI(title="Ground Truth", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    config: str = "baseline"


@cache
def _retriever(name: str) -> Retriever:
    return Retriever(load_configs()[name])


@app.get("/api/health")
def health():
    return {"ollama": ollama.available()}


@app.get("/api/configs")
def configs():
    return [{"name": c.name, "description": c.description, **c.params()}
            for c in load_configs().values() if not c.retrieval_only]


@app.post("/api/ask")
def ask(req: AskRequest):
    configs = load_configs()
    config = configs.get(req.config)
    if config is None or config.retrieval_only:
        raise HTTPException(400, f"unknown or retrieval-only config '{req.config}'")
    if not ollama.available():
        raise HTTPException(503, "Ollama is not running")
    pipeline = agent.answer if config.pipeline == "agent" else rag.answer
    a = pipeline(req.question, _retriever(config.name), config)
    return {
        "question": a.question, "answer": a.text, "citations": a.citations, "retrieved_docs": a.retrieved_docs,
        "retrieved_chunks": a.retrieved_chunks, "latency_ms": round(a.latency_ms),
        "tokens": a.prompt_tokens + a.output_tokens, "steps": [s.__dict__ for s in a.steps],
    }
