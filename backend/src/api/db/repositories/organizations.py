"""Queries against ``organizations`` — Phase 5, Task 7.

Not organization-scoped, and this is the one table where that needs saying out loud:
the organization *is* the tenant boundary, so a filter on ``organization_id`` has
nothing to filter. Access to a row here is decided one step earlier, by whether the
caller holds an active membership in it (§7.8).
"""

from __future__ import annotations

from uuid import UUID

from api.db.repositories.base import BaseRepository
from api.models.organization import Organization


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_slug(self, slug: str) -> Organization | None:
        return await self.get_by(slug=slug)

    async def get_active(self, organization_id: UUID) -> Organization | None:
        """The organization, if it is still active.

        A deactivated tenant answers like a missing one. Callers turn both into the
        same 404, because "exists but is switched off" is still more than someone
        outside it should learn.
        """
        organization = await self.get(organization_id)
        if organization is None or not organization.is_active:
            return None
        return organization
