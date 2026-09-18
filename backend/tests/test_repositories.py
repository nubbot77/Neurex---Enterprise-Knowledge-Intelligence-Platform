from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from api.db.repositories.users import UserRepository
from api.models.user import User


def _email() -> str:
    return f"{uuid.uuid4().hex}@example.test"


async def test_create_populates_primary_key_and_defaults(session):
    repo = UserRepository(session)

    user = await repo.create(email=_email(), password_hash="h", full_name="Ada")

    # flush() emitted the INSERT, so the server-generated state is readable without
    # the caller having committed anything.
    assert isinstance(user.id, uuid.UUID)
    assert user.is_active is True
    assert user.is_super_admin is False
    assert user.created_at is not None


async def test_get_round_trip(session):
    repo = UserRepository(session)
    created = await repo.create(email=_email(), password_hash="h", full_name="Ada")

    fetched = await repo.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id


async def test_get_returns_none_when_absent(session):
    repo = UserRepository(session)

    assert await repo.get(uuid.uuid4()) is None


async def test_get_by_email(session):
    repo = UserRepository(session)
    email = _email()
    await repo.create(email=email, password_hash="h", full_name="Ada")

    found = await repo.get_by_email(email)

    assert found is not None
    assert found.email == email
    assert await repo.get_by_email(_email()) is None


async def test_update_persists(session):
    repo = UserRepository(session)
    user = await repo.create(email=_email(), password_hash="h", full_name="Ada")

    await repo.update(user, full_name="Ada Lovelace", is_super_admin=True)
    session.expunge_all()
    reloaded = await repo.get(user.id)

    assert reloaded is not None
    assert reloaded.full_name == "Ada Lovelace"
    assert reloaded.is_super_admin is True


async def test_delete_removes_the_row(session):
    repo = UserRepository(session)
    user = await repo.create(email=_email(), password_hash="h", full_name="Ada")

    await repo.delete(user)

    assert await repo.get(user.id) is None


async def test_exists_and_count(session):
    repo = UserRepository(session)
    email = _email()

    assert await repo.email_exists(email) is False
    before = await repo.count()

    await repo.create(email=email, password_hash="h", full_name="Ada")

    assert await repo.email_exists(email) is True
    assert await repo.count() == before + 1
    assert await repo.count(email=email) == 1


async def test_list_paginates(session):
    repo = UserRepository(session)
    for _ in range(3):
        await repo.create(email=_email(), password_hash="h", full_name="Ada")

    page = await repo.list(limit=2, offset=0, order_by=User.created_at)

    assert len(page) == 2


async def test_unknown_filter_field_raises(session):
    repo = UserRepository(session)

    # A silently ignored filter would widen the query, and a widened query is how
    # rows leak. Phase 5 depends on this failing loudly.
    with pytest.raises(AttributeError):
        await repo.get_by(not_a_column="x")


async def test_duplicate_email_violates_unique_index(session):
    repo = UserRepository(session)
    email = _email()
    await repo.create(email=email, password_hash="h", full_name="Ada")

    with pytest.raises(IntegrityError):
        await repo.create(email=email, password_hash="h", full_name="Grace")


async def test_repository_does_not_commit(session):
    """The rollback in the fixture must be able to undo everything written here.

    If a repository method committed, this row would survive the fixture teardown and
    leak into the next test.
    """
    repo = UserRepository(session)
    await repo.create(email=_email(), password_hash="h", full_name="Ada")

    assert session.in_transaction() is True
