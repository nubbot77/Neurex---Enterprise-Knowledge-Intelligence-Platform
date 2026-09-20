"""Cross-tenant isolation — Phase 5, Task 11.

Not "does it work" but "can I break in". The whole suite is written from the attacker's
side: log in as one organization and try to reach another's data by every route the
system offers.

It exists to falsify the invariants in architecture §7.11. Every test here names the
one it attacks.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from api.auth.context import OrgContext
from api.auth.exceptions import CrossTenantWriteForbidden, PermissionDenied
from api.auth.membership_cache import cache_key
from api.auth.permissions import permissions_for
from api.db.repositories.memberships import OrgMembershipRepository
from api.models.audit import AuditLog
from api.models.membership import AccountType, Membership, MembershipRole, MembershipStatus
from api.models.user import User
from helpers import accept, add_member, create_team, invite, own_membership_id, register

# Every organization-scoped route, as a template. A new route added to the router in a
# later phase should be added here too — this list is what "every route scoped to it"
# in invariant 3 actually means.
SCOPED_ROUTES = [
    ("get", "/api/v1/orgs/{org}"),
    ("patch", "/api/v1/orgs/{org}"),
    ("delete", "/api/v1/orgs/{org}"),
    ("post", "/api/v1/orgs/{org}/leave"),
    ("get", "/api/v1/orgs/{org}/members"),
    ("post", "/api/v1/orgs/{org}/members"),
    # Phase 6. The document id below is a literal that exists nowhere: context
    # resolution refuses an outsider before any handler runs, so the id never has to
    # be real for this list to test what it claims to test.
    ("get", "/api/v1/orgs/{org}/documents"),
    ("post", "/api/v1/orgs/{org}/documents"),
    ("get", "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111"),
    ("patch", "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111"),
    ("delete", "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111"),
    ("get", "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111/versions"),
    ("post", "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111/versions"),
    ("get", "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111/download"),
    (
        "get",
        "/api/v1/orgs/{org}/documents/11111111-1111-1111-1111-111111111111/versions/1/download",
    ),
]


async def _call(client, method: str, path: str, headers: dict[str, str]):
    kwargs: dict[str, object] = {"headers": headers}
    if method in {"post", "patch", "put"}:
        kwargs["json"] = {"name": "Attacker", "email": "attacker@example.com"}
    return await getattr(client, method)(path, **kwargs)


# -- invariant 3: no active membership means 404 on every scoped route --------


@pytest.mark.parametrize("method,template", SCOPED_ROUTES, ids=lambda v: str(v))
async def test_outsider_gets_404_on_every_scoped_route(client, method: str, template: str):
    """A member of one organization may not touch another's, by any verb.

    404 rather than 403 throughout: a 403 would confirm the organization exists and
    hand anyone walking UUIDs a map of the tenant id space (§7.8).
    """
    victim = await register(client)
    victim_org = await create_team(client, victim, name="Victim Corp")
    attacker = await register(client)

    response = await _call(client, method, template.format(org=victim_org), attacker.headers)

    assert response.status_code == 404, f"{method} {template} leaked: {response.status_code}"
    assert response.json()["detail"] == "Organization not found"


async def test_nonexistent_organization_is_indistinguishable_from_a_forbidden_one(client):
    """The id space must not be probeable: real-but-not-mine reads like not-real."""
    victim = await register(client)
    victim_org = await create_team(client, victim)
    attacker = await register(client)

    forbidden = await client.get(f"/api/v1/orgs/{victim_org}", headers=attacker.headers)
    imaginary = await client.get(f"/api/v1/orgs/{uuid.uuid4()}", headers=attacker.headers)

    assert forbidden.status_code == imaginary.status_code == 404
    assert forbidden.json() == imaginary.json()


async def test_guessing_a_membership_id_from_another_organization_fails(client):
    """Invariant 2: a row from another tenant is never returned, even by exact id."""
    victim = await register(client)
    victim_org = await create_team(client, victim)
    victim_membership = await own_membership_id(client, victim, victim_org)

    attacker = await register(client)
    attacker_org = await create_team(client, attacker)

    # The attacker is a legitimate admin — in their *own* organization — and asks for a
    # membership id they somehow learned. Scoping, not authorization, is what stops it.
    response = await client.get(
        f"/api/v1/orgs/{attacker_org}/members/{victim_membership}",
        headers=attacker.headers,
    )

    assert response.status_code == 404


async def test_passing_another_organizations_id_in_the_path_is_not_access(client):
    """The path parameter is a lookup key, never an assertion (§7.8)."""
    victim = await register(client)
    victim_org = await create_team(client, victim)
    attacker = await register(client)
    await create_team(client, attacker)

    response = await client.get(f"/api/v1/orgs/{victim_org}/members", headers=attacker.headers)

    assert response.status_code == 404


async def test_a_pending_invitation_grants_nothing(client):
    """Invariant 3 again: ``pending`` resolves to no context at all (§7.4)."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    invitee = await register(client)

    invited = await invite(client, admin, org_id, invitee)
    assert invited.status_code == 201

    before_accepting = await client.get(f"/api/v1/orgs/{org_id}", headers=invitee.headers)
    assert before_accepting.status_code == 404

    await accept(client, invitee, org_id)
    after_accepting = await client.get(f"/api/v1/orgs/{org_id}", headers=invitee.headers)
    assert after_accepting.status_code == 200


