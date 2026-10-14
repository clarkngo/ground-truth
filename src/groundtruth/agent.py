"""Supervisor pattern: a planner decides whether a question needs decomposing, researchers answer each sub-question
from their own retrieval, and a synthesizer writes the final cited answer from their findings and sources."""
import json

from . import ollama, rag
from .config import RunConfig
from .retrieval import Hit, Retriever, doc_ranking

MAX_SUBQUESTIONS = 4
SUB_K = 4
MAX_SOURCES = 10

PLANNER = """You plan how to answer questions about a university's policies, fees, courses and calendar.
Decide whether the question can be answered from one place, or needs several separate lookups, for example:
following a chain of course prerequisites, combining a price with a refund rule, or finding when a course is
offered and then the date that quarter starts.

Reply with JSON only:
{"route": "direct"} or
{"route": "decompose", "sub_questions": ["...", "..."]}
Use at most 4 short, self-contained sub-questions."""

RESEARCHER = rag.SYSTEM + "\nAnswer only the sub-question, in one or two sentences."

SYNTHESIZER = rag.SYSTEM + """
You are given findings from researchers who each answered part of the question, plus the sources they used.
Combine the findings into one answer to the original question. Verify each finding against the sources, and cite
the sources, not the researchers."""


def plan(question: str, config: RunConfig) -> tuple[list[str], ollama.Completion]:
    completion = ollama.chat(config.model, PLANNER, question, json_mode=True)
    try:
        data = json.loads(completion.text)
    except json.JSONDecodeError:
        return [], completion
    subs = (data.get("sub_questions") or []) if data.get("route") == "decompose" else []
    subs = [s for s in subs if isinstance(s, str) and s.strip()][:MAX_SUBQUESTIONS]
    return (subs if len(subs) >= 2 else []), completion


def answer(question: str, retriever: Retriever, config: RunConfig) -> rag.Answer:
    subs, planned = plan(question, config)
    steps = [rag.Step("planner", "route question", planned.text, planned.latency_ms)]
    totals = [planned.latency_ms, planned.prompt_tokens, planned.output_tokens]

    if not subs:
        direct = rag.answer(question, retriever, config)
        direct.steps = steps + direct.steps
        direct.latency_ms += totals[0]
        direct.prompt_tokens += totals[1]
        direct.output_tokens += totals[2]
        return direct

    per_sub: list[list[Hit]] = []
    findings = []
    calcs: list[str] = []
    for sub in subs:
        hits = retriever.search(sub, SUB_K)
        per_sub.append(hits)
        done, sub_calcs = rag.call_model(RESEARCHER, f"Sources:\n\n{rag.format_sources(hits)}\n\nSub-question: {sub}", config)
        calcs += sub_calcs
        findings.append(f"- {sub}\n  Finding: {done.text}")
        steps.append(rag.Step("researcher", sub, done.text, done.latency_ms))
        totals = [totals[0] + done.latency_ms, totals[1] + done.prompt_tokens, totals[2] + done.output_tokens]
    pooled = interleave(per_sub, MAX_SOURCES)

    user = (f"Sources:\n\n{rag.format_sources(pooled)}\n\nResearcher findings:\n" + "\n".join(findings)
            + f"\n\nOriginal question: {question}")
    final, final_calcs = rag.call_model(SYNTHESIZER, user, config)
    calcs += final_calcs
    steps.append(rag.Step("synthesizer", f"{len(findings)} findings, {len(pooled)} sources", final.text, final.latency_ms))
    return rag.Answer(
        question=question,
        text=final.text,
        citations=rag.citations(final.text),
        retrieved_docs=doc_ranking(pooled),
        retrieved_chunks=[h.chunk.id for h in pooled],
        latency_ms=totals[0] + final.latency_ms,
        prompt_tokens=totals[1] + final.prompt_tokens,
        output_tokens=totals[2] + final.output_tokens,
        steps=steps,
        calculations=calcs,
    )


def interleave(rankings: list[list[Hit]], limit: int) -> list[Hit]:
    """Take sources round-robin across sub-questions, so every sub-question keeps its best sources under the cap."""
    pooled: list[Hit] = []
    for rank in range(max((len(r) for r in rankings), default=0)):
        for ranking in rankings:
            if rank < len(ranking) and all(ranking[rank].chunk.id != p.chunk.id for p in pooled):
                pooled.append(ranking[rank])
    return pooled[:limit]
