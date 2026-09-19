"""Queries against ``memberships`` — Phase 5, Tasks 1, 4 and 7.

Two repositories, because there are two genuinely different situations:

``MembershipRepository``
    Used **before** an organization context exists. It is what resolves one. It cannot
    inherit the mandatory tenant filter, because the filter's value is the thing it is
    being asked to establish — so every method here takes ``organization_id`` as an
    explicit argument and filters on it.

``OrgMembershipRepository``
    Used **after** a context exists, for listing and managing members. It inherits the
    mandatory filter like every other tenant-scoped table.

The split is deliberate. Folding both into one class would mean a single method that is
sometimes scoped and sometimes not, decided by a flag — and a flag is exactly what
nobody checks at the call site.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from api.db.repositories.base import BaseRepository
from api.db.repositories.org_scoped import OrgScopedRepository
from api.models.membership import Membership, MembershipRole, MembershipStatus
from api.models.organization import Organization


class MembershipRepository(BaseRepository[Membership]):
    """Context resolution. Unscoped by necessity, never by convenience."""

    model = Membership

    async def get_for_user_in_org(self, user_id: UUID, organization_id: UUID) -> Membership | None:
        """The membership joining this user to this organization, whatever its status.

        Both columns are always supplied, and the unique constraint on the pair means
        at most one row can come back. Status is *not* filtered here: the caller needs
        to tell "no membership" from "suspended membership" for logging, even though
        both resolve to the same 404 (§7.8).
        """
        result = await self.session.execute(
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.organization_id == organization_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, *, status: MembershipStatus | None = None
    ) -> Sequence[Membership]:
        """Every organization this user belongs to — the ``/me/organizations`` query."""
        stmt = (
            select(Membership)
            .where(Membership.user_id == user_id)
            # Eager, not lazy: a lazy load of ``organization`` inside an async session
            # raises MissingGreenlet at attribute access, which surfaces in the route
            # rather than here.
            .options(selectinload(Membership.organization))
        )
        if status is not None:
            stmt = stmt.where(Membership.status == status)
        result = await self.session.execute(stmt.order_by(Membership.created_at))
        return result.scalars().all()

    async def count_active_admins(self, organization_id: UUID) -> int:
        """Active admins in one organization.

        Advisory only. This is the service-layer half of the admin range (§7.7): it
        exists so the caller sees a 409 with a usable message instead of a constraint
        violation surfaced as a 500. Two concurrent requests can both pass it; the
        trigger's row lock is what actually decides.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.organization_id == organization_id,
                Membership.role == MembershipRole.ADMIN,
                Membership.status == MembershipStatus.ACTIVE,
            )
        )
        return result.scalar_one()

    async def get_with_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> tuple[Membership, Organization] | None:
        """The membership and its organization in one round-trip.

        Context resolution needs both — the membership for the role, the organization
        to confirm the tenant is still active — and this sits on the critical path of
        every organization-scoped request, so it is one query rather than two.
        """
        result = await self.session.execute(
            select(Membership, Organization)
            .join(Organization, Organization.id == Membership.organization_id)
            .where(
                Membership.user_id == user_id,
                Membership.organization_id == organization_id,
            )
            .limit(1)
        )
        row = result.first()
        return (row[0], row[1]) if row is not None else None


class OrgMembershipRepository(OrgScopedRepository[Membership]):
    """Member management inside a resolved organization.

    Every query inherits ``WHERE organization_id = :ctx.organization_id``, so a
    membership id belonging to another tenant reads as absent — which is what makes
    "guess a membership id" a dead end rather than a disclosure.
    """

    model = Membership

    async def list_members(
        self,
        *,
        status: MembershipStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Membership]:
        filters: dict[str, object] = {}
        if status is not None:
            filters["status"] = status
        return await self.list(
            limit=limit,
            offset=offset,
            order_by=Membership.created_at,
            **filters,
        )

    async def get_for_user(self, user_id: UUID) -> Membership | None:
        """This organization's membership for a given user, if any."""
        return await self.get_by(user_id=user_id)
