"""The organization context — Phase 5, Task 3.

Architecture §7.8. One object carrying everything an authorization decision needs:
who is asking, which tenant they are asking about, what they are in it, and what that
lets them do.

Built once, at the entrance, by ``api.auth.dependencies.get_org_context``. Nothing
below the route re-derives authority from the user and the path — two call sites that
each work it out separately are two chances to disagree, and the disagreement shows up
as a leak rather than as a crash.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from api.auth.permissions import (
    Permission,
    permissions_for,
    requires_ownership_check,
)
from api.models.membership import AccountType, Membership, MembershipRole


@dataclass(frozen=True, slots=True)
class OrgContext:
    """A resolved, in-force membership plus the permissions it carries.

    Frozen: a handler that could widen its own context would make every check upstream
    advisory. ``permissions`` is a ``frozenset`` for the same reason.

    ``account_type`` is carried for logging and billing only. It is **never** consulted
    in an authorization decision (§7.5, invariant 5) — two attributes that both read as
    "what kind of user is this" drift into two overlapping permission systems, and
    every later bug starts with "which of the two was supposed to win?".
    """

    user_id: UUID
    organization_id: UUID
    membership_id: UUID
    role: MembershipRole
    account_type: AccountType
    permissions: frozenset[Permission]
    is_super_admin: bool

    @classmethod
    def from_membership(cls, membership: Membership, *, is_super_admin: bool) -> OrgContext:
        """Build the context from an **active** membership row.

        The status check is not repeated here. It belongs to resolution (§7.8), which
        rejects anything that is not active before this is ever called; re-checking in
        the constructor would suggest a non-active membership is a thing this object
        can legitimately hold.
        """
        return cls(
            user_id=membership.user_id,
            organization_id=membership.organization_id,
            membership_id=membership.id,
            role=membership.role,
            account_type=membership.account_type,
            permissions=permissions_for(membership.role),
            is_super_admin=is_super_admin,
        )

    # -- queries -----------------------------------------------------------

    def has(self, permission: Permission) -> bool:
        """Whether the role holds this permission.

        ``is_super_admin`` grants nothing here. A platform operator has no membership
        and therefore no organization role; their reach is the explicit, audited,
        read-only bypass in §7.10, not a silent ``or is_super_admin`` in the middle of
        every check — which would be unauditable precisely because it is invisible.
        """
        return permission in self.permissions

    def owns_or_has_full(self, permission: Permission, *, created_by: UUID | None) -> bool:
        """Resource-level check for the "own only" entries in the §7.6 matrix.

        Call it *after* the route's ``require(permission)`` has passed. For a role the
        permission is unrestricted for, it is ``True``; for a role it is ownership
        scoped for, the row must have been created by this user.

        ``created_by is None`` fails closed: an unattributed row cannot be shown to
        someone who may only see their own.
        """
        if not self.has(permission):
            return False
        if not requires_ownership_check(self.role, permission):
            return True
        return created_by is not None and created_by == self.user_id

    def log_fields(self) -> dict[str, str]:
        """Identifiers for structured logs. No permission dump, no email."""
        return {
            "user_id": str(self.user_id),
            "organization_id": str(self.organization_id),
            "role": self.role.value,
        }
