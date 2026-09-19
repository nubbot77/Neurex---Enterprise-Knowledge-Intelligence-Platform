"""The audit trail — Phase 5, Task 9.

Architecture §7.10 requires that every cross-tenant access by a platform operator is
recorded: who, which organization, which resource, when, and the stated reason. An
unaudited bypass cannot answer "did anyone read this customer's data?", which is the
question that actually gets asked, usually by someone who is not in a mood to hear
"we don't log that".

The table is written by the bypass path and by the membership service. It is not
organization-scoped in the repository sense — a cross-tenant read has a *target*
organization, and the row has to survive being read by a platform operator who holds no
membership anywhere.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.base import Base


class AuditLog(Base):
    """One recorded action. Append-only by convention: nothing updates these rows.

    No ``TimestampMixin`` here, deliberately. That mixin carries ``updated_at``, and a
    column implying an audit row can be edited is the wrong thing to put on an audit
    row.
    """

    __tablename__ = "audit_log"

    __table_args__ = (
        # "What did this operator touch?" and "who touched this tenant?" are the two
        # questions an incident actually asks, in that order.
        Index("ix_audit_log_actor_created", "actor_user_id", "created_at"),
        Index("ix_audit_log_org_created", "organization_id", "created_at"),
        # Answers "did anyone read across tenants?" without scanning the whole table.
        Index(
            "ix_audit_log_cross_tenant",
            "created_at",
            postgresql_where=text("via_super_admin"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # SET NULL, not CASCADE: deleting an operator's account must not erase the record
    # of what they did. The action outlives the actor.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # The organization the action was aimed at. No foreign key: an organization can be
    # deleted, and the audit row for its deletion has to outlive it.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)

    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Required for a bypass — §7.10 asks for the stated reason, and a nullable column
    # is one a caller forgets to fill. Ordinary operations record what happened.
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    via_super_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
