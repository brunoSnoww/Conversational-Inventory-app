from __future__ import annotations

import pytest

from app.auth.passwords import verify_password
from app.auth.users import authenticate_user
from services.db import fetch_one

from .conftest import requires_db


@requires_db
def test_seed_user_login_with_django_hash():
    row = fetch_one(
        "SELECT email, password_hash FROM app_user WHERE email = %s",
        ["demo@inventory.local"],
    )
    assert row is not None
    assert verify_password("password123", row["password_hash"])
    user = authenticate_user("demo@inventory.local", "password123")
    assert user is not None
    assert user.email == "demo@inventory.local"
