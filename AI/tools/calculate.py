"""Tool: safe arithmetic on numbers the tools already returned (percentages, shares, differences, VAT).

The expression is parsed with `ast`, never `eval`: only numbers, + - * / and brackets are allowed.
Every operand must be a number a tool returned, or in the question, so the model cannot bring its own."""

import ast
import operator
import re

from AI.guards.number_check import ARABIC_DIGITS, known_numbers
from AI.tools.tool_context import ToolContext, ToolError, ToolResult, to_plain

MAX_EXPRESSION_CHARS = 300
FREE_CONSTANTS = {100.0, 1000.0, 1_000_000.0}  # for percentages and "in thousands / millions"
SMALLEST_CHECKED = 10  # like the number check: numbers below 10 are factors and counts, always allowed
OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}  # fmt: skip
THOUSANDS_COMMA = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def clean_expression(expression: str) -> str:
    """'1,250,000 * 15%' -> '1250000 * (15/100)'; Arabic digits become Latin ones."""
    text = str(expression).translate(ARABIC_DIGITS).replace("×", "*").replace("÷", "/")
    text = THOUSANDS_COMMA.sub("", text)
    return PERCENT.sub(r"(\1/100)", text)


def operands(tree: ast.AST) -> list[float]:
    """Every number in the expression; anything that is not plain arithmetic is refused."""
    numbers = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ToolError("Only numbers are allowed in the expression.")
            numbers.append(float(node.value))
        elif isinstance(node, (ast.BinOp, ast.UnaryOp)):
            if type(node.op) not in OPERATORS:
                raise ToolError("Only + - * / and brackets are allowed (no powers or functions).")
        elif not isinstance(node, (ast.Expression, ast.operator, ast.unaryop)):
            raise ToolError("Only numbers, + - * / and brackets are allowed (no names, functions or lists).")
    return numbers


def evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return evaluate(node.body)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.UnaryOp):
        return OPERATORS[type(node.op)](evaluate(node.operand))
    try:
        return OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
    except ZeroDivisionError as error:
        raise ToolError("Division by zero.") from error


def calculate(context: ToolContext, expression: str, label: str | None = None) -> ToolResult:
    """Compute `expression` from numbers the tools returned. `label` says what it is ("VAT on the total")."""
    if not str(expression or "").strip():
        raise ToolError("Give an expression, e.g. '907280968.18 * 15 / 100'.")
    if len(str(expression)) > MAX_EXPRESSION_CHARS:
        raise ToolError(f"The expression is too long (max {MAX_EXPRESSION_CHARS} characters).")
    cleaned = clean_expression(expression)
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as error:
        raise ToolError(f"'{expression}' is not a valid expression. Use numbers, + - * / and brackets.") from error
    known = known_numbers(context.known_texts)
    unknown = [
        to_plain(number)
        for number in operands(tree)
        if abs(number) >= SMALLEST_CHECKED and number not in FREE_CONSTANTS and number not in known
    ]
    if unknown:
        raise ToolError(
            f"These numbers were not returned by any tool or the question: {unknown}. Get them with "
            "query_table or search_documents first, and copy them exactly."
        )
    result = evaluate(tree)
    data = {
        "expression": cleaned,
        "result": to_plain(round(result, 4)),
        "result_rounded": to_plain(round(result, 2)),
        "note": "Write the result exactly as given here (result or result_rounded), with its currency.",
    }
    return ToolResult(data=data, step=f"Calculated {label or cleaned}")
