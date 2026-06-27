from __future__ import annotations

import psycopg.errors
from fastapi import APIRouter, HTTPException, status

from app.auth.jwt import mint_token_pair, refresh_access_token
from app.auth.schemas import AccessTokenResponse, AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from app.auth.users import authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user_id: int, email: str) -> AuthResponse:
    tokens = mint_token_pair(user_id)
    return AuthResponse(
        user_id=str(user_id),
        email=email,
        access=tokens.access,
        refresh=tokens.refresh,
    )


@router.post("/register/", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> AuthResponse:
    try:
        user = create_user(body.email, body.password)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Email already registered.") from None
    return _auth_response(user.user_id, user.email)


@router.post("/login/", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    user = authenticate_user(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid email or password.")
    return _auth_response(user.user_id, user.email)


@router.post("/refresh/", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest) -> AccessTokenResponse:
    try:
        access = refresh_access_token(body.refresh)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token is invalid or expired.") from exc
    return AccessTokenResponse(access=access)
