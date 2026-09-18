from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.membership import Membership


class OrganizationKind(StrEnum):
    """Solo users get a PERSONAL organization at signup.

    This is what lets ``organization_id`` be NOT NULL on every tenant-scoped table
    with no nullable-owner branch — architecture §7.3.
    """

    PERSONAL = "personal"
    TEAM = "team"


class Organization(Base, TimestampMixin):
    """A tenant: a company, a team, or one person's private workspace."""

    __tablename__ = "organizations"

    __table_args__ = (
        CheckConstraint(
            "max_admins >= 1",
            name="ck_organizations_max_admins_min",
        ),
        # Ceiling only. The floor (an active organization must keep at least one
        # admin) is enforced by the Phase 3 Task 6 trigger, not here: an
        # organization row is inserted before its first admin membership exists,
        # so a table-level "count >= 1" is unsatisfiable at creation time, and
        # PostgreSQL does not support DEFERRABLE CHECK constraints.
        CheckConstraint(
            "active_admin_count >= 0 AND active_admin_count <= max_admins",
            name="ck_organizations_active_admin_count_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    kind: Mapped[OrganizationKind] = mapped_column(
        Enum(
            OrganizationKind,
            native_enum=False,
            create_constraint=True,
            # Store the lowercase .value, not the enum .name — the CHECK constraint
            # is generated from whatever is stored, and server_default uses .value.
            values_callable=lambda e: [m.value for m in e],
            length=20,
            name="organization_kind",
        ),
        nullable=False,
        default=OrganizationKind.TEAM,
        server_default=OrganizationKind.TEAM.value,
    )

    # A column, not a literal, so a plan change is an UPDATE rather than a
    # migration plus a release — architecture §7.7.
    max_admins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default=text("2"),
    )

    # Maintained solely by the trigger on memberships. Starts at 0 because the
    # organization row is written before its first admin membership.
    active_admin_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    memberships: Mapped[list[Membership]] = relationship(
        "Membership",
        back_populates="organization",
        foreign_keys="Membership.organization_id",
        cascade="all, delete-orphan",
    )
