import pytest

from groundtruth.calculator import evaluate, substitute


def test_substitutes_expressions_with_exact_results():
    text, calls = substitute("Tuition is ${{9 * 665}} and the refund is ${{(5 * 435) * 0.75}}.")
    assert text == "Tuition is $5,985 and the refund is $1,631.25."
    assert calls == [("9 * 665", "5,985"), ("(5 * 435) * 0.75", "1,631.25")]


def test_tolerates_dollar_signs_commas_and_percent():
    assert evaluate("$2,175 * 75%") == pytest.approx(1631.25)


@pytest.mark.parametrize("expr", ["__import__('os').system('ls')", "2 ** 100", "open('f')", "a + 1"])
def test_rejects_anything_but_arithmetic(expr):
    with pytest.raises((ValueError, SyntaxError)):
        evaluate(expr)


def test_leaves_unparseable_expressions_in_place():
    text, calls = substitute("Total: {{fifteen times 435}}")
    assert text == "Total: fifteen times 435" and calls == []


def test_tool_runner_returns_results_and_errors_as_text():
    from groundtruth.calculator import run_tool

    assert run_tool("calculate", {"expression": "45 * 665"}) == "29,925"
    assert run_tool("calculate", {"expression": "import os"}).startswith("error:")
    assert run_tool("search", {}).startswith("error:")
