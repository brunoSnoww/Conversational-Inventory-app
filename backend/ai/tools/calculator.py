"""Calculator tool for agent arithmetic (simpleeval).

The system prompt forbids the model from doing mental math; it MUST route every
arithmetic operation (profit, margin, totals) through this tool. For a financial
app this is the difference between trustworthy numbers and plausible-looking
hallucinations.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic_ai import ModelRetry, RunContext
from simpleeval import InvalidExpression, simple_eval

T = TypeVar("T")


async def calculator(_ctx: RunContext[T], expression: str) -> str:
    """Evaluate a simple arithmetic expression and return the result as a string.

    Supports: +, -, *, /, ** (power), % (modulo), parentheses, numeric literals.
    Does NOT support: imports, variables, function calls, strings, dates.

    Examples: "100 * 1.05", "(1000 - 100) / 100 * 100", "2 ** 10"
    """
    try:
        # LLMs frequently emit ^ for exponentiation.
        expression = expression.replace("^", "**")
        return str(simple_eval(expression))
    except (InvalidExpression, SyntaxError, TypeError) as e:
        raise ModelRetry(f"Invalid expression: {e}. Rewrite it using only numbers and + - * / ** % ().") from e
