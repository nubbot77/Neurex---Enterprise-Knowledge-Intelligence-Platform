"""The caller's own identity, across organizations.

``/me`` is the second of the three route scopes in architecture §5: authenticated, but
with no organization context. Two kinds of route belong here and nowhere else:

* things about the person rather than a tenant (``GET /me``);
* things a **pending** member has to be able to do. A pending membership resolves to no
  context at all, so an invitation could never be accepted from under
  ``/orgs/{organization_id}/`` — the route would 404 the very person it is for.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from api.auth.dependencies import CurrentUser, MembershipServiceDep
from api.db.repositories.memberships import MembershipRepository
from api.db.session import SessionDep
from api.schemas.auth import UserResponse
from api.schemas.memberships import (
    MembershipResponse,
    MyMembershipResponse,
    OrganizationSummary,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("")
async def read_me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.get("/organizations")
async def list_my_organizations(
    user: CurrentUser,
    session: SessionDep,
) -> list[MyMembershipResponse]:
    """Every organization the caller belongs to, with their standing in each.

    Pending invitations are included. They grant nothing — a pending membership
    resolves to no permissions anywhere — but they are the one thing the user needs to
    see in order to accept them.

    No organization filter is possible here, and none is needed: the query is keyed by
    ``user_id``, so it returns exactly the tenants this caller has a row in.
    """
    memberships = await MembershipRepository(session).list_for_user(user.id)
    return [
        MyMembershipResponse(
            organization=OrganizationSummary.model_validate(m.organization),
            membership_id=m.id,
            role=m.role,
            status=m.status,
            joined_at=m.joined_at,
        )
        for m in memberships
    ]


@router.post("/invitations/{organization_id}/accept")
async def accept_invitation(
    organization_id: uuid.UUID,
    user: CurrentUser,
    service: MembershipServiceDep,
) -> MembershipResponse:
    """Accept an invitation to an organization.

    Answers 404 when there is no pending invitation for this caller — the same answer
    as for an organization that does not exist, because anything else would let
    someone probe which tenants are real (§7.8).
    """
    membership = await service.accept_invitation(
        user_id=user.id,
        organization_id=organization_id,
    )
    return MembershipResponse.model_validate(membership)
