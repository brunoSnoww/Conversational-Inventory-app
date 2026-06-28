from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str


class RefreshRequest(BaseModel):
    refresh: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    access: str
    refresh: str


class AccessTokenResponse(BaseModel):
    access: str