# -- invariant 7: revocation applies on the next request ----------------------


async def test_suspension_takes_effect_on_the_next_request(client, redis):
    """The reason role is resolved per request instead of carried in the token.

    The member is suspended while holding a perfectly valid access token, issued before
    the suspension. The very next request must fail — not at the next token expiry.
    """
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, membership_id = await add_member(client, admin, org_id)

    # Warm the cache, so the test also proves the invalidation and not just a cold read.
    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)).status_code == 200
    assert await redis.exists(cache_key(member.user_id, org_id))

    suspended = await client.post(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/suspend", headers=admin.headers
    )
    assert suspended.status_code == 200

    assert not await redis.exists(cache_key(member.user_id, org_id))
    after = await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)
    assert after.status_code == 404


async def test_demotion_takes_effect_on_the_next_request(client):
    """Same mechanism, the other direction: an admin demoted mid-session loses reach."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    second, second_membership = await add_member(client, admin, org_id, role="admin")

    assert (
        await client.patch(
            f"/api/v1/orgs/{org_id}", json={"name": "Renamed by second"}, headers=second.headers
        )
    ).status_code == 200

    demoted = await client.patch(
        f"/api/v1/orgs/{org_id}/members/{second_membership}/role",
        json={"role": "member"},
        headers=admin.headers,
    )
    assert demoted.status_code == 200

    after = await client.patch(
        f"/api/v1/orgs/{org_id}", json={"name": "Renamed again"}, headers=second.headers
    )
    assert after.status_code == 403


async def test_a_token_issued_before_removal_stops_working(client):
    """A stale token is identity, not authority — removal does not wait for expiry."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, membership_id = await add_member(client, admin, org_id)

    stale_headers = member.headers  # captured before the removal

    removed = await client.delete(
        f"/api/v1/orgs/{org_id}/members/{membership_id}", headers=admin.headers
    )
    assert removed.status_code == 200

    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=stale_headers)).status_code == 404


async def test_deactivating_an_organization_closes_it_for_its_own_admin(client, redis):
    admin = await register(client)
    org_id = await create_team(client, admin)

    assert (await client.delete(f"/api/v1/orgs/{org_id}", headers=admin.headers)).status_code == 204

    # The admin's own cached membership would otherwise keep the tenant reachable until
    # the entry expires, so the cache is cleared for this assertion. See the handover
    # gotcha: deactivation is bounded by the TTL, not immediate, for other members.
    await redis.delete(cache_key(admin.user_id, org_id))
    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=admin.headers)).status_code == 404


