"""Thin SQL helpers for Goose-managed tables (server-side ID defaults)."""

from __future__ import annotations

from typing import Any

from django.db import connection


def fetch_one(sql: str, params: list[Any] | tuple[Any, ...]) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [col[0] for col in cursor.description]
        return dict(zip(cols, row, strict=True))


def fetch_all(sql: str, params: list[Any] | tuple[Any, ...]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row, strict=True)) for row in cursor.fetchall()]
