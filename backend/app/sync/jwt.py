from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings


def powersync_jwks_k() -> str:
    secret = get_settings().powersync_jwt_secret
    return base64.urlsafe_b64encode(secret.encode()).decode().rstrip("=")


def mint_powersync_token(user_id: int, *, lifetime_hours: int = 12) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "aud": settings.powersync_jwt_audience,
        "iat": now,
        "exp": now + timedelta(hours=lifetime_hours),
    }
    return jwt.encode(
        payload,
        settings.powersync_jwt_secret,
        algorithm="HS256",
        headers={"kid": settings.powersync_jwt_kid, "alg": "HS256"},
    )
