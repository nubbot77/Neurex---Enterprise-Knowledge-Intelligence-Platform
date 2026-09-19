"""Authentication dependencies — Phase 4, Task 7.

A route states its requirement in its own signature:

    async def read_me(user: CurrentUser) -> UserResponse: ...

Not middleware matching a URL prefix. A prefix rule is invisible at the route and
silently stops matching the day someone renames a path, whereas a missing annotation
here is visible in the function it protects.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.context import OrgContext
from api.auth.exceptions import InvalidToken, NotAuthenticated, OrganizationNotFound
from api.auth.jwt import TokenClaims, decode_token
from api.auth.membership_cache import MembershipCache, get_membership_cache
from api.auth.permissions import permissions_for
from api.auth.revocation import RevocationStore, get_revocation_store
from api.config.settings import Settings, get_settings
from api.db.repositories.memberships import MembershipRepository
from api.db.repositories.users import UserRepository
from api.db.session import get_session
from api.models.membership import MembershipStatus
from api.models.user import User
from api.services.auth_service import AuthService
from api.services.membership_service import MembershipService
from api.services.organization_service import OrganizationService

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


# --- Organization context — Phase 5, Task 4 ---------------------------------


async def get_org_context(
    organization_id: UUID,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[MembershipCache, Depends(get_membership_cache)],
) -> OrgContext:
    """Resolve the caller's standing in the organization named in the URL.

    Architecture §7.8, in order: authenticate, read the requested ``organization_id``
    from the **path**, load the membership, reject anything that is not active, expand
    the role into its permission set.

    Two rules here are the ones that are easy to get wrong and expensive to retrofit:

    **The path parameter is a lookup key, never proof of access.** It is only ever fed
    into the membership query below.

    **Absent membership answers 404, not 403.** A 403 would confirm the organization
    exists, handing anyone who walks UUIDs a map of the tenant id space. A user with no
    active membership is told exactly what a user asking about a nonexistent
    organization is told — and pending, suspended and absent are all the same answer.
    """
    cached = await cache.get(user.id, organization_id)
    if cached is not None:
        return OrgContext(
            user_id=user.id,
            organization_id=organization_id,
            membership_id=cached.membership_id,
            role=cached.role,
            account_type=cached.account_type,
            permissions=permissions_for(cached.role),
            is_super_admin=user.is_super_admin,
        )

    row = await MembershipRepository(session).get_with_organization(user.id, organization_id)

    if row is None:
        # Covers both "no such organization" and "not a member of it". They are
        # indistinguishable to the caller by design; only the log tells them apart.
        logger.info(
            "orgcontext.denied",
            reason="no_membership",
            user_id=str(user.id),
            organization_id=str(organization_id),
        )
        raise OrganizationNotFound(reason="no_membership")

    membership, organization = row

    if not organization.is_active:
        logger.info(
            "orgcontext.denied",
            reason="organization_inactive",
            user_id=str(user.id),
            organization_id=str(organization_id),
        )
        raise OrganizationNotFound(reason="organization_inactive")

    if membership.status is not MembershipStatus.ACTIVE:
        # Checked once, here, rather than repeated at every call site — and it is what
        # makes a suspension take effect on the next request (invariant 7).
        logger.info(
            "orgcontext.denied",
            reason=f"membership_{membership.status.value}",
            user_id=str(user.id),
            organization_id=str(organization_id),
        )
        raise OrganizationNotFound(reason=f"membership_{membership.status.value}")

    await cache.set(membership)
    return OrgContext.from_membership(membership, is_super_admin=user.is_super_admin)


OrgContextDep = Annotated[OrgContext, Depends(get_org_context)]
MembershipCacheDep = Annotated[MembershipCache, Depends(get_membership_cache)]


async def get_membership_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    cache: Annotated[MembershipCache, Depends(get_membership_cache)],
) -> MembershipService:
    return MembershipService(session=session, cache=cache)


async def get_organization_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationService:
    return OrganizationService(session=session)


MembershipServiceDep = Annotated[MembershipService, Depends(get_membership_service)]
OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
