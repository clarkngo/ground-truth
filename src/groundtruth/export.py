"""Writes the dashboard's data: experiment results, questions and corpus as static JSON. Static files mean the
GitHub Pages demo shows the real results without a backend."""
import json
import shutil

from .corpus import load_corpus
from .evaluate import load_questions
from .paths import RESULTS_DIR, ROOT

OUT = ROOT / "web" / "public" / "data"


def export() -> list[str]:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "results").mkdir(parents=True)
    index = []
    for f in sorted(RESULTS_DIR.glob("*.json")):
        result = json.loads(f.read_text())
        shutil.copy(f, OUT / "results" / f.name)
        index.append({"config": result["config"], "ran_at": result["ran_at"], "duration_s": result["duration_s"],
                      "summary": result["summary"], "by_category": result["by_category"]})
    (OUT / "index.json").write_text(json.dumps(index, indent=1))
    (OUT / "questions.json").write_text(json.dumps(load_questions(), indent=1))
    corpus = [{**d.__dict__} for d in load_corpus().values()]
    (OUT / "corpus.json").write_text(json.dumps(corpus, indent=1))
    return [i["config"]["name"] for i in index]
