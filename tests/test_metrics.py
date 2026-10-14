from groundtruth.metrics import is_abstention, missing_groups, score_question, summarize


def test_every_group_must_match_and_any_alternative_counts():
    expect = [["ai 330"], ["ai 340"], ["march 30", "3/30"]]
    assert missing_groups("You need AI 330 and AI 340; Spring starts 3/30.", expect) == []
    assert missing_groups("You need AI 330; Spring starts March 30.", expect) == [["ai 340"]]


def test_literal_spaces_match_optional_whitespace():
    assert missing_groups("Prerequisite: AI210", [["ai 210"]]) == []


def test_regex_alternatives():
    assert missing_groups("A grade of C or higher.", [["re:\\bc\\b"]]) == []
    assert missing_groups("A grade of B.", [["re:\\bc\\b"]]) == [["re:\\bc\\b"]]


def test_abstention_detection():
    assert is_abstention("I don't know based on the provided sources.")
    assert is_abstention("The sources do not mention a parking fee.")
    assert not is_abstention("Tuition is $435 per credit [fin-tuition-2025-26].")


def test_unanswerable_is_correct_only_when_abstaining():
    q = {"id": "u01", "category": "unanswerable", "gold_docs": []}
    assert score_question(q, "I don't know based on the provided sources.", [], [], 5)["correct"]
    assert not score_question(q, "Parking costs $50 [svc-parking].", ["svc-parking"], [], 5)["correct"]


def test_answer_with_right_facts_but_invented_citation_is_correct_with_invalid_citations():
    q = {"id": "t02", "category": "temporal", "gold_docs": ["fin-tuition-2025-26"], "expect": [["435"]]}
    s = score_question(q, "It is $435 per credit [fin-tuition-2026].", ["fin-tuition-2026"], ["fin-tuition-2025-26"], 1)
    assert s["correct"] and s["citations_valid"] is False and s["cites_gold"] is False


def test_retrieval_recall_and_mrr():
    q = {"id": "m05", "category": "multi_hop", "gold_docs": ["cat-ai", "cal-2025-26"], "expect": [["sept"]]}
    s = score_question(q, "", [], ["prog-bs-ai", "cat-ai", "fin-refunds"], 3)
    assert s["retrieval_recall"] == 0.5 and s["retrieval_hit"] and s["retrieval_mrr"] == 0.5


def test_summary_separates_refusal_rates():
    rows = [
        {"category": "factual", "correct": True, "abstained": False, "citations_valid": True, "cites_gold": True,
         "latency_ms": 100, "prompt_tokens": 10, "output_tokens": 5},
        {"category": "factual", "correct": False, "abstained": True, "citations_valid": None, "cites_gold": None,
         "latency_ms": 300, "prompt_tokens": 10, "output_tokens": 5},
        {"category": "unanswerable", "correct": True, "abstained": True, "citations_valid": None, "cites_gold": None,
         "latency_ms": 200, "prompt_tokens": 10, "output_tokens": 5},
    ]
    s = summarize(rows, retrieval_only=False)
    assert s["accuracy"] == round(2 / 3, 4)
    assert s["false_refusals"] == 0.5 and s["correct_refusals"] == 1.0
    assert s["latency_p50_ms"] == 200
