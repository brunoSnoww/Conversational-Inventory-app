from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from psycopg.rows import dict_row

from app.db.pool import get_pool

_tx_conn: ContextVar[Any | None] = ContextVar("_tx_conn", default=None)


def _cursor():
    conn = _tx_conn.get()
    if conn is not None:
        return conn.cursor(row_factory=dict_row)
    return get_pool().connection().cursor(row_factory=dict_row)


def fetch_one(sql: str, params: list[Any] | tuple[Any, ...]) -> dict[str, Any] | None:
    conn = _tx_conn.get()
    if conn is not None:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()


def fetch_all(sql: str, params: list[Any] | tuple[Any, ...]) -> list[dict[str, Any]]:
    conn = _tx_conn.get()
    if conn is not None:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    with get_pool().connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())


@contextmanager
def transaction() -> Iterator[None]:
    with get_pool().connection() as conn:
        previous_autocommit = conn.autocommit
        conn.autocommit = False
        token = _tx_conn.set(conn)
        try:
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _tx_conn.reset(token)
            conn.autocommit = previous_autocommit
