"""Request and response shapes for organization routes — Phase 5."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.models.organization import OrganizationKind


class OrganizationCreateRequest(BaseModel):
    """``kind`` is not a field: this route only ever makes a team.

    A personal organization is created by registration, one per user, and a second one
    would have no owner rule to follow.
    """

    name: str = Field(min_length=1, max_length=255)


class OrganizationResponse(BaseModel):
    """What a member may see about their own organization.

    ``active_admin_count`` and ``max_admins`` are both returned: a client that has to
    explain "you cannot demote this person" needs the range it is being measured
    against, and neither number is sensitive to the people already inside the tenant.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    kind: OrganizationKind
    max_admins: int
    active_admin_count: int
    is_active: bool
    created_at: datetime


class OrganizationUpdateRequest(BaseModel):
    """Both fields optional; omitted ones are left alone.

    ``max_admins`` has a floor of 1 here as well as in the database. Lowering it below
    the number of admins currently serving is refused with a 409 rather than left to
    the CHECK constraint, which would arrive as a 500.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    max_admins: int | None = Field(default=None, ge=1, le=50)
