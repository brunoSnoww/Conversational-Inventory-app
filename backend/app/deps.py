from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import decode_access_token
from app.auth.users import UserRecord, get_user_by_email

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    email: str


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc
    row = get_user_by_email_by_id(user_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return CurrentUser(user_id=row.user_id, email=row.email)


def get_user_by_email_by_id(user_id: int) -> UserRecord | None:
    from services.db import fetch_one

    row = fetch_one(
        "SELECT user_id, email, is_active FROM app_user WHERE user_id = %s",
        [user_id],
    )
    if row is None:
        return None
    return UserRecord(
        user_id=int(row["user_id"]),
        email=row["email"],
        is_active=bool(row["is_active"]),
    )
