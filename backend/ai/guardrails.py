"""Agent guardrails — ponytail: one file, inventory-specific checks only."""

from __future__ import annotations

import json
import logging
import re

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, UserPromptPart

log = logging.getLogger(__name__)

MAX_INPUT_CHARS = 4000
FALLBACK_REPLY = (
    "Sorry — I couldn't produce a reliable answer just now. "
    "Please rephrase, or ask about a specific product SKU."
)

INJECTION = re.compile(
    r"(ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions"
    r"|disregard\s+(?:the\s+)?(?:system|previous)"
    r"|you\s+are\s+now\s+(?:a|an|in)\b"
    r"|system\s+prompt"
    r"|reveal\s+your\s+(?:system\s+)?prompt"
    r"|act\s+as\s+(?:a\s+)?(?:dan|developer\s+mode))",
    re.IGNORECASE,
)

READ_DATA_TOOLS = frozenset({"query_stock", "get_profit", "calculator"})
WRITE_TOOLS = frozenset({"register_product", "create_purchase_order", "record_sale", "add_stock"})
ALL_DATA_TOOLS = READ_DATA_TOOLS | WRITE_TOOLS

# User is asking to mutate inventory — not a read-only figure question.
WRITE_INTENT = re.compile(
    r"\b("
    r"register|buy\b|sell\b|"
    r"create\s+(?:a\s+)?purchase|purchase\s+order|"
    r"record\s+(?:a\s+)?sale|add\s+stock"
    r")\b",
    re.IGNORECASE,
)

