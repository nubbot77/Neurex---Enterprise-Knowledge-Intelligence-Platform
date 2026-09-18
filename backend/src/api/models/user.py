from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.membership import Membership


class User(Base, TimestampMixin):
    """A global identity: one human, one credential.

    Deliberately carries no ``role`` and no ``organization_id``. Authority inside an
    organization lives on ``Membership`` — see architecture §7.2. ``is_super_admin`` is
    the single exception: it is platform-wide, belongs to no organization, and is a
    fact about the person rather than about a relationship.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Platform operator. Bypasses the organization filter only through an explicit
    # named argument, read-only, and always audited — architecture §7.10.
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    # Membership has two foreign keys to users.id (user_id and invited_by_id), so
    # this relationship must say which one it means.
    memberships: Mapped[list[Membership]] = relationship(
        "Membership",
        back_populates="user",
        foreign_keys="Membership.user_id",
        cascade="all, delete-orphan",
    )
