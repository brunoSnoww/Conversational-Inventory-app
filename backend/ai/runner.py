"""Single entry point for running the agent — input guardrails + graceful fallback."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Coroutine, TypeVar

from asgiref.sync import sync_to_async

from .deps import Deps
from .agent import inventory_agent
from .guardrails import FALLBACK_REPLY, InputGuardrailError, check_input
from .history import load_chat_history

log = logging.getLogger(__name__)
T = TypeVar("T")

# ponytail: one persistent loop — pydantic-ai binds httpx client to first loop used.
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is not None and not _loop.is_closed():
        return _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            loop = asyncio.new_event_loop()
            thread = threading.Thread(target=loop.run_forever, name="agent-loop", daemon=True)
            thread.start()
            _loop = loop
    return _loop


def _run_coro(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run_coroutine_threadsafe(coro, _get_loop()).result()


def schedule_coro(coro: Coroutine[Any, Any, T]) -> asyncio.Future[T]:
    """Schedule on the agent loop without blocking the caller (WSGI thread)."""
    return asyncio.run_coroutine_threadsafe(coro, _get_loop())


try:
    from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
except Exception:  # pragma: no cover
    UnexpectedModelBehavior = Exception  # type: ignore[assignment, misc]
    ModelHTTPError = Exception  # type: ignore[assignment, misc]


def _friendly_model_error(err: BaseException) -> str | None:
    if not isinstance(err, ModelHTTPError):
        return None
    code = getattr(err, "status_code", None)
    if code == 401:
        return (
            "AI API key rejected (401). For OpenRouter use OPENROUTER_API_KEY=sk-or-… "
            "(not OPENAI_API_KEY) in inventory/.env, then: docker compose up -d api"
        )
    if code == 429:
        return (
            "The AI service quota is exhausted right now. "
            "Wait a minute and retry, or switch the API key/model in inventory/.env."
        )
    return None


async def run_inventory_agent(
    user_id: int,
    message: str,
    *,
    chat_message_id: int | None = None,
) -> str:
    try:
        clean = check_input(message)
    except InputGuardrailError as e:
        return str(e)
    try:
        history = await sync_to_async(load_chat_history)(
            user_id, exclude_message_id=chat_message_id,
        )
        result = await inventory_agent.run(
            clean,
            deps=Deps(user_id=user_id, chat_message_id=chat_message_id),
            message_history=history or None,
        )
        return result.output
    except UnexpectedModelBehavior as e:
        log.warning("agent retries exhausted for user_id=%s: %s", user_id, e)
        return FALLBACK_REPLY
    except ModelHTTPError as e:
        friendly = _friendly_model_error(e)
        if friendly:
            log.warning("model HTTP error for user_id=%s: %s", user_id, e)
            return friendly
        raise
