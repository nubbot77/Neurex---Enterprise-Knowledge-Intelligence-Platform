"""Membership lifecycle and the admin range — Phase 5, Tasks 1 and 8.

Architecture §7.4 and §7.7. The database is the authority on the admin range; what is
tested here is that the service reaches the same verdict *first*, so the caller sees a
409 they can act on rather than a constraint violation surfaced as a 500.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from api.auth.membership_cache import cache_key
from api.models.audit import AuditLog
from api.models.membership import Membership, MembershipRole, MembershipStatus
from api.models.organization import Organization, OrganizationKind
from helpers import accept, add_member, create_team, invite, own_membership_id, register

# -- creating a team ----------------------------------------------------------


async def test_creating_a_team_makes_the_creator_its_first_admin(client, session):
    actor = await register(client)

    org_id = await create_team(client, actor, name="Acme")

    organization = (
        await session.execute(select(Organization).where(Organization.id == org_id))
    ).scalar_one()
    membership = (
        await session.execute(
            select(Membership).where(
                Membership.organization_id == org_id, Membership.user_id == actor.user_id
            )
        )
    ).scalar_one()

    assert organization.kind is OrganizationKind.TEAM
    assert organization.active_admin_count == 1
    assert membership.role is MembershipRole.ADMIN
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.joined_at is not None


async def test_personal_and_team_organizations_both_appear_in_my_list(client):
    actor = await register(client)
    org_id = await create_team(client, actor)

    response = await client.get("/api/v1/me/organizations", headers=actor.headers)

    kinds = {row["organization"]["kind"] for row in response.json()}
    ids = {row["organization"]["id"] for row in response.json()}
    assert kinds == {"personal", "team"}
    assert str(org_id) in ids


# -- invite and accept --------------------------------------------------------


async def test_invitation_starts_pending_and_activates_on_accept(client, session):
    admin = await register(client)
    org_id = await create_team(client, admin)
    invitee = await register(client)

    invited = await invite(client, admin, org_id, invitee)
    assert invited.status_code == 201
    assert invited.json()["status"] == "pending"
    assert invited.json()["joined_at"] is None
    assert invited.json()["invited_by_id"] == str(admin.user_id)

    accepted = await accept(client, invitee, org_id)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "active"
    assert accepted.json()["joined_at"] is not None


async def test_inviting_an_unknown_address_is_refused(client):
    """No row is written for an address nobody could ever accept from."""
    admin = await register(client)
    org_id = await create_team(client, admin)

    response = await client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": f"{uuid.uuid4().hex}@example.com"},
        headers=admin.headers,
    )

    assert response.status_code == 409
    assert "No active account" in response.json()["detail"]


async def test_inviting_an_existing_member_is_refused(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, _ = await add_member(client, admin, org_id)

    response = await invite(client, admin, org_id, member)

    assert response.status_code == 409
    assert "already a member" in response.json()["detail"]


async def test_accepting_twice_is_refused(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    invitee = await register(client)
    await invite(client, admin, org_id, invitee)

    assert (await accept(client, invitee, org_id)).status_code == 200
    second = await accept(client, invitee, org_id)

    assert second.status_code == 409
    assert "not pending" in second.json()["detail"]


async def test_accepting_an_invitation_that_was_never_issued_is_a_404(client):
    """Same answer as an organization that does not exist — nothing is confirmed."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    outsider = await register(client)

    response = await accept(client, outsider, org_id)

    assert response.status_code == 404


