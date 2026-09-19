"""Request and response shapes for the auth routes — Phase 4, Task 4.

Defined before the routes because the routes annotate with them. Validation that lives
here cannot be forgotten at a call site, and it runs before any service code.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Argon2 has no practical input ceiling, but an unbounded field is a cheap way to make
# the server spend 64 MiB hashing a megabyte of text, so the maximum is a DoS guard
# rather than a password policy.
PASSWORD_MIN = 12
PASSWORD_MAX = 128


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """The refresh token is required at logout, not optional.

    Revoking only the access token leaves a seven-day refresh token alive in the
    storage the user just "logged out" of — the more valuable of the two.
    """

    refresh_token: str = Field(min_length=1)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserResponse(BaseModel):
    """What the caller may see about themselves.

    ``password_hash`` is absent by construction: the response model lists fields
    explicitly rather than dumping the ORM object, so a new column on ``users`` cannot
    start leaking by accident.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_super_admin: bool
    created_at: datetime


class RegisterResponse(BaseModel):
    """Registration logs the user straight in — no second round-trip to ``/login``.

    ``organization_id`` is the personal organization created in the same transaction.
    The client needs it immediately: every organization-scoped route in Phase 5 is
    ``/orgs/{organization_id}/…``.
    """

    user: UserResponse
    organization_id: uuid.UUID
    tokens: TokenPairResponse
