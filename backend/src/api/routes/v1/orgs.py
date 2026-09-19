"""Organization-scoped routes — Phase 5, Task 10.

Architecture §7.8. Everything an organization owns lives under

    /api/v1/orgs/{organization_id}/...

so the tenant is visible in the route, in access logs, in traces and in tests. A header
or a JWT claim would hide it, and an ambient tenant that appears nowhere in the request
is hard to audit after an incident — which is the moment someone has to reconstruct who
touched what.

Two dependencies do the work before any handler runs:

``DefaultDeny``
    attached to the router itself, so every route underneath — including ones added in
    later phases — must declare a permission or be refused.

``require(Permission...)``
    the declaration, which also hands the handler the ``OrgContext`` it resolved.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.auth.context import OrgContext
from api.auth.dependencies import CurrentUser, MembershipServiceDep, OrganizationServiceDep
from api.auth.permissions import Permission
from api.auth.rbac import DefaultDeny, require
from api.schemas.memberships import MembershipResponse
from api.schemas.organizations import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)

# Creation has no organization to be scoped to, so it sits outside the scoped router
# and outside default deny. Authentication is the only requirement: every user may
# start a team, exactly as every user already owns a personal one (§7.3).
creation_router = APIRouter(prefix="/orgs", tags=["organizations"])

router = APIRouter(
    prefix="/orgs/{organization_id}",
    tags=["organizations"],
    dependencies=[DefaultDeny],
)


@creation_router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    user: CurrentUser,
    service: OrganizationServiceDep,
) -> OrganizationResponse:
    """Create a team organization; the caller becomes its first admin.

    Without this, a team organization could not exist at all — registration only ever
    creates a personal one, and a personal workspace cannot take members (§7.3). So
    every route below, and every invitation, depends on it.
    """
    organization = await service.create(owner=user, name=payload.name)
    return OrganizationResponse.model_validate(organization)


@router.get("")
async def read_organization(
    ctx: Annotated[OrgContext, Depends(require(Permission.ORG_READ))],
    service: OrganizationServiceDep,
) -> OrganizationResponse:
    """The organization the caller is a member of.

    A caller with no active membership never reaches this handler: context resolution
    answered 404 first, exactly as it would for an organization that does not exist.
    """
    return OrganizationResponse.model_validate(await service.get(ctx))


@router.patch("")
async def update_organization(
    payload: OrganizationUpdateRequest,
    ctx: Annotated[OrgContext, Depends(require(Permission.ORG_UPDATE))],
    service: OrganizationServiceDep,
) -> OrganizationResponse:
    """Rename the organization or move its admin ceiling. Admins only."""
    organization = await service.update(
        ctx,
        name=payload.name,
        max_admins=payload.max_admins,
    )
    return OrganizationResponse.model_validate(organization)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_organization(
    ctx: Annotated[OrgContext, Depends(require(Permission.ORG_DELETE))],
    service: OrganizationServiceDep,
) -> None:
    """Switch the organization off.

    Deactivation rather than deletion: documents, conversations and audit rows point at
    this tenant, and the audit trail is the thing most likely to be wanted after it is
    shut down. Every organization-scoped route stops resolving immediately afterwards,
    for the caller too.
    """
    await service.deactivate(ctx)


@router.post("/leave", status_code=status.HTTP_200_OK)
async def leave_organization(
    ctx: Annotated[OrgContext, Depends(require(Permission.ORG_READ))],
    service: MembershipServiceDep,
) -> MembershipResponse:
    """The caller removes their own membership.

    Declares ``org:read`` because leaving needs no authority over anyone else — every
    active member holds it. What stops the last admin walking out is the admin range
    (§7.7), not a permission: the floor applies to a voluntary departure exactly as it
    applies to being removed.
    """
    return MembershipResponse.model_validate(await service.leave(ctx))
