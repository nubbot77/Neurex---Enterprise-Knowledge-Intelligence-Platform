"""Membership lifecycle — Phase 5, Tasks 1 and 8.

Invite, accept, change role, suspend, remove, reinstate and leave. Architecture §7.4
and §7.7.

Three things every write in this file does, in this order:

1. **Check the admin range first**, so the caller gets a 409 with a usable message.
   That check is a courtesy, not the guarantee — see ``_guard_admin_range``.
2. **Write, and translate the database's verdict.** The trigger and the CHECK on
   ``organizations`` are authoritative; a violation that slips past step 1 comes back
   as the same 409 rather than a 500.
3. **Invalidate the membership cache.** The resolved membership lives in Redis under
   ``membership:{user_id}:{organization_id}``; deleting that key in the same call that
   writes the row is what makes a demotion or a suspension apply on the next request
   (invariant 7) instead of at the next token expiry.

Removal is a status transition, never a row delete: audit rows reference the
membership, and deleting it orphans that history (§7.4).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.context import OrgContext
from api.auth.exceptions import (
    AdminRangeViolation,
    MembershipConflict,
    MembershipNotFound,
    OrganizationNotFound,
    PersonalOrganizationClosed,
)
from api.auth.membership_cache import MembershipCache
from api.db.repositories.memberships import MembershipRepository, OrgMembershipRepository
from api.db.repositories.organizations import OrganizationRepository
from api.db.repositories.users import UserRepository
from api.models.audit import AuditLog
from api.models.membership import (
    AccountType,
    Membership,
    MembershipRole,
    MembershipStatus,
)
from api.models.organization import Organization, OrganizationKind

logger = structlog.get_logger(__name__)

# Substrings identifying the two halves of the admin range in a database error. The
# ceiling is a named CHECK constraint; the floor is the trigger's own message.
_CEILING_MARKER = "ck_organizations_active_admin_count_range"
_FLOOR_MARKER = "no active admin"


class MembershipService:
    """Everything that changes who belongs to an organization, and as what."""

    def __init__(self, session: AsyncSession, cache: MembershipCache) -> None:
        self.session = session
        self.cache = cache
        self.memberships = MembershipRepository(session)
        self.organizations = OrganizationRepository(session)
        self.users = UserRepository(session)

    # -- reads -------------------------------------------------------------

    async def list_members(
        self,
        ctx: OrgContext,
        *,
        status: MembershipStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Membership]:
        """Members of the caller's organization, and only of it.

        Goes through the scoped repository, so the tenant filter is structural rather
        than written out here — nobody has to remember it at this call site.
        """
        return await OrgMembershipRepository(self.session, ctx).list_members(
            status=status, limit=limit, offset=offset
        )

    async def get_membership(self, ctx: OrgContext, membership_id: UUID) -> Membership:
        """One membership from the caller's organization.

        A membership id from another tenant reads as absent, exactly as an unknown id
        does, so walking ids reveals nothing.
        """
        membership = await OrgMembershipRepository(self.session, ctx).get(membership_id)
        if membership is None:
            raise MembershipNotFound(reason="membership_absent")
        return membership

    # -- invite / accept ---------------------------------------------------

    async def invite(
        self,
        ctx: OrgContext,
        *,
        email: str,
        role: MembershipRole = MembershipRole.MEMBER,
        account_type: AccountType = AccountType.MEMBER,
    ) -> Membership:
        """Invite an existing user into the organization, as ``pending``.

        The invitee must already have an account. Inviting an address that has never
        registered needs an email-delivered invitation token, which belongs with the
        email infrastructure rather than here; until then the endpoint says so plainly
        instead of writing a row nobody can ever accept.

        A ``pending`` row grants nothing (§7.4) — the permission set for a non-active
        membership is empty, and context resolution rejects it before any handler runs.
        """
        organization = await self.organizations.get_active(ctx.organization_id)
        if organization is None:
            raise OrganizationNotFound(reason="organization_inactive")

        if organization.kind is OrganizationKind.PERSONAL:
            # §7.3: a personal workspace exists so that every user owns a tenant from
            # their first second. Letting one take members would give it team
            # semantics without any of a team's checks.
            raise PersonalOrganizationClosed(reason="personal_organization")

        invitee = await self.users.get_by_email(email.strip().lower())
        if invitee is None or not invitee.is_active:
            # Same answer for "no such account" and "disabled account": this endpoint
            # is reachable by any admin, and a distinct reply turns it into an
            # account-existence oracle for the whole platform.
            raise MembershipConflict(
                "No active account exists for that address",
                reason="invitee_unavailable",
            )

        existing = await self.memberships.get_for_user_in_org(invitee.id, ctx.organization_id)
        if existing is not None:
            if existing.status is MembershipStatus.SUSPENDED:
                raise MembershipConflict(
                    "That person was removed from this organization; reinstate them instead",
                    reason="membership_suspended",
                )
            raise MembershipConflict(
                "That person is already a member of this organization",
                reason="membership_exists",
            )

        membership = Membership(
            user_id=invitee.id,
            organization_id=ctx.organization_id,
            role=role,
            account_type=account_type,
            status=MembershipStatus.PENDING,
            invited_by_id=ctx.user_id,
        )
        self.session.add(membership)

        # No admin-range check here even for an admin invitation: the range counts
        # *active* admins, and a pending row is not one. The check happens at accept,
        # which is when the count actually moves.
        await self._commit(
            membership,
            action="membership.invited",
            actor_id=ctx.user_id,
            organization_id=ctx.organization_id,
            reason=f"invited {invitee.id} as {role.value}",
        )
        logger.info(
            "membership.invited",
            membership_id=str(membership.id),
            invitee_id=str(invitee.id),
            # ``invited_role``, not ``role``: ctx.log_fields() already carries the
            # actor's role, and two keys of the same name collide at the call.
            invited_role=role.value,
            **ctx.log_fields(),
        )
        return membership

    async def accept_invitation(self, *, user_id: UUID, organization_id: UUID) -> Membership:
        """Turn the caller's own pending membership into an active one.

        Self-service by definition — an invitation nobody has to accept is just an
        assignment — so this takes a ``user_id`` rather than an ``OrgContext``: the
        invitee has no context to resolve yet, because a pending membership resolves
        to nothing.
        """
        membership = await self.memberships.get_for_user_in_org(user_id, organization_id)

        if membership is None:
            # No invitation and no organization are the same answer, for the reason in
            # §7.8: anything else confirms the tenant exists.
            raise OrganizationNotFound(reason="no_invitation")

        if membership.status is not MembershipStatus.PENDING:
            raise MembershipConflict(
                "That invitation is not pending",
                reason=f"membership_{membership.status.value}",
            )

        if membership.role is MembershipRole.ADMIN:
            await self._guard_admin_range(organization_id, delta=1)

        membership.status = MembershipStatus.ACTIVE
        membership.joined_at = datetime.now(UTC)

        await self._commit(
            membership,
            action="membership.accepted",
            actor_id=user_id,
            organization_id=organization_id,
            reason="invitation accepted",
        )
        logger.info(
            "membership.accepted",
            membership_id=str(membership.id),
            user_id=str(user_id),
            organization_id=str(organization_id),
        )
        return membership

    # -- role changes ------------------------------------------------------

    async def change_role(
        self, ctx: OrgContext, *, membership_id: UUID, role: MembershipRole
    ) -> Membership:
        """Promote or demote a member.

        Both directions can move the active-admin count, so both are range-checked:
        promotion can breach the ceiling, and demoting the last admin would strand the
        organization with nobody who can manage it.
        """
        membership = await self.get_membership(ctx, membership_id)

        if membership.role is role:
            return membership

        if membership.status is MembershipStatus.ACTIVE:
            delta = 1 if role is MembershipRole.ADMIN else -1
            await self._guard_admin_range(ctx.organization_id, delta=delta)

        previous = membership.role
        membership.role = role

        await self._commit(
            membership,
            action="membership.role_changed",
            actor_id=ctx.user_id,
            organization_id=ctx.organization_id,
            reason=f"role {previous.value} -> {role.value}",
        )
        logger.info(
            "membership.role_changed",
            membership_id=str(membership.id),
            subject_user_id=str(membership.user_id),
            previous_role=previous.value,
            new_role=role.value,
            **ctx.log_fields(),
        )
        return membership

    # -- suspend / remove / reinstate --------------------------------------

    async def suspend(self, ctx: OrgContext, *, membership_id: UUID) -> Membership:
        """Put a membership on hold. It grants nothing while suspended (§7.4)."""
        return await self._deactivate(
            ctx, membership_id=membership_id, action="membership.suspended"
        )

    async def remove(self, ctx: OrgContext, *, membership_id: UUID) -> Membership:
        """Remove someone from the organization.

        Same end state as suspension, and deliberately so: the row is retained because
        audit records point at it, and a delete would orphan that history. The two
        operations differ in the audit trail they leave, which is the part anyone will
        actually ask about later.
        """
        return await self._deactivate(ctx, membership_id=membership_id, action="membership.removed")

    async def reinstate(self, ctx: OrgContext, *, membership_id: UUID) -> Membership:
        """Bring a suspended membership back to active.

        Range-checked like any other operation that can add an admin: a suspended
        admin coming back moves the count.
        """
        membership = await self.get_membership(ctx, membership_id)

        if membership.status is not MembershipStatus.SUSPENDED:
            raise MembershipConflict(
                "That membership is not suspended",
                reason=f"membership_{membership.status.value}",
            )

        if membership.role is MembershipRole.ADMIN:
            await self._guard_admin_range(ctx.organization_id, delta=1)

        membership.status = MembershipStatus.ACTIVE
        membership.joined_at = membership.joined_at or datetime.now(UTC)

        await self._commit(
            membership,
            action="membership.reinstated",
            actor_id=ctx.user_id,
            organization_id=ctx.organization_id,
            reason="membership reinstated",
        )
        logger.info(
            "membership.reinstated",
            membership_id=str(membership.id),
            subject_user_id=str(membership.user_id),
            **ctx.log_fields(),
        )
        return membership

    async def leave(self, ctx: OrgContext) -> Membership:
        """The caller removes their own membership.

        Range-checked like every other departure. The last admin of an organization
        cannot leave it: the floor exists precisely so nobody can strand a tenant with
        no one able to manage it, and "I did it to myself" is not an exception the
        rescued organization cares about.
        """
        return await self._deactivate(
            ctx,
            membership_id=ctx.membership_id,
            action="membership.left",
        )

    async def _deactivate(self, ctx: OrgContext, *, membership_id: UUID, action: str) -> Membership:
        membership = await self.get_membership(ctx, membership_id)

        if membership.status is MembershipStatus.SUSPENDED:
            raise MembershipConflict(
                "That membership is already inactive",
                reason="membership_suspended",
            )

        if membership.status is MembershipStatus.ACTIVE and membership.role is MembershipRole.ADMIN:
            await self._guard_admin_range(ctx.organization_id, delta=-1)

        membership.status = MembershipStatus.SUSPENDED

        await self._commit(
            membership,
            action=action,
            actor_id=ctx.user_id,
            organization_id=ctx.organization_id,
            reason=action.split(".", 1)[-1],
        )
        logger.info(
            action,
            membership_id=str(membership.id),
            subject_user_id=str(membership.user_id),
            **ctx.log_fields(),
        )
        return membership

    # -- the admin range, layer 2 — architecture §7.7 ----------------------

    async def _guard_admin_range(self, organization_id: UUID, *, delta: int) -> None:
        """Reject an operation that would leave the organization outside its range.

        **This is layer 2, and layer 2 alone would be a bug.** Two concurrent requests
        can both read the same count here and both proceed; only the row lock the
        trigger takes on ``organizations`` actually serializes them. What this buys is
        the error message: a 409 the caller can act on instead of a constraint
        violation surfaced as a 500.
        """
        organization = await self.organizations.get(organization_id)
        if organization is None:
            raise OrganizationNotFound(reason="organization_absent")

        current = await self.memberships.count_active_admins(organization_id)
        projected = current + delta

        if projected < 1:
            raise AdminRangeViolation(
                "An organization must keep at least one active admin. "
                "Promote another member first.",
                reason="admin_floor",
            )

        if projected > organization.max_admins:
            raise AdminRangeViolation(
                f"This organization allows at most {organization.max_admins} active admins.",
                reason="admin_ceiling",
            )

    # -- commit, translate, invalidate -------------------------------------

    async def _commit(
        self,
        membership: Membership,
        *,
        action: str,
        actor_id: UUID,
        organization_id: UUID,
        reason: str,
    ) -> None:
        """Write the row and its audit record, then drop the cached membership.

        The audit row goes in the same transaction as the change it records: an audit
        trail that can survive a rolled-back write describes something that never
        happened.

        Cache invalidation happens **after** the commit, not before. Clearing first
        leaves a window in which a concurrent request re-reads the old row and caches
        it again, which is the stale entry the deletion was meant to prevent.
        """
        self.session.add(
            AuditLog(
                actor_user_id=actor_id,
                organization_id=organization_id,
                action=action,
                resource_type="memberships",
                resource_id=str(membership.id),
                reason=reason,
            )
        )

        try:
            await self.session.commit()
        except DBAPIError as exc:
            await self.session.rollback()
            raise self._translate(exc) from exc

        await self.cache.invalidate(membership.user_id, membership.organization_id)

    @staticmethod
    def _translate(exc: DBAPIError) -> Exception:
        """Turn the database's verdict on the admin range into a 409.

        The ceiling arrives as a named CHECK violation, the floor as the trigger's own
        exception. Anything else is not ours to reinterpret and is re-raised unchanged:
        swallowing unknown database errors into a tidy 409 is how a real fault gets
        reported as a user mistake.
        """
        message = str(exc.orig) if exc.orig is not None else str(exc)

        if _CEILING_MARKER in message:
            return AdminRangeViolation(
                "This organization already has its maximum number of admins.",
                reason="admin_ceiling_db",
            )
        if _FLOOR_MARKER in message:
            return AdminRangeViolation(
                "An organization must keep at least one active admin.",
                reason="admin_floor_db",
            )
        return exc

    # -- organization-level helpers ----------------------------------------

    async def get_organization(self, ctx: OrgContext) -> Organization:
        """The caller's organization.

        Access was already decided by context resolution — holding an ``OrgContext``
        for this tenant *is* the proof of membership — so this is a plain read.
        """
        organization = await self.organizations.get_active(ctx.organization_id)
        if organization is None:
            raise OrganizationNotFound(reason="organization_inactive")
        return organization
