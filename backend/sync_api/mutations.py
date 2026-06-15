"""PowerSync upload connector — apply client PUT mutations server-side."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from asgiref.sync import sync_to_async

from services.db import fetch_one

logger = logging.getLogger(__name__)


@dataclass
class Mutation:
    op: str
    type: str
    data: dict[str, Any]


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
    if client_id is not None:
        await sync_to_async(fetch_one)(
            """
            INSERT INTO chat_message (chat_message_id, user_id, role, content)
            VALUES (%s, %s, 'user'::chat_message_role, %s)
            ON CONFLICT (chat_message_id) DO NOTHING
            RETURNING chat_message_id
            """,
            [int(client_id), user_id, content],
        )
    else:
        await sync_to_async(fetch_one)(
            """
            INSERT INTO chat_message (user_id, role, content)
            VALUES (%s, 'user'::chat_message_role, %s)
            RETURNING chat_message_id
            """,
            [user_id, content],
        )

    from ai.runner import run_inventory_agent

    reply = await run_inventory_agent(user_id, content)

    await sync_to_async(fetch_one)(
        """
        INSERT INTO chat_message (user_id, role, content)
        VALUES (%s, 'assistant'::chat_message_role, %s)
        RETURNING chat_message_id
        """,
        [user_id, reply],
    )


def dispatch_mutations_sync(user_id: int, mutations: list[Mutation]) -> None:
    """WSGI-safe entry point — run on persistent agent loop."""
    from ai.runner import _run_coro

    _run_coro(dispatch_mutations(user_id, mutations))
