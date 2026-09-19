"""Model registry.

Importing this package is what puts every model into ``Base.metadata``. Alembic reads
that registry and never scans directories, so a model whose module is never imported is
invisible to autogenerate and silently produces an empty migration.
"""

from api.models.audit import AuditLog
from api.models.membership import (
    AccountType,
    Membership,
    MembershipRole,
    MembershipStatus,
)
from api.models.organization import Organization, OrganizationKind
from api.models.user import User

__all__ = [
    "AccountType",
    "AuditLog",
    "Membership",
    "MembershipRole",
    "MembershipStatus",
    "Organization",
    "OrganizationKind",
    "User",
]