async def test_a_member_cannot_invite(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, _ = await add_member(client, admin, org_id)
    outsider = await register(client)

    response = await invite(client, member, org_id, outsider)

    assert response.status_code == 403


# -- role changes -------------------------------------------------------------


async def test_promotion_and_demotion(client, session):
    admin = await register(client)
    org_id = await create_team(client, admin)
    _, membership_id = await add_member(client, admin, org_id)

    promoted = await client.patch(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/role",
        json={"role": "admin"},
        headers=admin.headers,
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"

    demoted = await client.patch(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/role",
        json={"role": "member"},
        headers=admin.headers,
    )
    assert demoted.status_code == 200

    count = await session.scalar(
        select(Organization.active_admin_count).where(Organization.id == org_id)
    )
    assert count == 1


async def test_changing_a_role_invalidates_the_cached_membership(client, redis):
    """Invariant 7 at the cache level: the key is dropped by the write itself."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, membership_id = await add_member(client, admin, org_id)

    await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)
    assert await redis.exists(cache_key(member.user_id, org_id))

    await client.patch(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/role",
        json={"role": "admin"},
        headers=admin.headers,
    )

    assert not await redis.exists(cache_key(member.user_id, org_id))


# -- the admin range, both ends (§7.7) ----------------------------------------


async def test_a_third_admin_is_refused_with_409(client):
    """The ceiling: two by default, and the service answers before the CHECK does."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    await add_member(client, admin, org_id, role="admin")  # the second admin
    _, third = await add_member(client, admin, org_id)

    response = await client.patch(
        f"/api/v1/orgs/{org_id}/members/{third}/role",
        json={"role": "admin"},
        headers=admin.headers,
    )

    assert response.status_code == 409
    assert "at most" in response.json()["detail"]


async def test_accepting_an_admin_invitation_past_the_ceiling_is_refused(client):
    """The count moves at accept, not at invite, so that is where the check fires."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    await add_member(client, admin, org_id, role="admin")

    third = await register(client)
    invited = await invite(client, admin, org_id, third, role="admin")
    assert invited.status_code == 201  # a pending admin is not an active one

    response = await accept(client, third, org_id)

    assert response.status_code == 409


async def test_demoting_the_last_admin_is_refused(client):
    """The floor. A cap alone would let an organization reach zero admins."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    membership_id = await own_membership_id(client, admin, org_id)

    response = await client.patch(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/role",
        json={"role": "member"},
        headers=admin.headers,
    )

    assert response.status_code == 409
    assert "at least one active admin" in response.json()["detail"]


async def test_the_last_admin_cannot_leave(client):
    """A voluntary departure moves the count exactly as a removal does."""
    admin = await register(client)
    org_id = await create_team(client, admin)

    response = await client.post(f"/api/v1/orgs/{org_id}/leave", headers=admin.headers)

    assert response.status_code == 409


async def test_the_last_admin_cannot_remove_themselves(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    membership_id = await own_membership_id(client, admin, org_id)

    response = await client.delete(
        f"/api/v1/orgs/{org_id}/members/{membership_id}", headers=admin.headers
    )

    assert response.status_code == 409


async def test_one_of_two_admins_may_leave(client, session):
    admin = await register(client)
    org_id = await create_team(client, admin)
    second, _ = await add_member(client, admin, org_id, role="admin")

    response = await client.post(f"/api/v1/orgs/{org_id}/leave", headers=second.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"
    count = await session.scalar(
        select(Organization.active_admin_count).where(Organization.id == org_id)
    )
    assert count == 1


async def test_a_member_may_leave_freely(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, _ = await add_member(client, admin, org_id)

    left = await client.post(f"/api/v1/orgs/{org_id}/leave", headers=member.headers)

    assert left.status_code == 200
    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)).status_code == 404


async def test_lowering_max_admins_below_the_current_count_is_refused(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    await add_member(client, admin, org_id, role="admin")

    response = await client.patch(
        f"/api/v1/orgs/{org_id}", json={"max_admins": 1}, headers=admin.headers
    )

    assert response.status_code == 409
    assert "demote one" in response.json()["detail"]


async def test_raising_max_admins_allows_a_third(client):
    """``max_admins`` is a column so a plan change is an UPDATE, not a migration."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    await add_member(client, admin, org_id, role="admin")
    _, third = await add_member(client, admin, org_id)

    raised = await client.patch(
        f"/api/v1/orgs/{org_id}", json={"max_admins": 3}, headers=admin.headers
    )
    assert raised.status_code == 200

    promoted = await client.patch(
        f"/api/v1/orgs/{org_id}/members/{third}/role",
        json={"role": "admin"},
        headers=admin.headers,
    )

    assert promoted.status_code == 200


# -- suspend, remove, reinstate ----------------------------------------------


async def test_suspend_then_reinstate_restores_access(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, membership_id = await add_member(client, admin, org_id)

    await client.post(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/suspend", headers=admin.headers
    )
    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)).status_code == 404

    reinstated = await client.post(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/reinstate", headers=admin.headers
    )

    assert reinstated.status_code == 200
    assert (await client.get(f"/api/v1/orgs/{org_id}", headers=member.headers)).status_code == 200


async def test_suspending_twice_is_refused(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    _, membership_id = await add_member(client, admin, org_id)

    first = await client.post(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/suspend", headers=admin.headers
    )
    second = await client.post(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/suspend", headers=admin.headers
    )

    assert first.status_code == 200
    assert second.status_code == 409


async def test_reinstating_someone_who_was_never_suspended_is_refused(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    _, membership_id = await add_member(client, admin, org_id)

    response = await client.post(
        f"/api/v1/orgs/{org_id}/members/{membership_id}/reinstate", headers=admin.headers
    )

    assert response.status_code == 409


async def test_a_removed_person_is_reinstated_rather_than_re_invited(client):
    """The suspended row still occupies the (user, organization) pair."""
    admin = await register(client)
    org_id = await create_team(client, admin)
    member, membership_id = await add_member(client, admin, org_id)
    await client.delete(f"/api/v1/orgs/{org_id}/members/{membership_id}", headers=admin.headers)

    response = await invite(client, admin, org_id, member)

    assert response.status_code == 409
    assert "reinstate" in response.json()["detail"]


# -- the audit trail ----------------------------------------------------------


async def test_membership_changes_are_audited(client, session):
    admin = await register(client)
    org_id = await create_team(client, admin)
    _, membership_id = await add_member(client, admin, org_id)
    await client.delete(f"/api/v1/orgs/{org_id}/members/{membership_id}", headers=admin.headers)

    rows = (
        (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.organization_id == org_id)
                .order_by(AuditLog.created_at)
            )
        )
        .scalars()
        .all()
    )

    actions = [row.action for row in rows]
    assert actions == [
        "organization.created",
        "membership.invited",
        "membership.accepted",
        "membership.removed",
    ]
    assert all(row.via_super_admin is False for row in rows)
    assert all(row.reason for row in rows)


async def test_listing_members_shows_every_status(client):
    admin = await register(client)
    org_id = await create_team(client, admin)
    await add_member(client, admin, org_id)
    pending = await register(client)
    await invite(client, admin, org_id, pending)

    everyone = await client.get(f"/api/v1/orgs/{org_id}/members", headers=admin.headers)
    only_pending = await client.get(
        f"/api/v1/orgs/{org_id}/members?status=pending", headers=admin.headers
    )

    assert everyone.json()["count"] == 3
    assert only_pending.json()["count"] == 1
    assert only_pending.json()["items"][0]["user_id"] == str(pending.user_id)
