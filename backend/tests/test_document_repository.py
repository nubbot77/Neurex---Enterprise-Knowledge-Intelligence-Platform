"""The document repositories, directly — Phase 6, Tasks 6 and 10.

These are the queries the base class cannot express: the soft-delete filter, the
ordering, the deduplication lookup and the next version number. Written against a
session rather than the API because each one needs rows in states the HTTP surface
cannot produce on demand — two documents with timestamps a day apart, a version whose
document was deleted, a hash belonging to another tenant.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from api.auth.context import OrgContext
from api.auth.permissions import permissions_for
from api.db.repositories.documents import DocumentRepository, DocumentVersionRepository
from api.models.document import Document, DocumentVersion
from api.models.membership import AccountType, MembershipRole
from api.models.organization import Organization, OrganizationKind


async def _organization(session, name: str = "Acme") -> Organization:
    organization = Organization(
        name=name,
        slug=f"{name.lower()}-{uuid.uuid4().hex[:8]}",
        kind=OrganizationKind.TEAM,
    )
    session.add(organization)
    await session.flush()
    return organization


def _context(organization: Organization) -> OrgContext:
    """A context for a tenant, with no user behind it.

    These tests exercise the filter, not the permission check — the role is an admin's
    because a repository never consults it.
    """
    return OrgContext(
        user_id=uuid.uuid4(),
        organization_id=organization.id,
        membership_id=uuid.uuid4(),
        role=MembershipRole.ADMIN,
        account_type=AccountType.MEMBER,
        permissions=permissions_for(MembershipRole.ADMIN),
        is_super_admin=False,
    )


async def _document(
    session, organization: Organization, *, title: str, created_at=None
) -> Document:
    document = Document(organization_id=organization.id, title=title, current_version=1)
    if created_at is not None:
        # Explicit, because the column default is ``now()`` — the *transaction's*
        # timestamp — and every row a test writes shares one transaction.
        document.created_at = created_at
        document.updated_at = created_at
    session.add(document)
    await session.flush()
    return document


async def _version(
    session,
    organization: Organization,
    document: Document,
    *,
    number: int = 1,
    content_hash: str = "0" * 64,
) -> DocumentVersion:
    version = DocumentVersion(
        organization_id=organization.id,
        document_id=document.id,
        version_number=number,
        storage_key=f"tenant_{organization.id}/documents/{document.id}/versions/v{number}/source.pdf",
        content_hash=content_hash,
        mime_type="application/pdf",
        file_size=1024,
        original_filename="handbook.pdf",
    )
    session.add(version)
    await session.flush()
    return version


@pytest.fixture
async def tenant(session):
    organization = await _organization(session)
    return organization, _context(organization)


# -- listing ------------------------------------------------------------------


async def test_list_orders_newest_first(session, tenant):
    organization, ctx = tenant
    now = datetime.now(UTC)

    await _document(session, organization, title="Older", created_at=now - timedelta(days=1))
    await _document(session, organization, title="Newer", created_at=now)

    rows = await DocumentRepository(session, ctx).list_live()

    assert [row.title for row in rows] == ["Newer", "Older"]


async def test_deleted_documents_are_invisible_to_every_read(session, tenant):
    organization, ctx = tenant
    document = await _document(session, organization, title="Gone")
    repository = DocumentRepository(session, ctx)

    assert await repository.get_live(document.id) is not None

    await repository.update(document, deleted_at=datetime.now(UTC))

    assert await repository.get_live(document.id) is None
    assert await repository.list_live() == []
    assert await repository.count_live() == 0


async def test_another_tenants_document_is_not_returned_by_id(session):
    """The base class's filter, on this table. A guessed id answers as a missing one."""
    mine = await _organization(session, "Mine")
    theirs = await _organization(session, "Theirs")
    document = await _document(session, theirs, title="Theirs")

    repository = DocumentRepository(session, _context(mine))

    assert await repository.get_live(document.id) is None
    assert await repository.list_live() == []


# -- deduplication ------------------------------------------------------------


async def test_find_by_hash_matches_within_the_organization(session, tenant):
    organization, ctx = tenant
    document = await _document(session, organization, title="Handbook")
    await _version(session, organization, document, content_hash="a" * 64)

    found = await DocumentVersionRepository(session, ctx).find_by_hash("a" * 64)

    assert found is not None
    assert found.document_id == document.id


async def test_find_by_hash_does_not_cross_tenants(session):
    """Invariant 2: identical bytes in another tenant are not this tenant's business."""
    mine = await _organization(session, "Mine")
    theirs = await _organization(session, "Theirs")
    document = await _document(session, theirs, title="Theirs")
    await _version(session, theirs, document, content_hash="b" * 64)

    found = await DocumentVersionRepository(session, _context(mine)).find_by_hash("b" * 64)

    assert found is None


async def test_find_by_hash_returns_the_oldest_match(session, tenant):
    """Repeated uploads of the same bytes must resolve to the same document every time."""
    organization, ctx = tenant
    now = datetime.now(UTC)

    first = await _document(
        session, organization, title="First", created_at=now - timedelta(days=2)
    )
    second = await _document(session, organization, title="Second", created_at=now)

    older = await _version(session, organization, first, content_hash="c" * 64)
    older.created_at = now - timedelta(days=2)
    newer = await _version(session, organization, second, content_hash="c" * 64)
    newer.created_at = now
    await session.flush()

    found = await DocumentVersionRepository(session, ctx).find_by_hash("c" * 64)

    assert found is not None
    assert found.document_id == first.id


# -- version numbering --------------------------------------------------------


async def test_next_version_number_starts_at_one(session, tenant):
    organization, ctx = tenant
    document = await _document(session, organization, title="New")

    assert await DocumentVersionRepository(session, ctx).next_version_number(document.id) == 1


async def test_next_version_number_follows_the_highest(session, tenant):
    organization, ctx = tenant
    document = await _document(session, organization, title="Revised")
    await _version(session, organization, document, number=1)
    await _version(session, organization, document, number=2)

    assert await DocumentVersionRepository(session, ctx).next_version_number(document.id) == 3


async def test_version_numbers_are_counted_per_document(session, tenant):
    """Numbers restart at 1 for every document, so the count must be scoped to one."""
    organization, ctx = tenant
    busy = await _document(session, organization, title="Busy")
    await _version(session, organization, busy, number=1)
    await _version(session, organization, busy, number=2)

    fresh = await _document(session, organization, title="Fresh")

    assert await DocumentVersionRepository(session, ctx).next_version_number(fresh.id) == 1
