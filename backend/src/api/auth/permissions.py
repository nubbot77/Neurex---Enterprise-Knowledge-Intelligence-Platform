"""The permission catalogue and the role matrix — Phase 5, Task 2.

Architecture §7.6. Every action the system can perform is named here as
``resource:action``, and every role's set is spelled out in one table.

**The matrix is a constant in code, not rows in a table.** With two organization roles,
a ``roles`` / ``permissions`` / ``role_permissions`` schema would add a join to every
request and buy nothing a dictionary does not, while hiding the permission set from
code review and from type checking.

The trigger for revisiting that is recorded so the decision gets made rather than
argued: **the first customer who needs a role the platform does not define.** Then the
matrix moves into the database as organization-scoped custom roles and these two become
seeded rows. Until then it stays here.
"""

from __future__ import annotations

from enum import StrEnum

from api.models.membership import MembershipRole


class Permission(StrEnum):
    """One value per action the API can perform inside an organization.

    ``super_admin`` appears nowhere in this enum. It is not an organization role and
    holds no permissions here; its cross-tenant reach is the explicit, audited,
    read-only bypass in ``api.db.repositories.org_scoped`` (§7.10).
    """

    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"

    MEMBER_INVITE = "member:invite"
    MEMBER_READ = "member:read"
    MEMBER_UPDATE_ROLE = "member:update_role"
    MEMBER_REMOVE = "member:remove"

    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_REPROCESS = "document:reprocess"

    CONVERSATION_CREATE = "conversation:create"
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_DELETE = "conversation:delete"

    SEARCH_EXECUTE = "search:execute"

    EVALUATION_CREATE = "evaluation:create"
    EVALUATION_READ = "evaluation:read"
    EVALUATION_RUN = "evaluation:run"

    APIKEY_CREATE = "apikey:create"
    APIKEY_READ = "apikey:read"
    APIKEY_REVOKE = "apikey:revoke"

    AUDIT_READ = "audit:read"


# An admin holds everything an organization can do. Written as "all of them" rather
# than a hand-copied list so a permission added above cannot be silently withheld from
# the only role that manages the tenant.
_ADMIN: frozenset[Permission] = frozenset(Permission)

_MEMBER: frozenset[Permission] = frozenset(
    {
        Permission.ORG_READ,
        Permission.MEMBER_READ,
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_REPROCESS,
        Permission.CONVERSATION_CREATE,
        # Granted, but narrowed to rows the member created — see OWNERSHIP_SCOPED.
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_DELETE,
        Permission.SEARCH_EXECUTE,
        Permission.EVALUATION_READ,
    }
)

ROLE_PERMISSIONS: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.ADMIN: _ADMIN,
    MembershipRole.MEMBER: _MEMBER,
}

# "own only" in the §7.6 matrix is a *resource-level* rule, not a role-level one. The
# permission is granted to the member; the service then additionally checks
# ``resource.created_by == ctx.user_id``.
#
# It is deliberately not expressed by withholding the permission. Role checks and
# ownership checks answer different questions — "may this role do this at all?" and
# "is this particular row theirs?" — and collapsing them into one loses the second:
# a route would pass the role check for its own rows and 403 for everything else, with
# nowhere left to distinguish "not yours" from "not allowed".
OWNERSHIP_SCOPED: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.ADMIN: frozenset(),
    MembershipRole.MEMBER: frozenset(
        {
            Permission.CONVERSATION_READ,
            Permission.CONVERSATION_DELETE,
        }
    ),
}


def permissions_for(role: MembershipRole) -> frozenset[Permission]:
    """The permission set a role holds.

    An unknown role resolves to the empty set rather than raising. The default in this
    system is deny, and a role added to the enum without a matrix entry must lock its
    holders out, not crash the request path for everyone — or, worse, be papered over
    with a permissive fallback at some call site.
    """
    return ROLE_PERMISSIONS.get(role, frozenset())


def requires_ownership_check(role: MembershipRole, permission: Permission) -> bool:
    """True when holding ``permission`` is not enough and the row must also be theirs."""
    return permission in OWNERSHIP_SCOPED.get(role, frozenset())
