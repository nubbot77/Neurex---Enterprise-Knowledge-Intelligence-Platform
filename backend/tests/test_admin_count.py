from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from api.models.membership import Membership, MembershipRole, MembershipStatus
from api.models.organization import Organization, OrganizationKind


async def _org(session, *, max_admins: int = 2, is_active: bool = True) -> Organization:
    org = Organization(
        name="Acme",
        slug=uuid.uuid4().hex,
        kind=OrganizationKind.TEAM,
        max_admins=max_admins,
        is_active=is_active,
    )
    session.add(org)
    await session.flush()
    return org


async def _user(session):
    from api.models.user import User

    user = User(email=f"{uuid.uuid4().hex}@example.test", password_hash="h", full_name="A")
    session.add(user)
    await session.flush()
    return user


async def _member(session, org, *, role=MembershipRole.MEMBER, status=MembershipStatus.ACTIVE):
    membership = Membership(
        user_id=(await _user(session)).id,
        organization_id=org.id,
        role=role,
        status=status,
    )
    session.add(membership)
    await session.flush()
    return membership


async def _count(session, org) -> int:
    return await session.scalar(
        select(Organization.active_admin_count).where(Organization.id == org.id)
    )


async def test_new_organization_starts_at_zero(session):
    """Zero is the legal transient state the CHECK cannot forbid."""
    org = await _org(session)

    assert await _count(session, org) == 0


async def test_active_admin_increments_the_counter(session):
    org = await _org(session)

    await _member(session, org, role=MembershipRole.ADMIN)

    assert await _count(session, org) == 1


async def test_pending_admin_does_not_count(session):
    """Only ACTIVE grants anything — an outstanding invitation must not hold a slot."""
    org = await _org(session)

    await _member(session, org, role=MembershipRole.ADMIN, status=MembershipStatus.PENDING)

    assert await _count(session, org) == 0


async def test_plain_member_does_not_count(session):
    org = await _org(session)

    await _member(session, org, role=MembershipRole.MEMBER)

    assert await _count(session, org) == 0


async def test_promotion_and_demotion_move_the_counter(session):
    org = await _org(session)
    admin = await _member(session, org, role=MembershipRole.ADMIN)
    second = await _member(session, org, role=MembershipRole.MEMBER)

    second.role = MembershipRole.ADMIN
    await session.flush()
    assert await _count(session, org) == 2

    second.role = MembershipRole.MEMBER
    await session.flush()
    assert await _count(session, org) == 1
    assert admin.role is MembershipRole.ADMIN


async def test_activating_a_pending_admin_counts(session):
    org = await _org(session)
    await _member(session, org, role=MembershipRole.ADMIN)
    invited = await _member(
        session, org, role=MembershipRole.ADMIN, status=MembershipStatus.PENDING
    )
    assert await _count(session, org) == 1

    invited.status = MembershipStatus.ACTIVE
    await session.flush()

    assert await _count(session, org) == 2


# -- the ceiling -----------------------------------------------------------


async def test_third_admin_is_rejected(session):
    org = await _org(session, max_admins=2)
    await _member(session, org, role=MembershipRole.ADMIN)
    await _member(session, org, role=MembershipRole.ADMIN)

    with pytest.raises(IntegrityError, match="ck_organizations_active_admin_count_range"):
        await _member(session, org, role=MembershipRole.ADMIN)


async def test_max_admins_is_configurable_per_organization(session):
    """The cap is a column, so raising it for one tenant needs no migration."""
    org = await _org(session, max_admins=3)
    for _ in range(3):
        await _member(session, org, role=MembershipRole.ADMIN)

    assert await _count(session, org) == 3


# -- the floor -------------------------------------------------------------


async def test_demoting_the_last_admin_is_rejected(session):
    org = await _org(session)
    admin = await _member(session, org, role=MembershipRole.ADMIN)

    admin.role = MembershipRole.MEMBER
    with pytest.raises(DBAPIError, match="no active admin"):
        await session.flush()


async def test_deleting_the_last_admin_is_rejected(session):
    org = await _org(session)
    admin = await _member(session, org, role=MembershipRole.ADMIN)

    await session.delete(admin)
    with pytest.raises(DBAPIError, match="no active admin"):
        await session.flush()


async def test_suspending_the_last_admin_is_rejected(session):
    org = await _org(session)
    admin = await _member(session, org, role=MembershipRole.ADMIN)

    admin.status = MembershipStatus.SUSPENDED
    with pytest.raises(DBAPIError, match="no active admin"):
        await session.flush()


async def test_removing_one_of_two_admins_is_allowed(session):
    org = await _org(session)
    first = await _member(session, org, role=MembershipRole.ADMIN)
    await _member(session, org, role=MembershipRole.ADMIN)

    await session.delete(first)
    await session.flush()

    assert await _count(session, org) == 1


async def test_inactive_organization_may_lose_its_last_admin(session):
    """Deactivating a tenant and then clearing its members is legitimate."""
    org = await _org(session, is_active=False)
    admin = await _member(session, org, role=MembershipRole.ADMIN)

    await session.delete(admin)
    await session.flush()

    assert await _count(session, org) == 0


# -- cascade ---------------------------------------------------------------


async def test_deleting_the_organization_does_not_trip_the_floor(session):
    """Cascading memberships away must not raise on a tenant that is going away."""
    org = await _org(session)
    await _member(session, org, role=MembershipRole.ADMIN)

    await session.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": org.id})
    await session.flush()

    remaining = await session.scalar(select(Membership).where(Membership.organization_id == org.id))
    assert remaining is None
