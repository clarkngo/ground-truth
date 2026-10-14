import re
from dataclasses import dataclass

from .config import RunConfig
from .corpus import Document


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    title: str
    heading: str
    text: str

    def embed_text(self) -> str:
        # A short header gives every chunk its document context, so "Prerequisite: AI 210" stays tied to its course.
        return f"{self.title} > {self.heading}\n{self.text}" if self.heading else f"{self.title}\n{self.text}"


def chunk_documents(docs: dict[str, Document], config: RunConfig) -> list[Chunk]:
    chunker = {"heading": by_heading, "fixed": fixed_window}[config.chunking]
    return [c for d in docs.values() for c in chunker(d, config)]


def by_heading(doc: Document, config: RunConfig) -> list[Chunk]:
    """One chunk per '##' section; sections longer than chunk_size are split on paragraph boundaries."""
    sections: list[tuple[str, str]] = []
    heading, lines = "", []
    for line in doc.body.splitlines():
        if line.startswith("## "):
            if "".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif line.startswith("# "):
            continue
        else:
            lines.append(line)
    if "".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))

    chunks = []
    for heading, text in sections:
        for part in _split_paragraphs(text, config.chunk_size):
            chunks.append(Chunk(f"{doc.id}#{len(chunks)}", doc.id, doc.title, heading, part))
    return chunks


def fixed_window(doc: Document, config: RunConfig) -> list[Chunk]:
    """Baseline: fixed-size character windows that ignore document structure."""
    text = re.sub(r"^#+ ", "", doc.body, flags=re.M)
    step = max(1, config.chunk_size - config.chunk_overlap)
    chunks = []
    for start in range(0, max(1, len(text)), step):
        part = text[start:start + config.chunk_size].strip()
        if part:
            chunks.append(Chunk(f"{doc.id}#{len(chunks)}", doc.id, doc.title, "", part))
        if start + config.chunk_size >= len(text):
            break
    return chunks


def _split_paragraphs(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for para in text.split("\n\n"):
        if current and len(current) + len(para) + 2 > limit:
            parts.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        parts.append(current)
    return parts
