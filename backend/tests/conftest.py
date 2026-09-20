from __future__ import annotations

from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from api.auth.dependencies import get_storage
from api.config.settings import get_settings
from api.db.redis import get_redis
from api.db.session import build_engine, get_session
from api.main import create_app
from fakes import InMemoryStorage


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest_asyncio.fixture(scope="session")
async def engine(settings):
    """One engine for the whole run.

    Goes through PgBouncer, like the app does, so the Task 3 settings (NullPool,
    statement_cache_size=0) are exercised by real traffic rather than assumed.
    """
    eng = build_engine(settings)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def connection(engine) -> AsyncGenerator[AsyncConnection]:
    """One connection per test, inside a transaction that is always rolled back.

    Everything a test touches — the ``session`` fixture and the app behind the
    ``client`` fixture — runs on *this* connection. That matters: two connections would
    sit in two transactions, so rows written through the API would be invisible to the
    test's own session and vice versa.
    """
    async with engine.connect() as conn:
        transaction = await conn.begin()
        yield conn
        # Closing the session can already have ended the transaction; rolling back a
        # deassociated transaction warns rather than failing, so check first.
        if transaction.is_active:
            await transaction.rollback()


def _session_factory(connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    """Sessions that commit into a SAVEPOINT rather than the outer transaction.

    ``join_transaction_mode="create_savepoint"`` is what lets the service commit for
    real — registration has to, its three rows are one transaction — while the outer
    rollback still wipes everything the test wrote.
    """
    return async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture
async def session(connection) -> AsyncGenerator[AsyncSession]:
    """A session for talking to the database directly."""
    async with _session_factory(connection)() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis]:
    """An in-process Redis.

    The revocation store only uses SET with an expiry, GET and EXISTS, all of which
    fakeredis implements faithfully including TTL expiry. Running it in-process keeps
    the auth tests independent of a container being up, and gives every test an empty
    deny-list.
    """
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def storage() -> InMemoryStorage:
    """Object storage for one test, in a dictionary.

    Phase 6 writes bytes to R2. A test suite that needed a bucket would need
    credentials, a network and a cleanup story, and would stop being runnable on a
    laptop — so the provider is swapped and everything above it is the real code.
    """
    return InMemoryStorage()


@pytest_asyncio.fixture
async def client(connection, redis, settings, storage) -> AsyncGenerator[AsyncClient]:
    """An HTTP client against the real app, on the test's own transaction."""
    factory = _session_factory(connection)

    async def override_session() -> AsyncGenerator[AsyncSession]:
        async with factory() as db_session:
            yield db_session

    async def override_redis():
        return redis

    def override_storage() -> InMemoryStorage:
        return storage

    app = create_app(settings)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = override_redis
    # The app never runs its lifespan under ASGITransport, so app.state.storage is
    # never set and the real dependency would answer 503. This override is the only
    # source of a storage provider in tests, exactly as the two above are for the
    # session and Redis.
    app.dependency_overrides[get_storage] = override_storage

    # ASGITransport talks to the app object directly — no socket and no lifespan, so
    # the overrides above are the only sources of a session and a Redis client.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as http_client:
        yield http_client
