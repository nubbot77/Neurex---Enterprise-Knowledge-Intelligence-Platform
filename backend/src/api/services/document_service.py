"""Document operations — Phase 6, Tasks 6, 7 and 9.

This is where the §10 upload flow is actually carried out, in the order §10 gives:
authenticate, authorize, validate, hash, store, record. Authentication and
authorization already happened at the route; everything from validation onwards is
here.

Three decisions in this file are worth reading before changing anything in it.

**The bytes are never materialised.** The request body is read in chunks, each chunk is
hashed and counted as it passes through, and the same chunk goes straight to storage.
Nothing accumulates but one multipart part inside the provider. A 500MB upload costs
8MB of memory, and the size cap is enforced against bytes actually read rather than
against the ``Content-Length`` the client chose.

**Storage is written before the database.** A row pointing at a key that does not exist
is unfixable from the outside — every read of it fails and nothing can tell whether the
object was lost or never written. A stored object with no row is merely garbage, and
garbage is sweepable. So the object goes first, and a failed database write deletes it
on the way out.

**Deduplication runs after the upload, not before it.** The hash is only known once the
bytes have been read, so the duplicate case pays for one wasted upload and then deletes
it. The alternative — buffering the whole file to hash it before deciding — is the
thing the first decision exists to prevent.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.context import OrgContext
from api.db.repositories.documents import DocumentRepository, DocumentVersionRepository
from api.models.document import Document, DocumentStatus, DocumentVersion
from api.services.document_errors import (
    DocumentNotFound,
    DocumentVersionConflict,
    DocumentVersionNotFound,
    EmptyUpload,
    FileTooLarge,
)
from api.services.file_validation import (
    SNIFF_BYTES,
    FileFormat,
    check_declared_mime_type,
    check_magic_bytes,
    extension_of,
    format_for_filename,
)
from shared.storage.base import StorageProvider, document_version_key

logger = structlog.get_logger(__name__)

# What each read from the request body asks for. Independent of the storage provider's
# part size: this bounds how much arrives at once, the provider bounds how much is held.
READ_CHUNK_SIZE = 1024 * 1024


@dataclass(slots=True)
class _Meter:
    """Carries the hash and the byte count out of a generator.

    A generator cannot return a value to a caller that iterates it, and the two facts
    the service needs — how many bytes there were and what they hashed to — are only
    known once iteration has finished. So they are written to this object as the
    stream runs, and read from it afterwards.
    """

    limit: int
    size: int = 0
    digest: hashlib._Hash = field(default_factory=hashlib.sha256)

    @property
    def content_hash(self) -> str:
        return self.digest.hexdigest()

    def consume(self, chunk: bytes) -> None:
        self.size += len(chunk)
        if self.size > self.limit:
            # Raised mid-stream, so the rest of the body is never read and the
            # provider aborts its multipart upload on the way out. Checking after the
            # fact would mean storing the oversized file first.
            raise FileTooLarge(
                f"Uploads are limited to {self.limit} bytes.",
                reason="size_limit_exceeded",
            )
        self.digest.update(chunk)


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    """What an upload produced, and whether it stored anything new."""

    document: Document
    version: DocumentVersion
    deduplicated: bool


class DocumentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: StorageProvider,
        max_upload_bytes: int,
    ) -> None:
        self.session = session
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes

    # -- reads -------------------------------------------------------------

    async def list_documents(
        self, ctx: OrgContext, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Document], int]:
        documents = self._documents(ctx)
        rows = await documents.list_live(limit=limit, offset=offset)
        return rows, await documents.count_live()

    async def get_document(self, ctx: OrgContext, document_id: uuid.UUID) -> Document:
        document = await self._documents(ctx).get_live(document_id)
        if document is None:
            raise DocumentNotFound(reason="document_absent_or_other_tenant")
        return document

    async def list_versions(
        self, ctx: OrgContext, document_id: uuid.UUID
    ) -> Sequence[DocumentVersion]:
        await self.get_document(ctx, document_id)
        return await self._versions(ctx).list_for_document(document_id)

    async def get_version(
        self,
        ctx: OrgContext,
        document_id: uuid.UUID,
        version_number: int | None = None,
    ) -> DocumentVersion:
        """One version, defaulting to the document's current one.

        The document is fetched first, so a version id belonging to another tenant — or
        to a deleted document — cannot be reached by naming its number.
        """
        document = await self.get_document(ctx, document_id)
        wanted = version_number if version_number is not None else document.current_version

        version = await self._versions(ctx).get_by_number(document_id, wanted)
        if version is None:
            raise DocumentVersionNotFound(reason="version_absent")
        return version

    async def open_download(
        self,
        ctx: OrgContext,
        document_id: uuid.UUID,
        version_number: int | None = None,
    ) -> tuple[DocumentVersion, AsyncIterator[bytes]]:
        """Resolve a version and open its bytes for streaming.

        The storage key comes from a row this organization owns; it is never accepted
        from the client. That is the whole tenant fence on the download path — object
        storage has no repository to filter it, so a route taking a key as a parameter
        would be a cross-tenant read with nothing in its way.
        """
        version = await self.get_version(ctx, document_id, version_number)
        return version, self.storage.open_stream(version.storage_key)

    # -- writes ------------------------------------------------------------

    async def upload(
        self,
        ctx: OrgContext,
        *,
        upload: UploadFile,
        title: str | None = None,
    ) -> UploadOutcome:
        """Store a new document: validate, stream, hash, deduplicate, record."""
        fmt, head = await self._validate(upload)

        document_id = uuid.uuid4()
        filename = _safe_filename(upload.filename)
        key = document_version_key(
            organization_id=ctx.organization_id,
            document_id=document_id,
            version=1,
            extension=extension_of(filename),
        )

        meter, stored = await self._store(upload, head=head, key=key, fmt=fmt)

        duplicate = await self._existing_duplicate(ctx, meter.content_hash)
        if duplicate is not None:
            document, version = duplicate
            await self._discard(key)
            logger.info(
                "document.upload_deduplicated",
                document_id=str(document.id),
                content_hash=meter.content_hash,
                **ctx.log_fields(),
            )
            return UploadOutcome(document=document, version=version, deduplicated=True)

        documents = self._documents(ctx)
        versions = self._versions(ctx)

        try:
            document = await documents.create(
                id=document_id,
                title=(title or filename).strip()[:512],
                current_version=1,
                status=DocumentStatus.UPLOADED,
                created_by=ctx.user_id,
            )
            version = await versions.create(
                document_id=document.id,
                version_number=1,
                storage_key=stored.key,
                content_hash=meter.content_hash,
                mime_type=fmt.mime_type,
                file_size=meter.size,
                original_filename=filename,
                uploaded_by=ctx.user_id,
            )
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            await self._discard(key)
            raise

        logger.info(
            "document.uploaded",
            document_id=str(document.id),
            version=1,
            file_size=meter.size,
            mime_type=fmt.mime_type,
            **ctx.log_fields(),
        )
        return UploadOutcome(document=document, version=version, deduplicated=False)

    async def add_version(
        self,
        ctx: OrgContext,
        *,
        document_id: uuid.UUID,
        upload: UploadFile,
    ) -> UploadOutcome:
        """Upload a revision of an existing document.

        Re-uploading the current version's exact bytes is a no-op that returns the
        current version, rather than a second row describing the same file. Uploading
        bytes that match an *older* version does create a new version: the document
        genuinely changed, and its history has to show that it changed back.
        """
        document = await self.get_document(ctx, document_id)
        fmt, head = await self._validate(upload)

        versions = self._versions(ctx)
        number = await versions.next_version_number(document_id)
        filename = _safe_filename(upload.filename)

        key = document_version_key(
            organization_id=ctx.organization_id,
            document_id=document_id,
            version=number,
            extension=extension_of(filename),
        )
        meter, stored = await self._store(upload, head=head, key=key, fmt=fmt)

        current = await versions.get_by_number(document_id, document.current_version)
        if current is not None and current.content_hash == meter.content_hash:
            await self._discard(key)
            logger.info(
                "document.version_unchanged",
                document_id=str(document_id),
                version=current.version_number,
                **ctx.log_fields(),
            )
            return UploadOutcome(document=document, version=current, deduplicated=True)

        try:
            version = await versions.create(
                document_id=document_id,
                version_number=number,
                storage_key=stored.key,
                content_hash=meter.content_hash,
                mime_type=fmt.mime_type,
                file_size=meter.size,
                original_filename=filename,
                uploaded_by=ctx.user_id,
            )
            document = await self._documents(ctx).update(
                document,
                current_version=number,
                status=DocumentStatus.UPLOADED,
            )
            await self.session.commit()
            # ``updated_at`` carries a server-side onupdate, so its new value is
            # unknown to the session after the UPDATE and the attribute is left
            # expired. Serialising the row would then trigger a lazy load outside the
            # async greenlet — a MissingGreenlet error at the response, far from its
            # cause. One SELECT here is the fix.
            await self.session.refresh(document)
        except IntegrityError:
            # Two uploads raced and computed the same version number. The unique
            # constraint on (document_id, version_number) decided; the loser is told to
            # retry rather than shown a 500.
            await self.session.rollback()
            await self._discard(key)
            raise DocumentVersionConflict(reason="version_number_taken") from None
        except BaseException:
            await self.session.rollback()
            await self._discard(key)
            raise

        logger.info(
            "document.version_added",
            document_id=str(document_id),
            version=number,
            file_size=meter.size,
            **ctx.log_fields(),
        )
        return UploadOutcome(document=document, version=version, deduplicated=False)

    async def rename(self, ctx: OrgContext, *, document_id: uuid.UUID, title: str) -> Document:
        document = await self.get_document(ctx, document_id)
        updated = await self._documents(ctx).update(document, title=title.strip()[:512])
        await self.session.commit()
        # See ``add_version``: the server-side onupdate on ``updated_at`` leaves the
        # attribute expired after a commit, and the route serialises it.
        await self.session.refresh(updated)
        return updated

    async def delete(self, ctx: OrgContext, *, document_id: uuid.UUID) -> None:
        """Soft delete. The row and the stored objects stay.

        From Phase 19 a citation points at a version, so removing the bytes would
        strand the provenance of an answer that has already been given. Purging is a
        retention job with its own audit trail, not a side effect of this route.
        """
        document = await self.get_document(ctx, document_id)
        await self._documents(ctx).update(document, deleted_at=datetime.now(UTC))
        await self.session.commit()

        logger.info("document.deleted", document_id=str(document_id), **ctx.log_fields())

    # -- internals ---------------------------------------------------------

    def _documents(self, ctx: OrgContext) -> DocumentRepository:
        return DocumentRepository(self.session, ctx)

    def _versions(self, ctx: OrgContext) -> DocumentVersionRepository:
        return DocumentVersionRepository(self.session, ctx)

    async def _validate(self, upload: UploadFile) -> tuple[FileFormat, bytes]:
        """Tasks 5. Everything cheap first, the magic bytes last and decisive.

        Returns the format and the head of the file, which the caller has to send on
        to storage — it has already been read off the stream and cannot be read again.
        """
        fmt = format_for_filename(upload.filename or "")
        check_declared_mime_type(fmt, upload.content_type)

        head = await upload.read(SNIFF_BYTES)
        if not head:
            raise EmptyUpload(reason="zero_bytes")

        check_magic_bytes(fmt, head)
        return fmt, head

    async def _store(
        self,
        upload: UploadFile,
        *,
        head: bytes,
        key: str,
        fmt: FileFormat,
    ):
        """Stream the body to storage, hashing and counting on the way past."""
        meter = _Meter(limit=self.max_upload_bytes)
        stored = await self.storage.put_stream(
            key=key,
            chunks=_chunks(upload, head=head, meter=meter),
            content_type=fmt.mime_type,
        )
        return meter, stored

    async def _existing_duplicate(
        self, ctx: OrgContext, content_hash: str
    ) -> tuple[Document, DocumentVersion] | None:
        """Task 6, scoped to this organization — see ``find_by_hash``.

        A match whose document has been deleted is *not* a duplicate: the caller is
        re-uploading something the organization threw away, and pointing them at a
        soft-deleted row would hand back a document no route will show them.
        """
        match = await self._versions(ctx).find_by_hash(content_hash)
        if match is None:
            return None

        document = await self._documents(ctx).get_live(match.document_id)
        if document is None:
            return None

        return document, match

    async def _discard(self, key: str) -> None:
        """Delete an object nothing is going to point at.

        Best effort on purpose. The request has either succeeded by another route
        (deduplication) or is already failing, and a storage error here would replace
        a useful outcome with an unrelated one. What is left behind is an orphan the
        sweep can find; what must never be left behind is a database row without its
        object.
        """
        try:
            await self.storage.delete(key)
        except Exception:
            logger.error("storage.orphan_left", key=key)


def _safe_filename(filename: str | None) -> str:
    """The client's filename, stripped of any path it arrived with.

    Browsers send a bare name, but the field is client-controlled and
    ``../../etc/passwd`` is free to type. The name is only ever stored and echoed back
    — the storage key is built from ids, never from this — so stripping the separators
    is enough, and rejecting the upload over a filename would be theatre.
    """
    name = (filename or "upload").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name[:512] or "upload"


async def _chunks(upload: UploadFile, *, head: bytes, meter: _Meter) -> AsyncIterator[bytes]:
    """The request body, from the first byte, measured as it goes.

    ``head`` was already read by validation, so it is yielded first: an upload that
    started at the second chunk would store a truncated file whose hash matches
    nothing.
    """
    chunk = head
    while chunk:
        meter.consume(chunk)
        yield chunk
        chunk = await upload.read(READ_CHUNK_SIZE)
