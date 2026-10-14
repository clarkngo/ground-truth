from dataclasses import dataclass
from functools import cache

import yaml

from .paths import CORPUS_DIR


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    type: str
    effective: str
    supersedes: str | None
    body: str


def parse(text: str) -> Document:
    if not text.startswith("---\n"):
        raise ValueError("document is missing front matter")
    _, front, body = text.split("---\n", 2)
    meta = yaml.safe_load(front)
    return Document(id=meta["id"], title=meta["title"], type=meta["type"], effective=str(meta["effective"]),
                    supersedes=meta.get("supersedes"), body=body.strip())


@cache
def load_corpus() -> dict[str, Document]:
    docs = [parse(p.read_text()) for p in sorted(CORPUS_DIR.glob("*.md")) if p.name != "README.md"]
    return {d.id: d for d in docs}


def superseded_ids(docs: dict[str, Document]) -> set[str]:
    return {d.supersedes for d in docs.values() if d.supersedes}
