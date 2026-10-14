from groundtruth.bm25 import BM25, tokenize
from groundtruth.chunking import by_heading, fixed_window
from groundtruth.config import RunConfig
from groundtruth.corpus import load_corpus
from groundtruth.metrics import score_question
from groundtruth.evaluate import load_questions
from groundtruth.retrieval import Retriever, doc_ranking


def test_heading_chunks_keep_their_section_and_document_context():
    chunks = by_heading(load_corpus()["cat-ai"], RunConfig(name="t"))
    ai340 = next(c for c in chunks if c.heading.startswith("AI 340"))
    assert "Prerequisite: AI 210" in ai340.text
    assert ai340.embed_text().startswith("Course Catalog: Artificial Intelligence (AI) > AI 340")


def test_fixed_windows_overlap_and_cover_the_document():
    doc = load_corpus()["prog-bs-ai"]
    chunks = fixed_window(doc, RunConfig(name="t", chunking="fixed", chunk_size=300, chunk_overlap=50))
    assert len(chunks) > 2
    assert all(len(c.text) <= 300 for c in chunks)


def test_bm25_prefers_documents_with_rare_query_terms():
    bm = BM25([tokenize("library hours saturday"), tokenize("tuition per credit"), tokenize("library study rooms")])
    scores = bm.scores(tokenize("saturday library hours"))
    assert scores.index(max(scores)) == 0


def test_bm25_retrieval_gate():
    """The same check CI runs: BM25 on heading chunks must keep finding the gold documents."""
    config = RunConfig(name="gate", retriever="bm25", retrieval_only=True)
    retriever = Retriever(config)
    recalls = []
    for q in load_questions():
        if q["gold_docs"]:
            docs = doc_ranking(retriever.search(q["question"]))
            recalls.append(score_question(q, "", [], docs, len(docs))["retrieval_recall"])
    assert sum(recalls) / len(recalls) >= 0.95
