from __future__ import annotations

import jwt

from app.config import get_settings
from app.sync.jwt import mint_powersync_token, powersync_jwks_k


def test_mint_powersync_token_sub_claim():
    settings = get_settings()
    token = mint_powersync_token(42)
    payload = jwt.decode(
        token,
        settings.powersync_jwt_secret,
        algorithms=["HS256"],
        audience=settings.powersync_jwt_audience,
    )
    assert payload["sub"] == "42"


def test_jwks_k_is_base64url():
    k = powersync_jwks_k()
    assert "=" not in k
    assert len(k) > 10
