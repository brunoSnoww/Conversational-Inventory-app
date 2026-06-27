from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
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