FINANCIAL_FIGURES = re.compile(
    r"\b(profit|margin|revenue|cost|lucro|margem|receita|custo)\b", re.IGNORECASE,
)
STOCK_QUESTION = re.compile(
    r"\b(stock|estoque|on[- ]hand|inventory levels?|how many (?:units|do (?:i|we) have)|quantas unidades)\b",
    re.IGNORECASE,
)
# ponytail: omit "total" — matches "$200 total" on purchase orders and false-triggers read-tool retries.
GENERIC_QUANTITY = re.compile(r"\b(how much|how many|quanto)\b", re.IGNORECASE)
HAS_FIGURE = re.compile(
    r"""
    (?:[$R]\$?\s*\d[\d.,]*)
    | (?:\b\d[\d.,]*\s*%)
    | (?:\b\d[\d.,]*\s*(?:kg|g|L|mL|units?|unidades?)\b)
    | (?:\b(?:profit|revenue|cost|margin|lucro|receita|custo|margem)\b[^.\n]{0,40}?\d)
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Backticks or "SKU X" — inventory SKUs are short alphanumeric + hyphen.
SKU_IN_OUTPUT = re.compile(
    r"`([^`]+)`|(?:\bSKU\s+)([A-Za-z0-9][A-Za-z0-9-]*)",
    re.IGNORECASE,
)

_FIGURE_RULES = (
    (STOCK_QUESTION, frozenset({"query_stock"}),
     "You answered a stock question with a number without calling query_stock this turn. "
     "Call query_stock to fetch fresh on-hand quantities from the server."),
    (FINANCIAL_FIGURES, READ_DATA_TOOLS,
     "You stated profit/revenue/cost/margin without calling a data tool this turn. "
     "Call get_profit (and the calculator for any arithmetic), then answer with the returned numbers."),
    (GENERIC_QUANTITY, ALL_DATA_TOOLS,
     "You stated a figure without calling a data tool this turn. "
     "Call the relevant tool (e.g. query_stock, get_profit) and answer with the returned numbers."),
)


class InputGuardrailError(Exception):
    """Raised when user input is rejected pre-model. Caller returns a safe reply."""


def check_input(message: str) -> str:
    stripped = (message or "").strip()
    if not stripped:
        raise InputGuardrailError("Empty message. Ask about products, stock, orders, or profit.")
    if len(stripped) > MAX_INPUT_CHARS:
        raise InputGuardrailError(f"Message too long ({len(stripped)} chars, max {MAX_INPUT_CHARS}).")
    if INJECTION.search(stripped):
        raise InputGuardrailError(
            "I can only help with inventory tasks (products, stock, orders, profit). "
            "I can't change my instructions or role."
        )
    return stripped


def sanitize_user_text(value: str, *, max_chars: int = 200) -> str:
    if not value:
        return value
    collapsed = " ".join(value.split())
    redacted = INJECTION.sub("[redacted]", collapsed)
    if len(redacted) > max_chars:
        redacted = redacted[: max_chars - 1].rstrip() + "…"
    return redacted


def _latest_user_prompt(ctx: RunContext) -> str | None:
    for msg in reversed(ctx.messages):
        if not isinstance(msg, ModelRequest):
            continue
        for part in msg.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                return part.content
    return None


def _tool_calls_this_turn(ctx: RunContext, names: frozenset[str]) -> list[ToolCallPart]:
    calls: list[ToolCallPart] = []
    for msg in reversed(ctx.messages):
        if isinstance(msg, ModelRequest) and any(isinstance(p, UserPromptPart) for p in msg.parts):
            break
        if not isinstance(msg, ModelResponse):
            continue
        for part in msg.parts:
            if isinstance(part, ToolCallPart) and part.tool_name in names:
                calls.append(part)
    return calls


def _tool_called_this_turn(ctx: RunContext, names: frozenset[str]) -> bool:
    return bool(_tool_calls_this_turn(ctx, names))


def _tool_call_args(part: ToolCallPart) -> dict:
    args = part.args
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _normalize_sku(sku: str) -> str:
    return sku.strip().upper()


def _write_tool_skus_this_turn(ctx: RunContext) -> set[str]:
    skus: set[str] = set()
    for part in _tool_calls_this_turn(ctx, WRITE_TOOLS):
        sku = _tool_call_args(part).get("sku")
        if isinstance(sku, str) and sku.strip():
            skus.add(_normalize_sku(sku))
    return skus


def _skus_mentioned_in_output(output: str) -> set[str]:
    skus: set[str] = set()
    for match in SKU_IN_OUTPUT.finditer(output):
        token = match.group(1) or match.group(2)
        if token and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", token.strip()):
            skus.add(_normalize_sku(token))
    return skus


def _is_clarifying_question(output: str) -> bool:
    """Allow short follow-up questions when required fields are missing."""
    stripped = output.strip()
    return stripped.endswith("?") and not HAS_FIGURE.search(stripped)


def _validate_write_uses_tool(ctx: RunContext, output: str) -> None:
    """Octopus-style: write intents must call a write tool before any final reply."""
    user_text = _latest_user_prompt(ctx)
    if not user_text or not WRITE_INTENT.search(user_text):
        return
    if _tool_called_this_turn(ctx, WRITE_TOOLS):
        return
    stripped = (output or "").strip()
    if not stripped or _is_clarifying_question(stripped):
        return
    raise ModelRetry(
        "This user message requires a write tool call before you reply. "
        "Call register_product, create_purchase_order, record_sale, or add_stock first, "
        "then summarize the tool result — never invent stock levels, revenue, or confirmations."
    )


def _validate_write_reply_matches_tools(ctx: RunContext, output: str) -> None:
    """After write tools run, reply must not narrate figures for unrelated SKUs."""
    acted = _write_tool_skus_this_turn(ctx)
    if not acted:
        return
    mentioned = _skus_mentioned_in_output(output)
    if not mentioned:
        return
    rogue = mentioned - acted
    if not rogue:
        return
    if not (HAS_FIGURE.search(output) or FINANCIAL_FIGURES.search(output)):
        return
    raise ModelRetry(
        "You called write tools this turn but your reply discusses different SKUs "
        f"({', '.join(sorted(rogue))}) than the ones you updated "
        f"({', '.join(sorted(acted))}). Summarize only the tool results for the SKUs you wrote."
    )


def _validate_figures_use_fresh_tool(ctx: RunContext, output: str) -> None:
    user_text = _latest_user_prompt(ctx)
    if not user_text or not HAS_FIGURE.search(output):
        return
    # ponytail: write commands (PO, sale, register) skip figure guard — Gemini often
    # narrates before tool call; retries exhaust → fallback. DB only changes via tools.
    if WRITE_INTENT.search(user_text):
        return
    for pattern, required_tools, message in _FIGURE_RULES:
        if pattern.search(user_text) and not _tool_called_this_turn(ctx, required_tools):
            raise ModelRetry(message)


async def output_guardrails_handler(ctx: RunContext, output: str) -> str:
    stripped = (output or "").strip()
    if not stripped:
        raise ModelRetry("Your response was empty. Provide a text answer to the user or call a tool.")
    _validate_write_uses_tool(ctx, stripped)
    _validate_write_reply_matches_tools(ctx, stripped)
    _validate_figures_use_fresh_tool(ctx, stripped)
    return output
