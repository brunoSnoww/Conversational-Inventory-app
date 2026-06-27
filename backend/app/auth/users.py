from __future__ import annotations

from dataclasses import dataclass

from app.auth.passwords import hash_password, verify_password
from services.db import fetch_one


@dataclass(frozen=True)
class UserRecord:
    user_id: int
    email: str
    is_active: bool


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> tuple[UserRecord, str] | None:
    row = fetch_one(
        """
        SELECT user_id, email, password_hash, is_active
        FROM app_user WHERE lower(email) = lower(%s)
        """,
        [email],
    )
    if row is None:
        return None
    user = UserRecord(
        user_id=int(row["user_id"]),
        email=row["email"],
        is_active=bool(row["is_active"]),
    )
    return user, row["password_hash"]


def authenticate_user(email: str, password: str) -> UserRecord | None:
    found = get_user_by_email(email)
    if found is None:
        return None
    user, password_hash = found
    if not user.is_active or not verify_password(password, password_hash):
        return None
    return user


def create_user(email: str, password: str) -> UserRecord:
    hashed = hash_password(password)
    row = fetch_one(
        """
        INSERT INTO app_user (email, password_hash)
        VALUES (%s, %s)
        RETURNING user_id, email, is_active
        """,
        [normalize_email(email), hashed],
    )
    assert row is not None
    return UserRecord(
        user_id=int(row["user_id"]),
        email=row["email"],
        is_active=bool(row["is_active"]),
    )
