from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "corpus"
QUESTIONS_FILE = ROOT / "evals" / "questions.yaml"
CONFIGS_FILE = ROOT / "experiments" / "configs.yaml"
RESULTS_DIR = ROOT / "experiments" / "results"
CACHE_DIR = ROOT / ".cache"
