"""Documents and their versions — Phase 6, Task 3.

Architecture §9. Two tables, not one, and the split is not bookkeeping:

``Document``
    the stable identity a user, a URL and — from Phase 19 — a citation refer to.

``DocumentVersion``
    one uploaded file. Immutable once written: bytes, hash, size and type describe an
    upload that already happened, and rewriting them would make an answer's provenance
    a lie.

If uploading a revision overwrote the row, a citation generated in March would silently
start describing text the model never saw. That single failure is what versioning buys
protection from; §9 lists the rest — rollback, reproducibility, auditing, re-indexing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base import Base, TimestampMixin


class DocumentStatus(StrEnum):
    """Where a document is in the pipeline.

    Phase 6 only ever writes ``UPLOADED``: the file is stored and recorded, and nothing
    has read its contents yet. The remaining values are the ones the ingestion job in
    Phase 7 will drive, declared now so that adding the worker is a code change rather
    than a migration plus a code change — an enum constrained by a CHECK cannot gain a
    value without DDL.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base, TimestampMixin):
    """One logical document inside one organization."""

    __tablename__ = "documents"

    __table_args__ = (
        # Every listing is "this organization's documents, newest first". The
        # organization_id index alone would still sort the whole tenant in memory.
        Index("ix_documents_org_created_at", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)

    # Which version is current, by number rather than by a foreign key to
    # ``document_versions.id``. A key in that direction plus the one already pointing
    # back at ``documents`` is a circular FK: it needs use_alter, a post_update
    # relationship and a two-step migration, and it buys nothing a number backed by
    # the (document_id, version_number) unique constraint does not already give.
    current_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            native_enum=False,
            create_constraint=True,
            # Store the lowercase .value, not the enum .name — the CHECK constraint
            # is generated from whatever is stored, and server_default uses .value.
            values_callable=lambda e: [m.value for m in e],
            length=20,
            name="document_status",
        ),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        server_default=DocumentStatus.UPLOADED.value,
    )

    # SET NULL, not CASCADE: deleting the person who uploaded a handbook must not
    # delete the handbook. Nullable for the same reason, and ownership checks treat
    # a null uploader as "not yours" (``OrgContext.owns_or_has_full``).
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Soft delete. The row and the stored objects stay: from Phase 19 a citation points
    # at a version, and hard-deleting the bytes would strand the provenance of an
    # answer that has already been given. Purging is a retention job with its own
    # audit trail, not a side effect of someone clicking delete.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    versions: Mapped[list[DocumentVersion]] = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )


class DocumentVersion(Base, TimestampMixin):
    """One uploaded file. Write once, read forever."""

    __tablename__ = "document_versions"

    __table_args__ = (
        # Version numbers are dense and per document, so "v2" names exactly one row.
        UniqueConstraint("document_id", "version_number", name="uq_document_versions_doc_number"),
        # Deduplication looks up (this organization, this hash) on every upload —
        # Task 6. Deliberately an index and **not** a unique constraint: a document
        # whose version 3 restores version 1's content is legitimate and would violate
        # uniqueness, and the check belongs where it can answer with a 200 and an
        # existing document rather than with a constraint violation surfaced as a 500.
        Index("ix_document_versions_org_hash", "organization_id", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Denormalised from the parent document on purpose. Every tenant-scoped row carries
    # its own ``organization_id`` (invariant 1) so that ``OrgScopedRepository`` can
    # filter this table without a join — and a filter that depends on a join is a
    # filter someone can drop.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # The §8 pointer. Unique across the bucket because the key embeds the tenant, the
    # document and the version — two rows sharing one would mean one of them is wrong.
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)

    # SHA-256, hex. 64 characters, fixed.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # BigInteger: a 4-byte integer caps at 2GB, and the cap on uploads is a policy
    # setting someone will raise without thinking about the column type.
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    document: Mapped[Document] = relationship("Document", back_populates="versions")
