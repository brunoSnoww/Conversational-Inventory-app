"""Thin SQL helpers for Goose-managed tables (server-side ID defaults)."""

from __future__ import annotations

from app.db.session import fetch_all, fetch_one

__all__ = ["fetch_one", "fetch_all"]