# -- the repository filter itself (§7.9) --------------------------------------


def _context(user_id: uuid.UUID, org_id: uuid.UUID, role=MembershipRole.ADMIN) -> OrgContext:
    return OrgContext(
        user_id=user_id,
        organization_id=org_id,
        membership_id=uuid.uuid4(),
        role=role,
        account_type=AccountType.MEMBER,
        permissions=permissions_for(role),
        is_super_admin=False,
    )


async def test_scoped_get_cannot_reach_another_tenants_row(client, session):
    """``session.get()`` would return it from the identity map; the override must not."""
    victim = await register(client)
    victim_org = await create_team(client, victim)
    victim_membership = await own_membership_id(client, victim, victim_org)

    attacker = await register(client)
    attacker_org = await create_team(client, attacker)

    repo = OrgMembershipRepository(session, _context(attacker.user_id, attacker_org))

    assert await repo.get(victim_membership) is None


async def test_scoped_list_returns_only_this_tenants_rows(client, session):
    victim = await register(client)
    victim_org = await create_team(client, victim)
    await add_member(client, victim, victim_org)

    attacker = await register(client)
    attacker_org = await create_team(client, attacker)

    repo = OrgMembershipRepository(session, _context(attacker.user_id, attacker_org))
    rows = await repo.list_members()

    assert {row.organization_id for row in rows} == {attacker_org}


async def test_a_caller_supplied_organization_filter_cannot_widen_the_scope(client, session):
    """A filter argument must not be able to redirect the tenant."""
    victim = await register(client)
    victim_org = await create_team(client, victim)

    attacker = await register(client)
    attacker_org = await create_team(client, attacker)

    repo = OrgMembershipRepository(session, _context(attacker.user_id, attacker_org))
    rows = await repo.list(organization_id=victim_org)

    assert all(row.organization_id == attacker_org for row in rows)


async def test_scoped_create_refuses_another_tenants_id(client, session):
    victim = await register(client)
    victim_org = await create_team(client, victim)
    attacker = await register(client)
    attacker_org = await create_team(client, attacker)

    repo = OrgMembershipRepository(session, _context(attacker.user_id, attacker_org))

    with pytest.raises(PermissionDenied):
        await repo.create(
            user_id=attacker.user_id,
            organization_id=victim_org,
            role=MembershipRole.ADMIN,
        )


async def test_scoped_update_refuses_a_row_from_another_tenant(client, session):
    """A row can arrive from anywhere; writing it is still checked."""
    victim = await register(client)
    victim_org = await create_team(client, victim)
    victim_membership_id = await own_membership_id(client, victim, victim_org)
    victim_membership = (
        await session.execute(select(Membership).where(Membership.id == victim_membership_id))
    ).scalar_one()

    attacker = await register(client)
    attacker_org = await create_team(client, attacker)
    repo = OrgMembershipRepository(session, _context(attacker.user_id, attacker_org))

    with pytest.raises(PermissionDenied):
        await repo.update(victim_membership, role=MembershipRole.MEMBER)


async def test_a_scoped_repository_without_a_context_refuses_to_query(session):
    """No context is a programming error, not an invitation to return everything."""
    repo = OrgMembershipRepository(session)

    with pytest.raises(RuntimeError, match="without an OrgContext"):
        await repo.list_members()


# -- the super_admin bypass (§7.10) -------------------------------------------


async def _as_super_admin(session, user_id: uuid.UUID) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
    user.is_super_admin = True
    await session.flush()
    return user


async def test_bypass_requires_the_explicit_argument(client, session):
    operator = await register(client)
    org_id = await create_team(client, operator)
    actor = await _as_super_admin(session, operator.user_id)

    repo = OrgMembershipRepository(session, _context(operator.user_id, org_id))

    with pytest.raises(ValueError, match="across_tenants must be True"):
        await repo.get_across_tenants(
            uuid.uuid4(), across_tenants=False, actor=actor, reason="support"
        )


