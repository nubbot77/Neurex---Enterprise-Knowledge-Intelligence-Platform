"""Request and response shapes for membership routes — Phase 5.

Fields are listed explicitly rather than dumped from the ORM object, so a column added
to ``memberships`` later cannot start appearing in responses by accident.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.models.membership import AccountType, MembershipRole, MembershipStatus
from api.models.organization import OrganizationKind


class InviteRequest(BaseModel):
    """Invite an existing account into this organization.

    ``role`` defaults to ``member``. Defaulting to admin would put the ceiling check on
    the least attentive path through the API.
    """

    email: EmailStr
    role: MembershipRole = MembershipRole.MEMBER
    account_type: AccountType = AccountType.MEMBER


class RoleUpdateRequest(BaseModel):
    role: MembershipRole


class MembershipResponse(BaseModel):
    """One membership, as its own organization sees it.

    ``account_type`` is returned because it is billing information the organization
    owns. It is not an authorization input anywhere in the system (§7.5) — a client
    that treats it as one is reading it wrong.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: MembershipRole
    account_type: AccountType
    status: MembershipStatus
    invited_by_id: uuid.UUID | None
    joined_at: datetime | None
    created_at: datetime


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]
    count: int = Field(description="Number of memberships in this page")


class OrganizationSummary(BaseModel):
    """An organization as it appears in the caller's own list of memberships."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    kind: OrganizationKind


class MyMembershipResponse(BaseModel):
    """The caller's standing in one organization, for ``/me/organizations``.

    Pending rows are included: an invitation the user has not accepted is the one
    thing they need to see in order to act on it, and it grants nothing until they do.
    """

    organization: OrganizationSummary
    membership_id: uuid.UUID
    role: MembershipRole
    status: MembershipStatus
    joined_at: datetime | None
