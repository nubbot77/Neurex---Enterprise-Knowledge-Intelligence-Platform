"""Redis client — Phase 4, Task 8.

Redis was running from Phase 1 but nothing connected to it. Revocation is the first
consumer; Phase 5 adds the membership cache, and later phases add the job queue and
rate limiting.

The pool is opened once in the app lifespan, not per request. Every authenticated
request now makes a Redis round-trip for the revocation check, so this sits on the
critical path of the whole API.
"""

from __future__ import annotations

from fastapi import Request
from redis.asyncio import Redis

from api.config.settings import Settings


def build_redis(settings: Settings) -> Redis:
    """Create the client.

    ``decode_responses=True`` because everything stored here is short ASCII — revoked
    token ids and timestamps — and comparing ``str`` to ``str`` avoids a class of
    bytes-versus-str bugs at the call sites.
    """
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        health_check_interval=30,
    )


async def get_redis(request: Request) -> Redis:
    """FastAPI dependency: the pool built at startup."""
    return request.app.state.redis
