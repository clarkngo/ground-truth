import json
import time
from collections import defaultdict
from datetime import datetime, timezone

import yaml

from . import agent, rag
from .config import RunConfig
from .metrics import score_question, summarize
from .rag import citations as parse_citations
from .paths import QUESTIONS_FILE, RESULTS_DIR, ROOT
from .retrieval import Retriever, doc_ranking


def load_questions() -> list[dict]:
    return yaml.safe_load(QUESTIONS_FILE.read_text())["questions"]


def run(config: RunConfig, limit: int | None = None, log=print) -> dict:
    questions = load_questions()[:limit] if limit else load_questions()
    retriever = Retriever(config)
    pipeline = agent.answer if config.pipeline == "agent" else rag.answer
    started = time.time()
    rows = []
    for i, q in enumerate(questions, 1):
        if config.retrieval_only:
            hits = retriever.search(q["question"])
            docs = doc_ranking(hits)
            row = {"id": q["id"], "category": q["category"], "retrieved_docs": docs,
                   **score_question(q, "", [], docs, len(docs))}
            for key in ("correct", "abstained", "missing", "citations_valid", "cites_gold"):
                row.pop(key, None)
        else:
            a = pipeline(q["question"], retriever, config)
            row = {
                "id": q["id"], "category": q["category"], "answer": a.text, "citations": a.citations,
                "retrieved_docs": a.retrieved_docs, "retrieved_chunks": a.retrieved_chunks,
                "latency_ms": round(a.latency_ms), "prompt_tokens": a.prompt_tokens, "output_tokens": a.output_tokens,
                "steps": [s.__dict__ for s in a.steps], "calculations": a.calculations,
                **score_question(q, a.text, a.citations, a.retrieved_docs, len(a.retrieved_docs)),
            }
            mark = "ok " if row["correct"] else "MISS"
            log(f"  [{i:>2}/{len(questions)}] {mark} {q['id']} {round(a.latency_ms / 1000, 1)}s")
        rows.append(row)

    by_category = defaultdict(list)
    for r in rows:
        by_category[r["category"]].append(r)
    result = {
        "config": {"name": config.name, "description": config.description, **config.params()},
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(time.time() - started, 1),
        "summary": summarize(rows, config.retrieval_only),
        "by_category": {c: summarize(rs, config.retrieval_only) for c, rs in sorted(by_category.items())},
        "questions": rows,
    }
    _drop_tool_metrics(result)
    save(result)
    log_mlflow(result)
    return result


def rescore(result: dict) -> dict:
    """Re-score saved answers against the current questions and scorer, without calling a model."""
    questions = {q["id"]: q for q in load_questions()}
    rows = []
    for row in result["questions"]:
        q = questions[row["id"]]
        if "answer" in row:
            row["citations"] = parse_citations(row["answer"])
            score = score_question(q, row["answer"], row["citations"], row["retrieved_docs"], len(row["retrieved_docs"]))
        else:
            score = score_question(q, "", [], row["retrieved_docs"], len(row["retrieved_docs"]))
            for key in ("correct", "abstained", "missing", "citations_valid", "cites_gold"):
                score.pop(key, None)
        rows.append({**row, **score})
    retrieval_only = result["config"].get("retrieval_only", False)
    by_category = defaultdict(list)
    for r in rows:
        by_category[r["category"]].append(r)
    result.update(questions=rows, summary=summarize(rows, retrieval_only),
                  by_category={c: summarize(rs, retrieval_only) for c, rs in sorted(by_category.items())})
    _drop_tool_metrics(result)
    return result


def _drop_tool_metrics(result: dict) -> None:
    """Calculator use only means something for runs that had the calculator."""
    if not result["config"].get("calculator"):
        for s in [result["summary"], *result["by_category"].values()]:
            s.pop("calculator_use", None)


def save(result: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{result['config']['name']}.json").write_text(json.dumps(result, indent=1))


def log_mlflow(result: dict) -> None:
    """Every run is also an MLflow run, so experiments can be compared in the MLflow UI."""
    try:
        import mlflow
    except ImportError:
        return
    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment("ground-truth")
    with mlflow.start_run(run_name=result["config"]["name"]):
        mlflow.log_params({k: v for k, v in result["config"].items() if k != "description"})
        mlflow.log_metrics({k: v for k, v in result["summary"].items() if isinstance(v, (int, float))})
        for category, s in result["by_category"].items():
            mlflow.log_metrics({f"{category}.{k}": v for k, v in s.items() if isinstance(v, (int, float))})
        mlflow.log_dict(result, "result.json")
