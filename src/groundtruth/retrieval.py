import hashlib
import json
from dataclasses import dataclass

from .bm25 import BM25, tokenize
from .chunking import Chunk, chunk_documents
from .config import RunConfig
from .corpus import load_corpus
from .paths import CACHE_DIR

RRF_K = 60  # standard reciprocal-rank-fusion constant
CANDIDATES = 20


@dataclass
class Hit:
    chunk: Chunk
    score: float


class EmbeddingCache:
    """Embeddings keyed by model and text hash, so re-running experiments doesn't re-embed the corpus."""

    def __init__(self, model: str):
        self.model = model
        self.path = CACHE_DIR / f"embeddings-{model.replace(':', '_').replace('/', '_')}.json"
        self.data: dict[str, list[float]] = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get_many(self, texts: list[str]) -> list[list[float]]:
        from . import ollama

        keys = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
        missing = [(k, t) for k, t in zip(keys, texts) if k not in self.data]
        for i in range(0, len(missing), 32):
            batch = missing[i:i + 32]
            for (k, _), vec in zip(batch, ollama.embed(self.model, [t for _, t in batch])):
                self.data[k] = vec
        if missing:
            CACHE_DIR.mkdir(exist_ok=True)
            self.path.write_text(json.dumps(self.data))
        return [self.data[k] for k in keys]


class Retriever:
    def __init__(self, config: RunConfig):
        self.config = config
        self.chunks = chunk_documents(load_corpus(), config)
        self.bm25 = BM25([tokenize(c.embed_text()) for c in self.chunks])
        self._collection = None

    # nomic-embed-text was trained with task prefixes; using them noticeably improves retrieval.
    def _doc_prefix(self) -> str:
        return "search_document: " if "nomic" in self.config.embed_model else ""

    def _query_prefix(self) -> str:
        return "search_query: " if "nomic" in self.config.embed_model else ""

    def collection(self):
        """A ChromaDB collection per chunking setup, rebuilt only when the chunks change."""
        if self._collection is None:
            import chromadb

            texts = [self._doc_prefix() + c.embed_text() for c in self.chunks]
            fingerprint = hashlib.sha256(json.dumps([self.config.embed_model, texts]).encode()).hexdigest()[:12]
            client = chromadb.PersistentClient(path=str(CACHE_DIR / "chroma"))
            name = f"{self.config.chunking}-{self.config.chunk_size}-{fingerprint}"
            col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
            if col.count() != len(self.chunks):
                vectors = EmbeddingCache(self.config.embed_model).get_many(texts)
                col.upsert(ids=[c.id for c in self.chunks], embeddings=vectors,
                           metadatas=[{"doc_id": c.doc_id} for c in self.chunks], documents=[c.text for c in self.chunks])
            self._collection = col
        return self._collection

    def dense(self, query: str, n: int) -> list[Hit]:
        vec = EmbeddingCache(self.config.embed_model).get_many([self._query_prefix() + query])[0]
        res = self.collection().query(query_embeddings=[vec], n_results=min(n, len(self.chunks)))
        by_id = {c.id: c for c in self.chunks}
        return [Hit(by_id[i], 1 - d) for i, d in zip(res["ids"][0], res["distances"][0])]

    def sparse(self, query: str, n: int) -> list[Hit]:
        scores = self.bm25.scores(tokenize(query))
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)[:n]
        return [Hit(self.chunks[i], scores[i]) for i in ranked if scores[i] > 0]

    def search(self, query: str, k: int | None = None) -> list[Hit]:
        k = k or self.config.k
        if self.config.retriever == "dense":
            return self.dense(query, k)
        if self.config.retriever == "bm25":
            return self.sparse(query, k)
        return rrf([self.dense(query, CANDIDATES), self.sparse(query, CANDIDATES)])[:k]


def rrf(rankings: list[list[Hit]]) -> list[Hit]:
    """Reciprocal rank fusion: rewards chunks ranked well by any retriever, without calibrating their scores."""
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking):
            scores[hit.chunk.id] = scores.get(hit.chunk.id, 0) + 1 / (RRF_K + rank + 1)
            chunks[hit.chunk.id] = hit.chunk
    return [Hit(chunks[i], s) for i, s in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


def doc_ranking(hits: list[Hit]) -> list[str]:
    """Distinct document ids in the order their first chunk was retrieved."""
    seen: list[str] = []
    for h in hits:
        if h.chunk.doc_id not in seen:
            seen.append(h.chunk.doc_id)
    return seen
