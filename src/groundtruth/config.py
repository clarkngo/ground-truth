from dataclasses import asdict, dataclass, fields

import yaml

from .paths import CONFIGS_FILE


@dataclass(frozen=True)
class RunConfig:
    """One experiment: how to chunk, retrieve and answer. Every field is logged with the results."""

    name: str
    description: str = ""
    chunking: str = "heading"  # heading | fixed
    chunk_size: int = 800  # characters; for heading chunking, the size above which a section is split
    chunk_overlap: int = 100  # characters, fixed chunking only
    retriever: str = "hybrid"  # dense | bm25 | hybrid
    k: int = 5
    embed_model: str = "nomic-embed-text"
    model: str = "qwen2.5:7b"
    pipeline: str = "rag"  # rag | agent
    calculator: bool = False  # model writes {{expressions}}; we compute them exactly
    retrieval_only: bool = False

    def params(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k not in ("name", "description")}


def load_configs() -> dict[str, RunConfig]:
    raw = yaml.safe_load(CONFIGS_FILE.read_text())
    known = {f.name for f in fields(RunConfig)}
    configs = {}
    for entry in raw["configs"]:
        unknown = set(entry) - known
        if unknown:
            raise ValueError(f"config {entry.get('name')}: unknown keys {sorted(unknown)}")
        configs[entry["name"]] = RunConfig(**entry)
    return configs
