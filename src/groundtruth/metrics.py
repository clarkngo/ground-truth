"""Deterministic scoring against ground truth. No LLM judge: every pass or fail can be traced to a pattern."""
import re
import statistics

_ABSTAIN = re.compile(
    r"(don'?t|do not|cannot|can't) (know|find|determine|answer)|not (stated|mentioned|specified|provided|included|"
    r"available|covered|listed)|no information|(sources|documents) (do not|don't) (contain|say|include|mention)",
    re.I)


def is_abstention(text: str) -> bool:
    return bool(_ABSTAIN.search(text))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("**", "")).strip()


def _matches(alternative: str, text: str) -> bool:
    if alternative.startswith("re:"):
        return re.search(alternative[3:], text, re.I) is not None
    pattern = r"\s*".join(re.escape(part) for part in alternative.lower().split(" "))
    return re.search(pattern, text) is not None


def missing_groups(answer: str, expect: list[list[str]]) -> list[list[str]]:
    """The expectation groups an answer fails to satisfy (empty means the answer is correct)."""
    text = _normalize(answer)
    return [group for group in expect if not any(_matches(alt, text) for alt in group)]


def score_question(q: dict, answer_text: str, citations: list[str], retrieved_docs: list[str], k_docs: int) -> dict:
    answerable = q["category"] != "unanswerable"
    abstained = is_abstention(answer_text)
    gold = set(q.get("gold_docs", []))

    if answerable:
        missing = missing_groups(answer_text, q["expect"])
        correct = not missing and not abstained
    else:
        missing = []
        correct = abstained

    top = retrieved_docs[:k_docs]
    retrieval = {}
    if gold:
        found = gold & set(top)
        first = next((i for i, d in enumerate(top) if d in gold), None)
        retrieval = {
            "recall": len(found) / len(gold),
            "hit": bool(found),
            "mrr": 0.0 if first is None else 1 / (first + 1),
        }

    return {
        "correct": correct,
        "abstained": abstained,
        "missing": missing,
        # Citations count as valid when every cited id was actually retrieved for this answer.
        "citations_valid": bool(citations) and set(citations) <= set(retrieved_docs) if answerable and not abstained else None,
        "cites_gold": bool(gold & set(citations)) if answerable and not abstained else None,
        **{f"retrieval_{k}": v for k, v in retrieval.items()},
    }


def _rate(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(sum(1 for v in values if v) / len(values), 4) if values else None


def _mean(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 4) if values else None


def summarize(rows: list[dict], retrieval_only: bool) -> dict:
    """Aggregate per-question scores into the headline metrics."""
    s = {
        "questions": len(rows),
        "retrieval_recall": _mean([r.get("retrieval_recall") for r in rows]),
        "retrieval_hit": _rate([r.get("retrieval_hit") for r in rows]),
        "retrieval_mrr": _mean([r.get("retrieval_mrr") for r in rows]),
    }
    if retrieval_only:
        return s
    answerable = [r for r in rows if r["category"] != "unanswerable"]
    unanswerable = [r for r in rows if r["category"] == "unanswerable"]
    latencies = sorted(r["latency_ms"] for r in rows)
    s.update({
        "accuracy": _rate([r["correct"] for r in rows]),
        "answerable_accuracy": _rate([r["correct"] for r in answerable]),
        "correct_refusals": _rate([r["abstained"] for r in unanswerable]),
        "false_refusals": _rate([r["abstained"] for r in answerable]),
        "citation_validity": _rate([r["citations_valid"] for r in answerable]),
        "cites_gold": _rate([r["cites_gold"] for r in answerable]),
        "latency_p50_ms": round(statistics.median(latencies)) if latencies else None,
        "latency_p95_ms": round(latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))]) if latencies else None,
        "calculator_use": _rate([bool(r.get("calculations")) for r in rows if r["category"] in ("numeric", "multi_hop")])
        if any("calculations" in r for r in rows) else None,
        "tokens_per_question": round(statistics.fmean(r["prompt_tokens"] + r["output_tokens"] for r in rows)) if rows else None,
    })
    return s
