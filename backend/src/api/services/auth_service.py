"""Authentication workflow — Phase 4, Tasks 3 and 5.

Kept free of HTTP so it can be tested without a client and reused from a worker or a
CLI later. It raises the domain errors in ``api.auth.exceptions``; ``api.main`` maps
them to status codes.

Logging convention for this module: an identifier and a reason code, never a
credential. No password, no whole token, no hash. ``jti`` is logged because it is the
handle revocation works on and is useless without the token it names.
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.exceptions import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidToken,
    TokenReused,
)
from api.auth.jwt import TokenClaims, TokenPair, create_token_pair, decode_token
from api.auth.password import DUMMY_HASH, hash_password, needs_rehash, verify_password
from api.auth.revocation import RevocationStore
from api.config.settings import Settings
from api.db.repositories.users import UserRepository
from api.models.membership import AccountType, Membership, MembershipRole, MembershipStatus
from api.models.organization import Organization, OrganizationKind
from api.models.user import User

logger = structlog.get_logger(__name__)

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slug_for(email: str) -> str:
    """A unique, readable slug for a personal organization.

    The random suffix is not decoration: ``organizations.slug`` is unique, and two
    people at the same company domain would otherwise collide on signup.
    """
    local = email.split("@", 1)[0].lower()
    stem = _SLUG_STRIP.sub("-", local).strip("-")[:32] or "workspace"
    return f"{stem}-{secrets.token_hex(4)}"


class AuthService:
    """Register, log in, refresh and log out."""

    def __init__(
        self,
        session: AsyncSession,
        revocation: RevocationStore,
        settings: Settings,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.revocation = revocation
        self.settings = settings

    # -- registration ------------------------------------------------------

    async def register(
        self, *, email: str, password: str, full_name: str
    ) -> tuple[User, Organization, TokenPair]:
        """Create a user, their personal organization and the membership joining them.

        Three rows in one transaction, per architecture §7.3. The personal organization
        is what lets ``organization_id`` be NOT NULL on every tenant-scoped table: with
        no such row, tenant queries would need
        ``WHERE organization_id = :org OR (organization_id IS NULL AND owner_id = :user)``
        and that ``OR`` is exactly the clause a developer forgets — a cross-tenant leak.
        """
        email = email.strip().lower()

        # Advisory: two concurrent signups can both pass it. The unique index decides,
        # and the IntegrityError below is the real guard.
        if await self.users.email_exists(email):
            logger.info("auth.register_rejected", reason="email_taken")
            raise EmailAlreadyRegistered()

        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
        )
        organization = Organization(
            name=f"{full_name.strip()}'s workspace",
            slug=_slug_for(email),
            kind=OrganizationKind.PERSONAL,
        )
        self.session.add_all([user, organization])

        try:
            # flush(), not commit(): the INSERTs run so the UUIDs exist, but the
            # transaction stays open — a failure on the third row rolls back the first
            # two, and nobody ends up with an account and no workspace.
            await self.session.flush()

            self.session.add(
                Membership(
                    user_id=user.id,
                    organization_id=organization.id,
                    role=MembershipRole.ADMIN,
                    account_type=AccountType.MEMBER,
                    # Not the column default. ``pending`` is right for someone who was
                    # invited; the person who just created the workspace is active, and
                    # the admin-count trigger only counts active admins.
                    status=MembershipStatus.ACTIVE,
                    joined_at=datetime.now(UTC),
                )
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            logger.info("auth.register_rejected", reason="integrity_conflict")
            raise EmailAlreadyRegistered() from exc

        tokens = create_token_pair(user.id, settings=self.settings)
        logger.info(
            "auth.registered",
            user_id=str(user.id),
            organization_id=str(organization.id),
        )
        return user, organization, tokens

    # -- login -------------------------------------------------------------

    async def login(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        """Verify a password and issue a token pair.

        The hash is verified even when the account does not exist. Returning early
        would answer "no such account" in about a millisecond and "wrong password" in
        sixty, because only the second runs Argon2 — a working email-enumeration
        oracle for anyone with a list of addresses.
        """
        email = email.strip().lower()
        user = await self.users.get_by_email(email)

        stored_hash = user.password_hash if user else DUMMY_HASH
        password_ok = verify_password(password, stored_hash)

        if user is None or not password_ok or not user.is_active:
            reason = (
                "unknown_email"
                if user is None
                else "bad_password"
                if not password_ok
                else "account_disabled"
            )
            # The reason is recorded here and deliberately not returned to the caller.
            logger.info("auth.login_failed", reason=reason)
            raise InvalidCredentials()

        # Login is the only moment the plaintext exists, so it is the only moment an
        # old hash can be upgraded to current parameters.
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            await self.session.commit()
            logger.info("auth.password_rehashed", user_id=str(user.id))

        tokens = create_token_pair(user.id, settings=self.settings)
        logger.info("auth.login", user_id=str(user.id))
        return user, tokens

    # -- refresh -----------------------------------------------------------

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Trade a refresh token for a new pair, and kill the one presented.

        Rotation plus reuse detection. Because the old token dies on use, a second
        presentation of the same ``jti`` means two parties hold it. There is no way to
        tell which one is knocking, so every session for that user is revoked.
        """
        claims = decode_token(refresh_token, expected_type="refresh", settings=self.settings)

        if await self.revocation.is_revoked(claims):
            await self.revocation.revoke_all_for_user(
                claims.sub,
                ttl_seconds=self.settings.refresh_token_expire_days * 86400,
            )
            logger.warning("auth.refresh_reused", user_id=str(claims.sub), jti=claims.jti)
            raise TokenReused()

        user = await self.users.get(claims.sub)
        if user is None or not user.is_active:
            logger.info("auth.refresh_rejected", reason="account_unavailable")
            raise InvalidToken(reason="account_unavailable")

        await self.revocation.revoke(claims)
        tokens = create_token_pair(user.id, settings=self.settings)
        logger.info("auth.refreshed", user_id=str(user.id), rotated_jti=claims.jti)
        return tokens

    # -- logout ------------------------------------------------------------

    async def logout(self, *, access_claims: TokenClaims, refresh_token: str) -> None:
        """Revoke both tokens.

        A refresh token that fails to decode is not an error worth surfacing: the
        access token still gets revoked, and the caller is logging out either way.
        Raising here would leave the session half-alive.
        """
        await self.revocation.revoke(access_claims)

        try:
            refresh_claims = decode_token(
                refresh_token, expected_type="refresh", settings=self.settings
            )
        except InvalidToken:
            logger.info("auth.logout", user_id=str(access_claims.sub), refresh="undecodable")
            return

        if refresh_claims.sub != access_claims.sub:
            # Someone is logging out with somebody else's refresh token. Revoke only
            # what was proven — the access token — and record it.
            logger.warning(
                "auth.logout_token_mismatch",
                user_id=str(access_claims.sub),
                refresh_subject=str(refresh_claims.sub),
            )
            return

        await self.revocation.revoke(refresh_claims)
        logger.info("auth.logout", user_id=str(access_claims.sub))

    async def logout_everywhere(self, user_id: UUID) -> None:
        """Kill every token for a user, including ones this process never saw."""
        await self.revocation.revoke_all_for_user(
            user_id,
            ttl_seconds=self.settings.refresh_token_expire_days * 86400,
        )
        logger.info("auth.logout_all", user_id=str(user_id))
