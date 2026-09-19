"""JWT encoding and decoding — Phase 4, Tasks 2 and 3.

A JWT is three base64url segments joined by dots: ``header.payload.signature``. The
first two are *encoded, not encrypted* — anyone holding the token can read every claim,
so nothing secret goes in one. The signature is an HMAC over the first two segments
keyed by ``JWT_SECRET_KEY``; edit a claim and the recomputed HMAC no longer matches.

The claim set is deliberately thin:

``sub``  the user id, and the entire identity assertion
``jti``  unique per token — the handle the revocation deny-list needs
``typ``  ``access`` or ``refresh``
``iat``  issued-at, compared against the per-user revocation cutoff
``exp``  expiry

There is no ``role`` and no ``organization_id``. A role baked into a token keeps
asserting itself until the token expires, so a demotion or a suspended membership would
not apply for up to ``access_token_expire_minutes`` — architecture §7.8 forbids exactly
that. Phase 5 resolves authority per request instead.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import jwt

from api.auth.exceptions import InvalidToken
from api.config.settings import Settings

TokenType = Literal["access", "refresh"]

# Tolerance for clock drift between instances when comparing ``exp`` and ``iat``.
# Without it, a few seconds of skew rejects tokens that are genuinely valid.
CLOCK_SKEW_LEEWAY_SECONDS = 30


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """A decoded, verified token."""

    sub: UUID
    jti: str
    typ: TokenType
    iat: datetime
    exp: datetime

    @property
    def seconds_until_expiry(self) -> int:
        """Remaining life, floored at zero.

        This is the TTL a revocation entry gets: the deny-list only has to outlive the
        token it denies, so entries expire themselves and the list stays small.
        """
        remaining = (self.exp - datetime.now(UTC)).total_seconds()
        return max(0, int(remaining))


@dataclass(frozen=True, slots=True)
class TokenPair:
    """What every successful authentication returns."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


def _encode(
    user_id: UUID,
    *,
    token_type: TokenType,
    lifetime: timedelta,
    settings: Settings,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID, *, settings: Settings) -> str:
    return _encode(
        user_id,
        token_type="access",
        lifetime=timedelta(minutes=settings.access_token_expire_minutes),
        settings=settings,
    )


def create_refresh_token(user_id: UUID, *, settings: Settings) -> str:
    return _encode(
        user_id,
        token_type="refresh",
        lifetime=timedelta(days=settings.refresh_token_expire_days),
        settings=settings,
    )


def create_token_pair(user_id: UUID, *, settings: Settings) -> TokenPair:
    """Issue both tokens at once.

    Two tokens exist because one cannot do both jobs. The access token travels on every
    request and expires in minutes, so a stolen copy is nearly worthless. The refresh
    token lives for days but leaves storage only to call ``/auth/refresh``.
    """
    return TokenPair(
        access_token=create_access_token(user_id, settings=settings),
        refresh_token=create_refresh_token(user_id, settings=settings),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(token: str, *, expected_type: TokenType, settings: Settings) -> TokenClaims:
    """Verify a token and return its claims, or raise ``InvalidToken``.

    ``algorithms`` is pinned to the server's own setting. Passing the token's own
    ``alg`` back in — or omitting the argument on a library that allows it — is the
    ``alg: none`` bug: an attacker rewrites the header to ``{"alg": "none"}``, drops the
    signature, and the server accepts the token's word for how it was signed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            leeway=CLOCK_SKEW_LEEWAY_SECONDS,
            options={"require": ["sub", "jti", "typ", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidToken(reason="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        # Covers a bad signature, a malformed token, a missing required claim and
        # ``alg: none``. All of them are one 401 to the client.
        raise InvalidToken(reason="token_invalid") from exc

    if payload["typ"] != expected_type:
        # Without this check a refresh token — good for seven days — works perfectly
        # well as an access token, and the short access lifetime becomes decorative.
        raise InvalidToken(reason="token_wrong_type")

    try:
        subject = UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise InvalidToken(reason="token_bad_subject") from exc

    return TokenClaims(
        sub=subject,
        jti=str(payload["jti"]),
        typ=payload["typ"],
        iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
