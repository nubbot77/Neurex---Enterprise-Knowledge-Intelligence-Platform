"""Token revocation — Phase 4, Task 9.

A JWT's selling point is that it needs no server-side lookup. Its cost is that it stays
valid until ``exp``, so "log me out" and "this account is compromised" have nothing to
act on. A deny-list restores that, at the price of one Redis round-trip per request.

The design keeps that price small by storing the **exception** rather than the session:
Redis holds only revoked tokens, each with a TTL equal to the life the token had left,
so entries delete themselves and the list stays roughly the size of the last few
minutes of logouts — not the size of the user base.

Two kinds of entry:

``revoked:jti:{jti}``    one token, killed by logout or by refresh rotation
``revoked:user:{sub}``   a cutoff timestamp; every token issued before it is dead
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis

from api.auth.jwt import TokenClaims
from api.db.redis import get_redis

_JTI_PREFIX = "revoked:jti:"
_USER_PREFIX = "revoked:user:"


class RevocationStore:
    """The deny-list every authenticated request is checked against."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def revoke(self, claims: TokenClaims) -> None:
        """Kill one token.

        The TTL is the token's own remaining life: once it would have expired anyway,
        the entry is pointless. An already-expired token is not stored at all, since
        ``decode_token`` rejects it before the deny-list is ever consulted.
        """
        ttl = claims.seconds_until_expiry
        if ttl > 0:
            # The value is never read; only the key's existence matters. ``set(ex=…)``
            # rather than ``setex`` — the latter is deprecated in redis-py 8.
            await self.redis.set(f"{_JTI_PREFIX}{claims.jti}", "1", ex=ttl)

    async def revoke_all_for_user(self, user_id: UUID, *, ttl_seconds: int) -> None:
        """Log a user out of everything, everywhere.

        One cutoff key instead of enumerating that user's outstanding token ids —
        cheaper, and complete: it also covers tokens this process has never seen.
        Used by reuse detection, and available to Phase 5 for a compromised account.
        """
        now = int(datetime.now(UTC).timestamp())
        await self.redis.set(f"{_USER_PREFIX}{user_id}", str(now), ex=ttl_seconds)

    async def is_revoked(self, claims: TokenClaims) -> bool:
        """True when this token must be rejected despite a valid signature."""
        if await self.redis.exists(f"{_JTI_PREFIX}{claims.jti}"):
            return True

        cutoff = await self.redis.get(f"{_USER_PREFIX}{claims.sub}")
        if cutoff is None:
            return False

        # ``iat`` has one-second resolution, so a token minted in the same second as the
        # cutoff compares equal. Treat that as revoked: issuing a fresh pair immediately
        # after a mass revocation is the caller's job, and it will carry a later ``iat``
        # only if a second has passed — erring the other way would let the token that
        # triggered the revocation survive it.
        return int(claims.iat.timestamp()) <= int(cutoff)


async def get_revocation_store(redis: Annotated[Redis, Depends(get_redis)]) -> RevocationStore:
    return RevocationStore(redis)
