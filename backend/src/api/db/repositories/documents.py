"""Queries against ``documents`` and ``document_versions`` — Phase 6, Tasks 6 and 10.

Both inherit ``OrgScopedRepository``, so ``WHERE organization_id = ?`` is on every
read and every write without either class mentioning it. That is Task 10 almost in its
entirety: what is left is the storage layer, which has no repository and is fenced
only by the tenant prefix in the key.

The queries that are written out here are the ones the base class cannot express: the
soft-delete filter, the deduplication lookup, and "the next version number for this
document".
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from api.db.repositories.org_scoped import OrgScopedRepository
from api.models.document import Document, DocumentVersion


class DocumentRepository(OrgScopedRepository[Document]):
    """Documents belonging to the context's organization."""

    model = Document

    async def get_live(self, document_id: UUID) -> Document | None:
        """One document, unless it has been deleted.

        Soft-deleted rows are invisible to every read path. They are kept because
        citations point at their versions, not because anyone should still find them
        by id — so a deleted document answers exactly as a missing one does.
        """
        result = await self.session.execute(
            select(Document)
            .where(
                Document.id == document_id,
                Document.organization_id == self.organization_id,
                Document.deleted_at.is_(None),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_live(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        created_by: UUID | None = None,
    ) -> Sequence[Document]:
        """A page of this organization's documents, newest first.

        ``created_by`` narrows to one uploader. It is a filter, not an authorization
        rule: ``document:read`` is unrestricted for both roles in the §7.6 matrix, so
        nothing here decides who may see what.
        """
        stmt = (
            select(Document)
            .where(
                Document.organization_id == self.organization_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if created_by is not None:
            stmt = stmt.where(Document.created_by == created_by)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_live(self, *, created_by: UUID | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(
                Document.organization_id == self.organization_id,
                Document.deleted_at.is_(None),
            )
        )
        if created_by is not None:
            stmt = stmt.where(Document.created_by == created_by)

        result = await self.session.execute(stmt)
        return result.scalar_one()


class DocumentVersionRepository(OrgScopedRepository[DocumentVersion]):
    """Versions belonging to the context's organization."""

    model = DocumentVersion

    async def get_by_number(self, document_id: UUID, version_number: int) -> DocumentVersion | None:
        """One version of one document.

        ``document_id`` is filtered as well as ``version_number`` — version numbers
        restart at 1 for every document, so the number alone names thousands of rows.
        """
        result = await self.session.execute(
            select(DocumentVersion)
            .where(
                DocumentVersion.organization_id == self.organization_id,
                DocumentVersion.document_id == document_id,
                DocumentVersion.version_number == version_number,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_document(self, document_id: UUID) -> Sequence[DocumentVersion]:
        """Every version of one document, oldest first."""
        result = await self.session.execute(
            select(DocumentVersion)
            .where(
                DocumentVersion.organization_id == self.organization_id,
                DocumentVersion.document_id == document_id,
            )
            .order_by(DocumentVersion.version_number)
        )
        return result.scalars().all()

    async def find_by_hash(self, content_hash: str) -> DocumentVersion | None:
        """The deduplication lookup — Task 6.

        **Scoped to the organization, and that is the whole point.** A global hash
        index would let one tenant's upload match another's, which leaks the existence
        of a document across a tenant boundary (invariant 2) and points two customers
        at one stored object, so deleting for one deletes for both. The cost of
        scoping is a duplicated object in the rare cross-tenant case; the cost of not
        scoping is a cross-tenant disclosure.

        Oldest match wins, so the answer is stable: repeated uploads of the same bytes
        always resolve to the same document rather than to whichever row sorted first.
        """
        result = await self.session.execute(
            select(DocumentVersion)
            .where(
                DocumentVersion.organization_id == self.organization_id,
                DocumentVersion.content_hash == content_hash,
            )
            .order_by(DocumentVersion.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def next_version_number(self, document_id: UUID) -> int:
        """One past the highest version this document has.

        Read-then-write, so two uploads racing on the same document can compute the
        same number. The unique constraint on ``(document_id, version_number)`` is what
        actually decides: the loser gets an IntegrityError, which the service turns
        into a 409 rather than a 500. Taking a row lock here would serialise uploads
        per document to prevent a conflict that is already handled and is, in practice,
        rare.
        """
        result = await self.session.execute(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.organization_id == self.organization_id,
                DocumentVersion.document_id == document_id,
            )
        )
        return (result.scalar_one() or 0) + 1