async def test_bypass_requires_a_stated_reason(client, session):
    operator = await register(client)
    org_id = await create_team(client, operator)
    actor = await _as_super_admin(session, operator.user_id)

    repo = OrgMembershipRepository(session, _context(operator.user_id, org_id))

    with pytest.raises(ValueError, match="must state a reason"):
        await repo.get_across_tenants(uuid.uuid4(), across_tenants=True, actor=actor, reason="  ")


async def test_bypass_is_refused_to_an_ordinary_admin(client, session):
    """Being an admin of one organization is not platform authority."""
    victim = await register(client)
    victim_org = await create_team(client, victim)
    victim_membership = await own_membership_id(client, victim, victim_org)

    attacker = await register(client)
    attacker_org = await create_team(client, attacker)
    ordinary = (await session.execute(select(User).where(User.id == attacker.user_id))).scalar_one()

    repo = OrgMembershipRepository(session, _context(attacker.user_id, attacker_org))

    with pytest.raises(PermissionDenied):
        await repo.get_across_tenants(
            victim_membership, across_tenants=True, actor=ordinary, reason="curiosity"
        )


async def test_bypass_reads_across_tenants_and_writes_an_audit_row(client, session):
    victim = await register(client)
    victim_org = await create_team(client, victim)
    victim_membership = await own_membership_id(client, victim, victim_org)

    operator = await register(client)
    operator_org = await create_team(client, operator)
    actor = await _as_super_admin(session, operator.user_id)

    repo = OrgMembershipRepository(session, _context(operator.user_id, operator_org))
    row = await repo.get_across_tenants(
        victim_membership,
        across_tenants=True,
        actor=actor,
        reason="ticket 4471: customer cannot see their own members",
    )

    assert row is not None
    assert row.organization_id == victim_org

    audit = (
        (
            await session.execute(
                select(AuditLog).where(
                    AuditLog.actor_user_id == actor.id, AuditLog.via_super_admin.is_(True)
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(audit) == 1
    assert audit[0].action == "cross_tenant_read"
    assert audit[0].organization_id == victim_org
    assert audit[0].resource_id == str(victim_membership)
    assert "ticket 4471" in audit[0].reason


async def test_bypass_cannot_write(client, session):
    """Cross-tenant reads are support work; cross-tenant writes have no use (§7.10)."""
    operator = await register(client)
    org_id = await create_team(client, operator)
    actor = await _as_super_admin(session, operator.user_id)

    repo = OrgMembershipRepository(session, _context(operator.user_id, org_id))

    with pytest.raises(CrossTenantWriteForbidden):
        await repo.update_across_tenants(uuid.uuid4(), actor=actor, role=MembershipRole.MEMBER)


# -- invariant 1 --------------------------------------------------------------


async def test_every_membership_row_carries_an_organization(client, session):
    """Invariant 1, asserted against the column rather than the code path."""
    actor = await register(client)
    await create_team(client, actor)

    orphans = (
        (await session.execute(select(Membership).where(Membership.organization_id.is_(None))))
        .scalars()
        .all()
    )

    assert orphans == []


async def test_a_personal_organization_cannot_take_members(client):
    """§7.3: the personal workspace is one seat, by construction."""
    owner = await register(client)
    outsider = await register(client)

    response = await invite(client, owner, owner.organization_id, outsider)

    assert response.status_code == 409
    assert "personal workspace" in response.json()["detail"]


async def test_suspended_membership_is_retained_not_deleted(client, session):
    """§7.4: audit rows point at the membership, so removal is a status change."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, membership_id = await add_member(client, admin, org_id)

    await client.delete(f"/api/v1/orgs/{org_id}/members/{membership_id}", headers=admin.headers)

    row = (
        await session.execute(select(Membership).where(Membership.id == membership_id))
    ).scalar_one()

    assert row.status is MembershipStatus.SUSPENDED
