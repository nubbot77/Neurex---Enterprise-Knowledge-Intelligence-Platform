from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.organization import Organization
    from api.models.user import User


class MembershipRole(StrEnum):
    """What a user may do inside one organization. Never stored on User."""

    ADMIN = "admin"
    MEMBER = "member"


class AccountType(StrEnum):
    """Seat classification for billing.

    Never an authorization input — architecture §7.5. Only ``role`` decides what
    someone may do.
    """

    MEMBER = "member"
    GUEST = "guest"
    SERVICE = "service"


class MembershipStatus(StrEnum):
    """Only ACTIVE grants permissions. PENDING and SUSPENDED resolve to none."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Membership(Base, TimestampMixin):
    """Links a User to an Organization and carries that user's authority within it."""

    __tablename__ = "memberships"

    __table_args__ = (
        # One membership per user per organization. Two rows would make
        # "what is this user's role here?" a question with no correct answer.
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
        # Admin-count and member-listing queries filter by organization first;
        # the unique constraint's index leads with user_id and cannot serve them.
        Index("ix_memberships_org_role_status", "organization_id", "role", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MembershipRole] = mapped_column(
        Enum(
            MembershipRole,
            native_enum=False,
            create_constraint=True,
            # Store the lowercase .value, not the enum .name — the CHECK constraint
            # is generated from whatever is stored, and server_default uses .value.
            values_callable=lambda e: [m.value for m in e],
            length=20,
            name="membership_role",
        ),
        nullable=False,
        default=MembershipRole.MEMBER,
        server_default=MembershipRole.MEMBER.value,
    )

    account_type: Mapped[AccountType] = mapped_column(
        Enum(
            AccountType,
            native_enum=False,
            create_constraint=True,
            # Store the lowercase .value, not the enum .name — the CHECK constraint
            # is generated from whatever is stored, and server_default uses .value.
            values_callable=lambda e: [m.value for m in e],
            length=20,
            name="account_type",
        ),
        nullable=False,
        default=AccountType.MEMBER,
        server_default=AccountType.MEMBER.value,
    )

    status: Mapped[MembershipStatus] = mapped_column(
        Enum(
            MembershipStatus,
            native_enum=False,
            create_constraint=True,
            # Store the lowercase .value, not the enum .name — the CHECK constraint
            # is generated from whatever is stored, and server_default uses .value.
            values_callable=lambda e: [m.value for m in e],
            length=20,
            name="membership_status",
        ),
        nullable=False,
        default=MembershipStatus.PENDING,
        server_default=MembershipStatus.PENDING.value,
    )

    # SET NULL rather than CASCADE: deleting the inviter must not delete the
    # memberships they created.
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Set when status first becomes ACTIVE. Distinct from created_at, which is
    # when the invitation was issued.
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
    )

    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="memberships",
        foreign_keys=[organization_id],
    )

    invited_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[invited_by_id],
    )
