"""PowerSync upload connector — apply client PUT mutations server-side."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from asgiref.sync import sync_to_async

from ai.constants import THINKING_PLACEHOLDER
from services.db import fetch_one

logger = logging.getLogger(__name__)


@dataclass
class Mutation:
    op: str
    type: str
    data: dict[str, Any]


@dataclass(frozen=True)
class _PendingReply:
    placeholder_id: int


async def dispatch_mutations(user_id: int, mutations: list[Mutation]) -> None:
    for mutation in mutations:
        await _dispatch_one(user_id, mutation)


async def _dispatch_one(user_id: int, mutation: Mutation) -> None:
    if mutation.op != "PUT" or not mutation.data:
        return

    if mutation.type == "chat_message":
        await _handle_chat_message(user_id, mutation.data)
        return

    logger.debug("ignored mutation type=%s op=%s", mutation.type, mutation.op)


async def _insert_user_message(user_id: int, content: str, client_id: int | None) -> int:
    if client_id is not None:
        row = await sync_to_async(fetch_one)(
            """
            INSERT INTO chat_message (chat_message_id, user_id, role, content)
            VALUES (%s, %s, 'user'::chat_message_role, %s)
            ON CONFLICT (chat_message_id) DO NOTHING
            RETURNING chat_message_id
            """,
            [client_id, user_id, content],
        )
        if row is not None:
            return int(row["chat_message_id"])
        existing = await sync_to_async(fetch_one)(
            """
            SELECT chat_message_id FROM chat_message
            WHERE chat_message_id = %s AND user_id = %s
            """,
            [client_id, user_id],
        )
        if existing is None:
            raise PermissionError("chat_message_id belongs to another user or is missing")
        return int(existing["chat_message_id"])

    row = await sync_to_async(fetch_one)(
        """
        INSERT INTO chat_message (user_id, role, content)
        VALUES (%s, 'user'::chat_message_role, %s)
        RETURNING chat_message_id
        """,
        [user_id, content],
    )
    assert row is not None
    return int(row["chat_message_id"])


def _update_assistant_message(user_id: int, chat_message_id: int, content: str) -> bool:
    row = fetch_one(
        """
        UPDATE chat_message
        SET content = %s
        WHERE chat_message_id = %s
          AND user_id = %s
          AND role = 'assistant'::chat_message_role
        RETURNING chat_message_id
        """,
        [content, chat_message_id, user_id],
    )
    return row is not None


async def _insert_thinking_placeholder(user_id: int) -> int:
    row = await sync_to_async(fetch_one)(
        """
        INSERT INTO chat_message (user_id, role, content)
        VALUES (%s, 'assistant'::chat_message_role, %s)
        RETURNING chat_message_id
        """,
        [user_id, THINKING_PLACEHOLDER],
    )
    assert row is not None
    return int(row["chat_message_id"])


async def _resolve_pending_reply(user_id: int, user_message_id: int) -> _PendingReply | None:
    """Return a placeholder to fill, or None when a final assistant reply already exists."""
    row = await sync_to_async(fetch_one)(
        """
        SELECT chat_message_id, content
        FROM chat_message
        WHERE user_id = %s
          AND role = 'assistant'::chat_message_role
          AND created_at > (
            SELECT created_at
            FROM chat_message
            WHERE chat_message_id = %s AND user_id = %s
          )
        ORDER BY created_at ASC
        LIMIT 1
        """,
        [user_id, user_message_id, user_id],
    )
    if row is None:
        placeholder_id = await _insert_thinking_placeholder(user_id)
        return _PendingReply(placeholder_id=placeholder_id)

    content = (row.get("content") or "").strip()
    if content == THINKING_PLACEHOLDER:
        return _PendingReply(placeholder_id=int(row["chat_message_id"]))

    logger.info(
        "chat_message_id=%s already has final assistant reply — skipping agent",
        user_message_id,
    )
    return None


async def _complete_chat_reply(
    user_id: int,
    user_message_id: int,
    content: str,
    placeholder_id: int,
) -> None:
    from ai.guardrails import FALLBACK_REPLY
    from ai.runner import run_inventory_agent

    try:
        reply = await run_inventory_agent(
            user_id, content, chat_message_id=user_message_id,
        )
    except Exception:
        logger.exception(
            "agent failed user_id=%s user_message_id=%s placeholder_id=%s",
            user_id, user_message_id, placeholder_id,
        )
        reply = FALLBACK_REPLY

    updated = await sync_to_async(_update_assistant_message)(
        user_id, placeholder_id, reply,
    )
    if not updated:
        logger.warning(
            "thinking placeholder missing user_id=%s placeholder_id=%s — inserting reply",
            user_id, placeholder_id,
        )
        await sync_to_async(fetch_one)(
            """
            INSERT INTO chat_message (user_id, role, content)
            VALUES (%s, 'assistant'::chat_message_role, %s)
            RETURNING chat_message_id
            """,
            [user_id, reply],
        )


async def _handle_chat_message(user_id: int, data: dict[str, Any]) -> None:
    role = data.get("role")
    if role != "user":
        return

    content = (data.get("content") or "").strip()
    if not content:
        return

    msg_user_id = int(data.get("user_id") or 0)
    if msg_user_id != user_id:
        raise PermissionError("chat_message user_id does not match authenticated user")

    client_id = data.get("chat_message_id")
    chat_message_id = await _insert_user_message(
        user_id, content, int(client_id) if client_id is not None else None,
    )

    pending = await _resolve_pending_reply(user_id, chat_message_id)
    if pending is None:
        return

    from ai.runner import schedule_coro

    schedule_coro(
        _complete_chat_reply(user_id, chat_message_id, content, pending.placeholder_id),
    )


def dispatch_mutations_sync(user_id: int, mutations: list[Mutation]) -> None:
    """WSGI-safe entry point — run on persistent agent loop."""
    from ai.runner import run_coro_blocking

    run_coro_blocking(dispatch_mutations(user_id, mutations))
