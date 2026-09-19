"""The membership cache — Phase 5, Tasks 1 and 4.

Architecture §7.8. The access token carries identity and nothing about authority, so
role and membership are resolved **per request**. A token that said ``role: admin``
would keep saying it until it expired, and a demotion or a suspension would take
minutes to apply — which defeats both the admin range and membership suspension, whose
whole point is that they apply now.

Resolving per request costs a query on the critical path of every organization-scoped
route, so the resolved membership is cached in Redis under
``membership:{user_id}:{organization_id}`` with a short TTL.

**The TTL is the backstop, not the mechanism.** Correctness comes from deleting the key
whenever the membership row changes — ``MembershipService`` does that on every write,
in the same call that writes it. The TTL only bounds how long a change made by
something outside the service (a migration, a hand-run UPDATE during an incident) can
be stale.

Only **active** memberships are cached. A pending, suspended or absent membership is
re-read every time: those are the states where being wrong is a security answer rather
than a slow one, and they are rare enough that the query does not matter.
"""

from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import Depends
from redis.asyncio import Redis

from api.config.settings import Settings, get_settings
from api.db.redis import get_redis
from api.models.membership import AccountType, Membership, MembershipRole, MembershipStatus

logger = structlog.get_logger(__name__)

_PREFIX = "membership:"


def cache_key(user_id: UUID, organization_id: UUID) -> str:
    return f"{_PREFIX}{user_id}:{organization_id}"


class CachedMembership:
    """The few fields context resolution needs, decoded from Redis.

    Deliberately not the ORM object. Caching a ``Membership`` would mean caching
    whatever columns that table grows later, and a stale copy of a column nobody
    remembered is worse than a second query.
    """

    __slots__ = ("account_type", "membership_id", "organization_id", "role", "user_id")

    def __init__(
        self,
        *,
        membership_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        role: MembershipRole,
        account_type: AccountType,
    ) -> None:
        self.membership_id = membership_id
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role
        self.account_type = account_type


class MembershipCache:
    """Redis-backed cache of resolved, active memberships."""

    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def get(self, user_id: UUID, organization_id: UUID) -> CachedMembership | None:
        raw = await self.redis.get(cache_key(user_id, organization_id))
        if raw is None:
            return None

        try:
            data: dict[str, Any] = json.loads(raw)
            return CachedMembership(
                membership_id=UUID(data["membership_id"]),
                user_id=user_id,
                organization_id=organization_id,
                role=MembershipRole(data["role"]),
                account_type=AccountType(data["account_type"]),
            )
        except ValueError, KeyError, TypeError:
            # A malformed or outdated entry must not fail the request and must not be
            # trusted either. Drop it and fall through to the database, which is
            # authoritative anyway.
            logger.warning(
                "membership.cache_corrupt",
                user_id=str(user_id),
                organization_id=str(organization_id),
            )
            await self.invalidate(user_id, organization_id)
            return None

    async def set(self, membership: Membership) -> None:
        """Cache an active membership. Anything else is ignored rather than stored."""
        if membership.status is not MembershipStatus.ACTIVE:
            return

        payload = json.dumps(
            {
                "membership_id": str(membership.id),
                "role": membership.role.value,
                "account_type": membership.account_type.value,
            }
        )
        await self.redis.set(
            cache_key(membership.user_id, membership.organization_id),
            payload,
            ex=self.ttl_seconds,
        )

    async def invalidate(self, user_id: UUID, organization_id: UUID) -> None:
        """Drop one entry. Called by every write to the membership row."""
        await self.redis.delete(cache_key(user_id, organization_id))


async def get_membership_cache(
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MembershipCache:
    return MembershipCache(redis, ttl_seconds=settings.membership_cache_ttl_seconds)
