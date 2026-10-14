"""The corpus and the ground truth must stay consistent with each other."""
from groundtruth.corpus import load_corpus
from groundtruth.evaluate import load_questions


def test_question_ids_are_unique():
    ids = [q["id"] for q in load_questions()]
    assert len(ids) == len(set(ids))


def test_gold_docs_exist():
    docs = load_corpus()
    for q in load_questions():
        for d in q["gold_docs"]:
            assert d in docs, f"{q['id']} cites missing doc {d}"


def test_answerable_questions_have_expectations_and_unanswerable_do_not():
    for q in load_questions():
        if q["category"] == "unanswerable":
            assert not q["gold_docs"] and "expect" not in q, q["id"]
        else:
            assert q["gold_docs"] and q["expect"], q["id"]


def test_superseded_documents_exist():
    docs = load_corpus()
    for d in docs.values():
        if d.supersedes:
            assert d.supersedes in docs and docs[d.supersedes].effective < d.effective
