from __future__ import annotations

import jwt

from sync_api.jwt import POWERSYNC_JWT_AUDIENCE, POWERSYNC_JWT_SECRET, mint_powersync_token, powersync_jwks_k


def test_mint_powersync_token_sub_claim():
    token = mint_powersync_token(42)
    payload = jwt.decode(token, POWERSYNC_JWT_SECRET, algorithms=["HS256"], audience=POWERSYNC_JWT_AUDIENCE)
    assert payload["sub"] == "42"


def test_jwks_k_is_base64url():
    k = powersync_jwks_k()
    assert "=" not in k
    assert len(k) > 10
