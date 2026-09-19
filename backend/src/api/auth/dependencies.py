"""Authentication dependencies — Phase 4, Task 7.

A route states its requirement in its own signature:

    async def read_me(user: CurrentUser) -> UserResponse: ...

Not middleware matching a URL prefix. A prefix rule is invisible at the route and
silently stops matching the day someone renames a path, whereas a missing annotation
here is visible in the function it protects.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.exceptions import InvalidToken, NotAuthenticated
from api.auth.jwt import TokenClaims, decode_token
from api.auth.revocation import RevocationStore, get_revocation_store
from api.config.settings import Settings, get_settings
from api.db.repositories.users import UserRepository
from api.db.session import get_session
from api.models.user import User
from api.services.auth_service import AuthService

logger = structlog.get_logger(__name__)

# auto_error=False so a missing header raises our own error with our own body, rather
# than FastAPI's default 403 — which would be the wrong code as well as the wrong shape.
_bearer = HTTPBearer(auto_error=False, description="Access token issued by /auth/login")


async def get_access_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    revocation: Annotated[RevocationStore, Depends(get_revocation_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenClaims:
    """Verify the bearer token: signature, expiry, type, then the deny-list."""
    if credentials is None:
        raise NotAuthenticated()

    claims = decode_token(credentials.credentials, expected_type="access", settings=settings)

    if await revocation.is_revoked(claims):
        logger.info("auth.token_rejected", reason="revoked", jti=claims.jti)
        raise InvalidToken(reason="token_revoked")

    return claims


async def get_current_user(
    claims: Annotated[TokenClaims, Depends(get_access_claims)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """The logged-in user, or 401.

    The database read is not optional, even though avoiding lookups is the whole point
    of a JWT. A valid signature proves the claims were issued by this server; it cannot
    prove the account still exists or is still enabled. Skip this and a deactivated
    user keeps working until their token expires.
    """
    user = await UserRepository(session).get(claims.sub)

    if user is None or not user.is_active:
        reason = "user_missing" if user is None else "user_disabled"
        logger.info("auth.token_rejected", reason=reason, user_id=str(claims.sub))
        raise InvalidToken(reason=reason)

    return user


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    revocation: Annotated[RevocationStore, Depends(get_revocation_store)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session=session, revocation=revocation, settings=settings)


# Aliases the routes annotate with, so the ``Annotated[...]`` noise is written once.
CurrentUser = Annotated[User, Depends(get_current_user)]
AccessClaims = Annotated[TokenClaims, Depends(get_access_claims)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
