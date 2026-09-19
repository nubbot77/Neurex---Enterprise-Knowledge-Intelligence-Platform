"""RBAC — Phase 5, Task 12.

Two halves, and the second is the one that matters most:

* the **matrix test**: every role against every permission, asserting architecture
  §7.6. The expected table below is written out by hand rather than imported from
  ``ROLE_PERMISSIONS`` — a test that derives its expectations from the code under test
  asserts only that the code equals itself.
* the **default-deny test**: a route that declares no permission denies everyone
  (invariant 6). That is the guarantee most likely to regress silently, because
  nothing else in the system complains when it does.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from api.auth.context import OrgContext
from api.auth.permissions import (
    OWNERSHIP_SCOPED,
    Permission,
    permissions_for,
    requires_ownership_check,
)
from api.auth.rbac import DefaultDeny, require, scan_permission_declarations
from api.db.redis import get_redis
from api.db.session import get_session
from api.main import create_app
from api.models.membership import AccountType, MembershipRole
from helpers import add_member, create_team, register

# Architecture §7.6, transcribed. "yes" means the role holds the permission at all;
# ownership narrowing for a member's own conversations is asserted separately, because
# it is a resource-level rule rather than a role-level one.
MATRIX: dict[Permission, dict[MembershipRole, bool]] = {
    Permission.ORG_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.ORG_UPDATE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.ORG_DELETE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.MEMBER_INVITE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.MEMBER_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.MEMBER_UPDATE_ROLE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.MEMBER_REMOVE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.DOCUMENT_CREATE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.DOCUMENT_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.DOCUMENT_UPDATE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.DOCUMENT_DELETE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.DOCUMENT_REPROCESS: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.CONVERSATION_CREATE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.CONVERSATION_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.CONVERSATION_DELETE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.SEARCH_EXECUTE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.EVALUATION_CREATE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.EVALUATION_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: True},
    Permission.EVALUATION_RUN: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.APIKEY_CREATE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.APIKEY_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.APIKEY_REVOKE: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
    Permission.AUDIT_READ: {MembershipRole.ADMIN: True, MembershipRole.MEMBER: False},
}


# -- the matrix ---------------------------------------------------------------


def test_every_permission_appears_in_the_expected_matrix():
    """A new permission must be given a row here, deliberately.

    Without this, adding a ``Permission`` silently escapes the matrix test below and
    nobody ever decides which roles hold it.
    """
    assert set(MATRIX) == set(Permission)


@pytest.mark.parametrize("permission", list(Permission), ids=lambda p: p.value)
@pytest.mark.parametrize("role", list(MembershipRole), ids=lambda r: r.value)
def test_role_permission_matrix(role: MembershipRole, permission: Permission):
    assert (permission in permissions_for(role)) is MATRIX[permission][role]


def test_admin_holds_every_permission():
    assert permissions_for(MembershipRole.ADMIN) == frozenset(Permission)


def test_unknown_role_resolves_to_no_permissions():
    """Default deny, at the matrix level: an unmapped role holds nothing."""
    assert permissions_for("auditor") == frozenset()  # type: ignore[arg-type]


# -- ownership narrowing ------------------------------------------------------


def test_member_conversations_are_ownership_scoped():
    assert requires_ownership_check(MembershipRole.MEMBER, Permission.CONVERSATION_READ)
    assert requires_ownership_check(MembershipRole.MEMBER, Permission.CONVERSATION_DELETE)


def test_admin_conversations_are_not_ownership_scoped():
    assert OWNERSHIP_SCOPED[MembershipRole.ADMIN] == frozenset()
    assert not requires_ownership_check(MembershipRole.ADMIN, Permission.CONVERSATION_READ)


def test_ownership_check_is_a_second_step_not_a_withheld_permission(actor_context):
    """The member *holds* conversation:read; the row still has to be theirs."""
    ctx = actor_context(MembershipRole.MEMBER)

    assert ctx.has(Permission.CONVERSATION_READ)
    assert ctx.owns_or_has_full(Permission.CONVERSATION_READ, created_by=ctx.user_id)
    assert not ctx.owns_or_has_full(Permission.CONVERSATION_READ, created_by=None)


def test_admin_sees_conversations_it_did_not_create(actor_context):
    import uuid

    ctx = actor_context(MembershipRole.ADMIN)

    assert ctx.owns_or_has_full(Permission.CONVERSATION_READ, created_by=uuid.uuid4())


@pytest.fixture
def actor_context():
    import uuid

    def build(role: MembershipRole, account_type: AccountType = AccountType.MEMBER) -> OrgContext:
        return OrgContext(
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            membership_id=uuid.uuid4(),
            role=role,
            account_type=account_type,
            permissions=permissions_for(role),
            is_super_admin=False,
        )

    return build


# -- account_type is never an authorization input (invariant 5) ---------------


@pytest.mark.parametrize("account_type", list(AccountType), ids=lambda a: a.value)
def test_account_type_does_not_change_permissions(actor_context, account_type: AccountType):
    ctx = actor_context(MembershipRole.MEMBER, account_type)

    assert ctx.permissions == permissions_for(MembershipRole.MEMBER)


async def test_guest_seat_has_the_same_reach_as_a_member_seat(client):
    """The same assertion over HTTP: a ``guest`` seat is a member, no more and no less."""
    admin = await register(client)
    org_id = await create_team(client, admin)

    guest = await register(client)
    invited = await client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": guest.email, "role": "member", "account_type": "guest"},
        headers=admin.headers,
    )
    assert invited.status_code == 201
    await client.post(f"/api/v1/me/invitations/{org_id}/accept", headers=guest.headers)

    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=guest.headers)).status_code == 200
    assert (
        await client.patch(
            f"/api/v1/orgs/{org_id}", json={"name": "Renamed"}, headers=guest.headers
        )
    ).status_code == 403


# -- require() ----------------------------------------------------------------


def test_require_needs_at_least_one_permission():
    """A zero-argument require() would look like a declaration and demand nothing."""
    with pytest.raises(ValueError, match="at least one Permission"):
        require()


def test_require_marks_the_dependency_for_the_startup_scan():
    dependency = require(Permission.ORG_READ, Permission.ORG_UPDATE)

    assert dependency.__rbac_permissions__ == frozenset(
        {Permission.ORG_READ, Permission.ORG_UPDATE}
    )


async def test_member_is_refused_an_admin_only_route(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, _ = await add_member(client, admin, org_id)

    allowed = await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)
    refused = await client.patch(
        f"/api/v1/orgs/{org_id}", json={"name": "Renamed"}, headers=member.headers
    )

    assert allowed.status_code == 200
    # 403, not 404: membership is established, so the caller already knows the
    # organization exists and a precise answer leaks nothing (§7.8).
    assert refused.status_code == 403


async def test_admin_passes_the_same_route(client):
    admin = await register(client)
    org_id = await create_team(client, admin)

    response = await client.patch(
        f"/api/v1/orgs/{org_id}", json={"name": "Renamed"}, headers=admin.headers
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


# -- default deny (invariant 6) -----------------------------------------------


async def test_route_without_a_declared_permission_denies_everyone(
    connection, redis, settings, session
):
    """The guarantee, tested the only way that means anything: by forgetting.

    A route is mounted on an organization router with no ``require(...)`` at all — the
    mistake this system is built to survive — and then called by an admin, who holds
    every permission there is. It must still be refused.
    """
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from api.auth.dependencies import get_org_context

    factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )

    async def override_session() -> AsyncGenerator[AsyncSession]:
        async with factory() as db_session:
            yield db_session

    async def override_redis():
        return redis

    app: FastAPI = create_app(settings)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_redis] = override_redis

    forgetful = APIRouter(prefix="/orgs/{organization_id}", dependencies=[DefaultDeny])

    @forgetful.get("/undeclared")
    async def undeclared(ctx: Annotated[OrgContext, Depends(get_org_context)]) -> dict[str, str]:
        return {"organization_id": str(ctx.organization_id)}

    app.include_router(forgetful, prefix="/api/v1")
    # Re-run the scan so the new route is considered; it declares nothing, so it must
    # not appear in the declared set.
    declared = scan_permission_declarations(app)
    assert undeclared not in declared

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as http:
        admin = await register(http)
        org_id = await create_team(http, admin)

        response = await http.get(f"/api/v1/orgs/{org_id}/undeclared", headers=admin.headers)

    assert response.status_code == 403


async def test_every_org_scoped_route_declares_a_permission(settings):
    """The audit the startup scan performs, asserted as a test.

    A route added under ``/orgs/{organization_id}/`` in a later phase without a
    declaration fails here as well as being refused at runtime — which is the point of
    having both.
    """
    from api.auth.rbac import iter_api_routes, route_permissions

    app = create_app(settings)

    undeclared = [
        f"{sorted(route.methods)[0]} {path}"
        for path, route in iter_api_routes(app)
        if "/orgs/{organization_id}" in path and route_permissions(route) is None
    ]

    assert undeclared == []
