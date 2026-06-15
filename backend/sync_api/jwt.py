"""PowerSync client JWT (HS256, local dev — matches inventory/powersync/config.yaml)."""

from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone

import jwt

POWERSYNC_JWT_SECRET = os.environ.get(
    "POWERSYNC_JWT_SECRET",
    "inventory-dev-powersync-secret-key-32b",
)
POWERSYNC_JWT_AUDIENCE = os.environ.get("POWERSYNC_JWT_AUDIENCE", "http://localhost:2000")
POWERSYNC_JWT_KID = os.environ.get("POWERSYNC_JWT_KID", "inventory-local-key")
POWERSYNC_URL = os.environ.get("POWERSYNC_URL", "http://localhost:2000")


def powersync_jwks_k() -> str:
    """Base64url-encoded oct key for config.yaml `client_auth.jwks.keys[].k`."""
    return base64.urlsafe_b64encode(POWERSYNC_JWT_SECRET.encode()).decode().rstrip("=")


def mint_powersync_token(user_id: int, *, lifetime_hours: int = 12) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "aud": POWERSYNC_JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=lifetime_hours),
    }
    return jwt.encode(
        payload,
        POWERSYNC_JWT_SECRET,
        algorithm="HS256",
        headers={"kid": POWERSYNC_JWT_KID, "alg": "HS256"},
    )
