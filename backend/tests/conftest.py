from __future__ import annotations

import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


def _db_reachable() -> bool:
    try:
        from django.db import connection

        connection.ensure_connection()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_reachable(), reason="Postgres not available")
