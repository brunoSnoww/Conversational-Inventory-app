from __future__ import annotations

import os

import pytest

from app.db.pool import close_pool, get_pool


def _db_reachable() -> bool:
    try:
        with get_pool().connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_reachable(), reason="Postgres not available")


@pytest.fixture(scope="session", autouse=True)
def _configure_test_env() -> None:
    os.environ.setdefault("INVENTORY_DB_HOST", os.environ.get("INVENTORY_DB_HOST", "localhost"))
    os.environ.setdefault("INVENTORY_DB_PORT", os.environ.get("INVENTORY_DB_PORT", "5433"))
    os.environ.setdefault("INVENTORY_DB_NAME", os.environ.get("INVENTORY_DB_NAME", "db_inventory"))
    os.environ.setdefault("INVENTORY_DB_USER", os.environ.get("INVENTORY_DB_USER", "postgres"))
    os.environ.setdefault("INVENTORY_DB_PASSWORD", os.environ.get("INVENTORY_DB_PASSWORD", "postgres"))
    os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")


@pytest.fixture(scope="session", autouse=True)
def _close_pool_after_tests() -> None:
    yield
    close_pool()
