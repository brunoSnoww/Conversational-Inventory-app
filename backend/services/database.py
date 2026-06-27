"""Database access wrapper for repository dependency injection."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from app.db.session import transaction as _transaction

from .db import fetch_all, fetch_one


class Database:
    """Thin adapter over psycopg pool helpers."""

    def fetch_one(self, sql: str, params: list[Any] | tuple[Any, ...]) -> dict[str, Any] | None:
        return fetch_one(sql, params)

    def fetch_all(self, sql: str, params: list[Any] | tuple[Any, ...]) -> list[dict[str, Any]]:
        return fetch_all(sql, params)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with _transaction():
            yield
