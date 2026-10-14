import argparse
import json
import sys

from .config import RunConfig, load_configs
from .paths import RESULTS_DIR


def main() -> None:
    p = argparse.ArgumentParser(prog="gt", description="Ground Truth: RAG and agents, measured.")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("eval", help="run one or more experiment configs")
    e.add_argument("configs", nargs="+", help="config names from experiments/configs.yaml, or 'all'")
    e.add_argument("--limit", type=int, help="only the first N questions (for quick checks)")

    a = sub.add_parser("ask", help="ask one question")
    a.add_argument("question")
    a.add_argument("--config", default="baseline")

    sub.add_parser("report", help="print a leaderboard of saved results")
    sub.add_parser("export", help="write results, questions and corpus for the dashboard")
    sub.add_parser("rescore", help="re-score saved answers after a scorer or question fix (no model calls)")

    v = sub.add_parser("serve", help="run the API")
    v.add_argument("--port", type=int, default=8000)

    g = sub.add_parser("gate", help="fail if retrieval quality drops below a threshold (used in CI)")
    g.add_argument("--config", default="ci-bm25")
    g.add_argument("--min-recall", type=float, required=True)
    g.add_argument("--min-mrr", type=float, default=0.0)

    args = p.parse_args()
    configs = load_configs()
    {"eval": cmd_eval, "ask": cmd_ask, "report": cmd_report, "gate": cmd_gate, "export": cmd_export, "rescore": cmd_rescore,
     "serve": cmd_serve}[args.cmd](args, configs)


def _get(configs: dict[str, RunConfig], name: str) -> RunConfig:
    if name not in configs:
        sys.exit(f"unknown config '{name}'. Available: {', '.join(configs)}")
    return configs[name]


def cmd_eval(args, configs) -> None:
    from .evaluate import run

    names = list(configs) if args.configs == ["all"] else args.configs
    for name in names:
        config = _get(configs, name)
        print(f"{name}: {config.description}")
        result = run(config, args.limit)
        print(json.dumps(result["summary"], indent=2))


def cmd_ask(args, configs) -> None:
    from . import agent, rag
    from .retrieval import Retriever

    config = _get(configs, args.config)
    pipeline = agent.answer if config.pipeline == "agent" else rag.answer
    a = pipeline(args.question, Retriever(config), config)
    for s in a.steps:
        print(f"[{s.agent}] {s.detail}\n  {s.output}\n")
    print(f"Sources retrieved: {', '.join(a.retrieved_docs)}")
    print(f"{round(a.latency_ms / 1000, 1)}s, {a.prompt_tokens + a.output_tokens} tokens")


def cmd_report(args, configs) -> None:
    rows = [json.loads(f.read_text()) for f in sorted(RESULTS_DIR.glob("*.json"))]
    cols = ["accuracy", "correct_refusals", "citation_validity", "retrieval_recall", "retrieval_mrr", "latency_p50_ms"]
    print(f"{'config':<28}" + "".join(f"{c:>19}" for c in cols))
    for r in sorted(rows, key=lambda r: r["summary"].get("accuracy") or -1, reverse=True):
        s = r["summary"]
        print(f"{r['config']['name']:<28}" + "".join(f"{_fmt(s.get(c)):>19}" for c in cols))


def cmd_gate(args, configs) -> None:
    """Retrieval-only and deterministic (BM25), so it runs in CI without a model server."""
    from .evaluate import run

    config = _get(configs, args.config)
    if not config.retrieval_only or config.retriever != "bm25":
        sys.exit("the gate must use a retrieval-only BM25 config so it is deterministic in CI")
    s = run(config, log=lambda *_: None)["summary"]
    print(f"recall={s['retrieval_recall']} mrr={s['retrieval_mrr']} (min recall {args.min_recall}, min mrr {args.min_mrr})")
    if s["retrieval_recall"] < args.min_recall or s["retrieval_mrr"] < args.min_mrr:
        sys.exit("retrieval regression: quality fell below the gate")


def cmd_rescore(args, configs) -> None:
    from .evaluate import rescore, save

    for f in sorted(RESULTS_DIR.glob("*.json")):
        result = rescore(json.loads(f.read_text()))
        save(result)
        print(f"{result['config']['name']:<26} accuracy={_fmt(result['summary'].get('accuracy'))}")


def cmd_export(args, configs) -> None:
    from .export import export

    print("exported:", ", ".join(export()))


def cmd_serve(args, configs) -> None:
    import uvicorn

    uvicorn.run("groundtruth.api:app", port=args.port)


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float) and v <= 1:
        return f"{v:.0%}"
    return str(v)
