"""Stable UUIDs for agent write tools — retries must not duplicate orders."""

from __future__ import annotations

import uuid
from decimal import Decimal

# Fixed namespace — same chat turn + tool + args always yields the same guid.
_TOOL_GUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://inventory.local/agent-tool")


def tool_guid(chat_message_id: int | None, tool_name: str, **args: object) -> uuid.UUID | None:
    """Derive a deterministic order guid from the chat turn and tool arguments.

    Returns None when chat_message_id is missing (demo REPL, tests) — caller falls
    back to uuid.uuid4() in the service layer.
    """
    if chat_message_id is None:
        return None
    parts: list[str] = [str(chat_message_id), tool_name]
    for key in sorted(args):
        parts.append(f"{key}={_normalize_arg(args[key])}")
    return uuid.uuid5(_TOOL_GUID_NAMESPACE, "|".join(parts))


def _normalize_arg(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)
