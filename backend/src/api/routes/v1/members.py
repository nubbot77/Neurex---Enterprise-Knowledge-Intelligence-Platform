"""Member management — Phase 5, Tasks 1 and 10.

Mounted under ``/api/v1/orgs/{organization_id}/members``. Every route declares the
permission it needs; the router's ``DefaultDeny`` refuses anything that forgets.

Accepting an invitation is deliberately **not** here. A pending membership resolves to
no context at all, so a route under this prefix could never be reached by the person
who was invited — acceptance lives under ``/me``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from api.auth.context import OrgContext
from api.auth.dependencies import MembershipServiceDep
from api.auth.permissions import Permission
from api.auth.rbac import DefaultDeny, require
from api.models.membership import MembershipStatus
from api.schemas.memberships import (
    InviteRequest,
    MembershipListResponse,
    MembershipResponse,
    RoleUpdateRequest,
)

router = APIRouter(
    prefix="/orgs/{organization_id}/members",
    tags=["members"],
    dependencies=[DefaultDeny],
)


@router.get("")
async def list_members(
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_READ))],
    service: MembershipServiceDep,
    status_filter: Annotated[MembershipStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MembershipListResponse:
    """Members of this organization. Both roles may read the roster."""
    members = await service.list_members(ctx, status=status_filter, limit=limit, offset=offset)
    items = [MembershipResponse.model_validate(m) for m in members]
    return MembershipListResponse(items=items, count=len(items))


@router.post("", status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InviteRequest,
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_INVITE))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """Invite an existing account. The row is created ``pending`` and grants nothing."""
    membership = await service.invite(
        ctx,
        email=payload.email,
        role=payload.role,
        account_type=payload.account_type,
    )
    return MembershipResponse.model_validate(membership)


@router.get("/{membership_id}")
async def read_member(
    membership_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_READ))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """One membership.

    The lookup is scoped, so an id from another organization answers 404 — identical
    to an id that does not exist anywhere.
    """
    return MembershipResponse.model_validate(await service.get_membership(ctx, membership_id))


@router.patch("/{membership_id}/role")
async def change_member_role(
    membership_id: uuid.UUID,
    payload: RoleUpdateRequest,
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_UPDATE_ROLE))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """Promote or demote a member.

    Both directions are range-checked: promotion can hit the ceiling, and demoting the
    last admin would leave the organization unmanageable (409 either way).
    """
    membership = await service.change_role(ctx, membership_id=membership_id, role=payload.role)
    return MembershipResponse.model_validate(membership)


@router.post("/{membership_id}/suspend")
async def suspend_member(
    membership_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_REMOVE))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """Put a membership on hold. It grants nothing until reinstated."""
    return MembershipResponse.model_validate(
        await service.suspend(ctx, membership_id=membership_id)
    )


@router.post("/{membership_id}/reinstate")
async def reinstate_member(
    membership_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_INVITE))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """Bring a suspended membership back.

    Declares ``member:invite`` rather than ``member:update_role``: this is bringing
    someone into the organization, which is the same authority as inviting them, and
    it is range-checked when the membership is an admin's.
    """
    return MembershipResponse.model_validate(
        await service.reinstate(ctx, membership_id=membership_id)
    )


@router.delete("/{membership_id}")
async def remove_member(
    membership_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.MEMBER_REMOVE))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """Remove someone from the organization.

    Returns the membership rather than 204, because the row still exists: removal is a
    status transition to ``suspended``, kept because audit records point at it (§7.4).
    Answering "no content" would suggest something was deleted.
    """
    return MembershipResponse.model_validate(await service.remove(ctx, membership_id=membership_id))
