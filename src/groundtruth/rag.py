import re
from dataclasses import dataclass, field

from . import calculator, ollama
from .config import RunConfig
from .corpus import load_corpus
from .retrieval import Hit, Retriever, doc_ranking

ABSTAIN = "I don't know based on the provided sources."

SYSTEM = f"""You answer questions about Larkspur Institute of Technology using ONLY the sources provided.

Rules:
- Cite the source id in square brackets after every claim, for example [pol-grading].
- When one policy replaces another (see "effective" and "supersedes"), use the newer one unless the question asks
  about an earlier year.
- For calculations, show the arithmetic in one line.
- If the sources do not contain the answer, reply exactly: {ABSTAIN}
- Be concise: two to four sentences."""

_CITATION = re.compile(r"\[([a-z0-9][a-z0-9.\-]*(?:\s*,\s*[a-z0-9][a-z0-9.\-]*)*)\]")


@dataclass
class Step:
    agent: str
    detail: str
    output: str
    latency_ms: float


@dataclass
class Answer:
    question: str
    text: str
    citations: list[str]
    retrieved_docs: list[str]
    retrieved_chunks: list[str]
    latency_ms: float
    prompt_tokens: int
    output_tokens: int
    steps: list[Step] = field(default_factory=list)
    calculations: list[str] = field(default_factory=list)


def system_prompt(base: str, config: RunConfig) -> str:
    if not config.calculator:
        return base
    return base.replace("- For calculations, show the arithmetic in one line.\n", "") + "\n" + calculator.TOOL_RULE


def call_model(system: str, user: str, config: RunConfig) -> tuple[ollama.Completion, list[str]]:
    """One model turn. With the calculator enabled, the model gets a real `calculate` tool via function calling."""
    if not config.calculator:
        return ollama.chat(config.model, system, user), []
    completion, calls = ollama.chat_with_tools(config.model, system_prompt(system, config), user,
                                               [calculator.TOOL], calculator.run_tool)
    completion.text, inline = finish(completion.text, config)  # fallback if a model writes {{expr}} anyway
    return completion, calls + inline


def finish(text: str, config: RunConfig) -> tuple[str, list[str]]:
    """Applies the calculator if enabled. Returns the final text and the calculations it performed."""
    if not config.calculator:
        return text, []
    text, calls = calculator.substitute(text)
    return text, [f"{e} = {r}" for e, r in calls]


def format_sources(hits: list[Hit]) -> str:
    docs = load_corpus()
    blocks = []
    for h in hits:
        d = docs[h.chunk.doc_id]
        meta = f"effective {d.effective}" + (f", supersedes {d.supersedes}" if d.supersedes else "")
        heading = f" > {h.chunk.heading}" if h.chunk.heading else ""
        blocks.append(f"[{d.id}] {d.title}{heading} ({meta})\n{h.chunk.text}")
    return "\n\n".join(blocks)


def citations(text: str) -> list[str]:
    known = load_corpus()
    out: list[str] = []
    for c in _CITATION.findall(text):
        for part in c.split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    # Keep unknown ids too: citing a source that doesn't exist is exactly what citation validity should catch.
    return [c for c in out if c in known or "-" in c]


def generate(question: str, hits: list[Hit], config: RunConfig) -> tuple[ollama.Completion, list[str]]:
    user = f"Sources:\n\n{format_sources(hits)}\n\nQuestion: {question}"
    return call_model(SYSTEM, user, config)


def answer(question: str, retriever: Retriever, config: RunConfig) -> Answer:
    hits = retriever.search(question)
    completion, calcs = generate(question, hits, config)
    return Answer(
        question=question,
        text=completion.text,
        citations=citations(completion.text),
        retrieved_docs=doc_ranking(hits),
        retrieved_chunks=[h.chunk.id for h in hits],
        latency_ms=completion.latency_ms,
        prompt_tokens=completion.prompt_tokens,
        output_tokens=completion.output_tokens,
        steps=[Step("rag", f"retrieved {len(hits)} chunks" + (f", calculated {'; '.join(calcs)}" if calcs else ""),
                    completion.text, completion.latency_ms)],
        calculations=calcs,
    )
