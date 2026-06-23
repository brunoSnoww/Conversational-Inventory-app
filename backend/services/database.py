"""Database access wrapper for repository dependency injection."""

from __future__ import annotations

from typing import Any

from .db import fetch_all, fetch_one


class Database:
    """Thin adapter over Django connection helpers."""

    def fetch_one(self, sql: str, params: list[Any] | tuple[Any, ...]) -> dict[str, Any] | None:
        return fetch_one(sql, params)

    def fetch_all(self, sql: str, params: list[Any] | tuple[Any, ...]) -> list[dict[str, Any]]:
        return fetch_all(sql, params)
