from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt

from app.config import Settings, get_settings


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


def _encode(payload: dict[str, Any], settings: Settings) -> str:
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def mint_token_pair(user_id: int, *, settings: Settings | None = None) -> TokenPair:
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    access_exp = now + timedelta(hours=settings.jwt_access_lifetime_hours)
    refresh_exp = now + timedelta(days=settings.jwt_refresh_lifetime_days)
    access = _encode(
        {
            "token_type": "access",
            "exp": access_exp,
            "iat": now,
            "jti": str(uuid4()),
            "user_id": user_id,
        },
        settings,
    )
    refresh = _encode(
        {
            "token_type": "refresh",
            "exp": refresh_exp,
            "iat": now,
            "jti": str(uuid4()),
            "user_id": user_id,
        },
        settings,
    )
    return TokenPair(access=access, refresh=refresh)


def decode_access_token(token: str, *, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
    if payload.get("token_type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return int(payload["user_id"])


def refresh_access_token(refresh_token: str, *, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    payload = jwt.decode(refresh_token, settings.app_secret_key, algorithms=["HS256"])
    if payload.get("token_type") != "refresh":
        raise jwt.InvalidTokenError("not a refresh token")
    user_id = int(payload["user_id"])
    now = datetime.now(timezone.utc)
    access_exp = now + timedelta(hours=settings.jwt_access_lifetime_hours)
    return _encode(
        {
            "token_type": "access",
            "exp": access_exp,
            "iat": now,
            "jti": str(uuid4()),
            "user_id": user_id,
        },
        settings,
    )
