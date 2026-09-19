"""Organization-level operations — Phase 5.

Small on purpose: read, rename, adjust the admin ceiling, deactivate. Membership
changes live in ``MembershipService``; these are the operations on the tenant itself.
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.context import OrgContext
from api.auth.exceptions import AdminRangeViolation, OrganizationNotFound
from api.db.repositories.memberships import MembershipRepository
from api.db.repositories.organizations import OrganizationRepository
from api.models.audit import AuditLog
from api.models.membership import (
    AccountType,
    Membership,
    MembershipRole,
    MembershipStatus,
)
from api.models.organization import Organization, OrganizationKind
from api.models.user import User

logger = structlog.get_logger(__name__)

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def _slug_for(name: str) -> str:
    """A unique, readable slug. The random suffix is what makes it unique.

    ``organizations.slug`` is unique platform-wide, and two customers called "Acme"
    is the normal case rather than the exotic one.
    """
    stem = _SLUG_STRIP.sub("-", name.lower()).strip("-")[:32] or "workspace"
    return f"{stem}-{secrets.token_hex(4)}"


class OrganizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.organizations = OrganizationRepository(session)
        self.memberships = MembershipRepository(session)

    async def create(self, *, owner: User, name: str) -> Organization:
        """Create a team organization with its creator as the first admin.

        Two rows in one transaction, for the same reason registration writes three
        (§7.3): an organization with no admin is one the admin range immediately
        forbids, and one nobody could ever manage.

        This route is not organization-scoped — there is no organization yet to scope
        it to — so it lives beside ``/me`` rather than under
        ``/orgs/{organization_id}/``, and authentication is the only requirement.
        """
        organization = Organization(
            name=name.strip(),
            slug=_slug_for(name),
            kind=OrganizationKind.TEAM,
        )
        self.session.add(organization)
        await self.session.flush()

        self.session.add(
            Membership(
                user_id=owner.id,
                organization_id=organization.id,
                role=MembershipRole.ADMIN,
                account_type=AccountType.MEMBER,
                # Explicit, not the column default: ``pending`` is for invitations,
                # and the admin-count trigger only counts active admins — a pending
                # creator would leave the organization at zero.
                status=MembershipStatus.ACTIVE,
                joined_at=datetime.now(UTC),
            )
        )
        self.session.add(
            AuditLog(
                actor_user_id=owner.id,
                organization_id=organization.id,
                action="organization.created",
                resource_type="organizations",
                resource_id=str(organization.id),
                reason="team organization created",
            )
        )
        await self.session.commit()

        # The admin-count trigger updates ``organizations`` after this object was
        # loaded, so the in-memory copy still says zero admins. Without the refresh the
        # create response reports ``active_admin_count: 0`` for an organization that
        # has one — verified against a live server before this line existed.
        await self.session.refresh(organization)

        logger.info(
            "organization.created",
            organization_id=str(organization.id),
            user_id=str(owner.id),
        )
        return organization

    async def get(self, ctx: OrgContext) -> Organization:
        """The caller's organization.

        No permission logic here: holding an ``OrgContext`` for this tenant already
        means an active membership was resolved for it (§7.8), and the route's
        ``require(ORG_READ)`` decided the rest.
        """
        organization = await self.organizations.get_active(ctx.organization_id)
        if organization is None:
            raise OrganizationNotFound(reason="organization_inactive")
        return organization

    async def update(
        self,
        ctx: OrgContext,
        *,
        name: str | None = None,
        max_admins: int | None = None,
    ) -> Organization:
        """Rename the organization, or move its admin ceiling.

        ``max_admins`` is a column rather than a constant so a plan change is an
        UPDATE instead of a migration plus a release (§7.7). Lowering it below the
        admins currently serving is checked here so the caller gets a 409 naming the
        number, rather than the CHECK constraint's 500.
        """
        organization = await self.get(ctx)

        if max_admins is not None and max_admins < organization.active_admin_count:
            raise AdminRangeViolation(
                f"This organization has {organization.active_admin_count} active admins; "
                f"demote one before lowering the limit to {max_admins}.",
                reason="ceiling_below_current",
            )

        changes: list[str] = []
        if name is not None and name != organization.name:
            organization.name = name
            changes.append("name")
        if max_admins is not None and max_admins != organization.max_admins:
            organization.max_admins = max_admins
            changes.append("max_admins")

        if not changes:
            return organization

        self.session.add(
            AuditLog(
                actor_user_id=ctx.user_id,
                organization_id=ctx.organization_id,
                action="organization.updated",
                resource_type="organizations",
                resource_id=str(organization.id),
                reason=f"changed {', '.join(changes)}",
            )
        )

        try:
            await self.session.commit()
        except DBAPIError:
            await self.session.rollback()
            raise

        logger.info("organization.updated", changed=changes, **ctx.log_fields())
        return organization

    async def deactivate(self, ctx: OrgContext) -> None:
        """Switch the organization off.

        Deactivation, not deletion. Documents, conversations and audit rows all point
        at this row; removing it would orphan them, and the audit trail is exactly what
        someone will want *after* a tenant is shut down.

        An inactive organization stops resolving a context at all (§7.8), so this locks
        every organization-scoped route for every member, including the admin who ran
        it. Members already holding a cached membership keep it until the entry expires
        — at most ``membership_cache_ttl_seconds``.
        """
        organization = await self.get(ctx)
        organization.is_active = False

        self.session.add(
            AuditLog(
                actor_user_id=ctx.user_id,
                organization_id=ctx.organization_id,
                action="organization.deactivated",
                resource_type="organizations",
                resource_id=str(organization.id),
                reason="organization deactivated",
            )
        )
        await self.session.commit()
        logger.warning("organization.deactivated", **ctx.log_fields())
