"""A tiny calculator tool. Models write arithmetic as {{15 * 435}}; we compute it exactly and substitute the result.
LLMs are reliable at setting up a calculation and unreliable at multiplying, so each does the part it's good at."""
import ast
import operator
import re

_EXPR = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}

TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "Evaluate an arithmetic expression exactly. Use it for every multiplication, sum, percentage "
                       "or total instead of computing in your head.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. (5 * 435) * 0.75"}},
            "required": ["expression"],
        },
    },
}

TOOL_RULE = "- Use the calculate tool for every calculation, then state the result it returns."


def run_tool(name: str, arguments: dict) -> str:
    if name != "calculate":
        return f"error: unknown tool {name}"
    try:
        return fmt(evaluate(str(arguments.get("expression", ""))))
    except (ValueError, SyntaxError, ZeroDivisionError) as e:
        return f"error: {e}"


RULE = ("- Never do arithmetic yourself, and don't use LaTeX. Write every calculation inside double curly braces and "
        "it will be replaced with the exact result. Example: \"Tuition is ${{15 * 435}} [fin-tuition-2025-26].\" "
        "becomes \"Tuition is $6,525 [fin-tuition-2025-26].\" Use plain numbers inside the braces, with no $ or commas.")


def evaluate(expr: str) -> float:
    """Safely evaluates + - * / and parentheses over numbers. Anything else raises ValueError."""
    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.operand))
        raise ValueError(f"unsupported expression: {expr}")

    cleaned = expr.replace(",", "").replace("$", "").replace("×", "*").replace("x", "*").replace("%", "/100")
    return walk(ast.parse(cleaned, mode="eval"))


def fmt(value: float) -> str:
    return f"{int(round(value)):,}" if abs(value - round(value)) < 1e-9 else f"{value:,.2f}"


def substitute(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Replaces every {{expr}} with its value; returns the new text and the (expression, result) pairs."""
    calls: list[tuple[str, str]] = []

    def repl(m: re.Match) -> str:
        try:
            result = fmt(evaluate(m.group(1)))
        except (ValueError, SyntaxError, ZeroDivisionError):
            return m.group(1)
        calls.append((m.group(1), result))
        return result

    return _EXPR.sub(repl, text), calls
