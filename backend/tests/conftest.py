from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.config.settings import get_settings
from api.db.session import build_engine


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
async def session(engine) -> AsyncGenerator[AsyncSession]:
    """A session inside a transaction that is always rolled back.

    Each test sees a clean database and leaves nothing behind, so tests cannot order-
    depend on each other. The repository never commits, which is what makes this
    work — a repository that committed would escape the rollback.
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        async with factory() as db_session:
            yield db_session
        # Closing the session can already have ended the transaction; rolling back a
        # deassociated transaction warns rather than failing, so check first.
        if transaction.is_active:
            await transaction.rollback()
