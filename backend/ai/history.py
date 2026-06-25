"""Load prior chat turns from Postgres for pydantic-ai message_history."""

from __future__ import annotations

from typing import Any

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from ai.constants import CHAT_HISTORY_LIMIT, THINKING_PLACEHOLDER
from services.db import fetch_all


def rows_to_message_history(rows: list[dict[str, Any]]) -> list[ModelMessage]:
    """Convert chat_message rows (oldest first) to pydantic-ai history."""
    history: list[ModelMessage] = []
    for row in rows:
        content = (row.get("content") or "").strip()
        if not content or content == THINKING_PLACEHOLDER:
            continue
        role = row.get("role")
        if role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
    return history


def load_chat_history(
    user_id: int,
    *,
    exclude_message_id: int | None = None,
    limit: int = CHAT_HISTORY_LIMIT,
) -> list[ModelMessage]:
    """Fetch recent chat messages for a user, excluding the current turn if given."""
    params: list[Any] = [user_id]
    exclude_clause = ""
    if exclude_message_id is not None:
        exclude_clause = "AND chat_message_id <> %s"
        params.append(exclude_message_id)

    params.append(THINKING_PLACEHOLDER)
    params.append(limit)
    rows = fetch_all(
        f"""
        SELECT chat_message_id, role, content
        FROM chat_message
        WHERE user_id = %s
        {exclude_clause}
          AND trim(content) <> ''
          AND content <> %s
        ORDER BY chat_message_id DESC
        LIMIT %s
        """,
        params,
    )
    rows.reverse()
    return rows_to_message_history(rows)
