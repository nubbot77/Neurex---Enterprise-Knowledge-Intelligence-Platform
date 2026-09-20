"""Document routes — Phase 6, Tasks 8 and 10.

Mounted under ``/api/v1/orgs/{organization_id}/documents``, so the tenant is in the
URL, the access log and every trace. The router carries ``DefaultDeny``: a route added
here that forgets to declare a permission refuses everyone and is logged as an error at
boot, rather than opening silently.

Handlers stay thin — validate the shape, call the service, serialise the result. The
one piece of real logic in this file is the ``Content-Length`` guard, which is here
rather than in the service because it has to run before the body is read at all.
"""

from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from api.auth.context import OrgContext
from api.auth.dependencies import DocumentServiceDep
from api.auth.permissions import Permission
from api.auth.rbac import DefaultDeny, require
from api.config.settings import Settings, get_settings
from api.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadResponse,
    DocumentVersionListResponse,
    DocumentVersionResponse,
)
from api.services.document_errors import FileTooLarge
from api.services.document_service import UploadOutcome

router = APIRouter(
    prefix="/orgs/{organization_id}/documents",
    tags=["documents"],
    dependencies=[DefaultDeny],
)


async def enforce_content_length(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject an obviously oversized upload before its body is read.

    ``Content-Length`` is a string the client chose, so this is **not** the size
    guarantee — the byte count taken while streaming is, and it runs regardless. This
    exists so that the ordinary case of someone picking a 2GB file costs one rejected
    header instead of 2GB of transfer, and so a lying header buys nothing but a longer
    wait before the same 413.
    """
    declared = request.headers.get("content-length")
    if declared is None or not declared.isdigit():
        return

    if int(declared) > settings.max_upload_bytes:
        raise FileTooLarge(
            f"Uploads are limited to {settings.max_upload_bytes} bytes.",
            reason="content_length_exceeded",
        )


def _uploaded(outcome: UploadOutcome) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(outcome.document),
        version=DocumentVersionResponse.model_validate(outcome.version),
        # Phase 7 fills this in when the ingestion job exists. Declared now so adding
        # it is not a breaking change for clients written against this response.
        job_id=None,
        deduplicated=outcome.deduplicated,
    )


def _content_disposition(filename: str) -> str:
    """Attachment, with the filename given twice.

    The bare ``filename=`` is ASCII-only and is what old clients read; ``filename*``
    carries the real, possibly non-ASCII name per RFC 5987. Quoting both is what stops
    a name containing a quote or a newline from injecting a header.
    """
    ascii_name = filename.encode("ascii", "replace").decode("ascii").replace('"', "")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def _download(version, stream) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type=version.mime_type,
        headers={
            "Content-Disposition": _content_disposition(version.original_filename),
            "Content-Length": str(version.file_size),
            # The bytes are one organization's private content. A cache between here
            # and the client holding a copy is a cross-tenant leak waiting for a
            # shared proxy.
            "Cache-Control": "private, no-store",
        },
    )


# -- upload ------------------------------------------------------------------


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_content_length)],
)
async def upload_document(
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_CREATE))],
    service: DocumentServiceDep,
    file: Annotated[UploadFile, File(description="The source file")],
    title: Annotated[str | None, Form(description="Defaults to the filename")] = None,
) -> DocumentUploadResponse:
    """Upload a new document.

    Returns as soon as the object is stored and the rows are written; nothing is
    parsed, chunked or embedded here. From Phase 7 this also enqueues an ingestion job
    and ``job_id`` stops being null.

    A file whose bytes are already in this organization returns the existing document
    with ``deduplicated: true`` and stores nothing new.
    """
    outcome = await service.upload(ctx, upload=file, title=title)
    return _uploaded(outcome)


@router.post(
    "/{document_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_content_length)],
)
async def upload_version(
    document_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_UPDATE))],
    service: DocumentServiceDep,
    file: Annotated[UploadFile, File(description="The revised file")],
) -> DocumentUploadResponse:
    """Add a version to an existing document.

    Declares ``document:update`` rather than ``document:create``: this changes a
    document that already exists, and a member who may edit documents may revise one.

    Re-uploading the current version's exact bytes changes nothing and returns the
    current version.
    """
    outcome = await service.add_version(ctx, document_id=document_id, upload=file)
    return _uploaded(outcome)


# -- metadata ----------------------------------------------------------------


@router.get("")
async def list_documents(
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_READ))],
    service: DocumentServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    """This organization's documents, newest first. Deleted ones are not listed."""
    documents, total = await service.list_documents(ctx, limit=limit, offset=offset)
    items = [DocumentResponse.model_validate(d) for d in documents]
    return DocumentListResponse(items=items, count=len(items), total=total)


@router.get("/{document_id}")
async def read_document(
    document_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_READ))],
    service: DocumentServiceDep,
) -> DocumentResponse:
    """One document's metadata.

    An id from another organization answers 404, identically to one that does not
    exist anywhere — the lookup is scoped before it is performed.
    """
    return DocumentResponse.model_validate(await service.get_document(ctx, document_id))


@router.get("/{document_id}/versions")
async def list_document_versions(
    document_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_READ))],
    service: DocumentServiceDep,
) -> DocumentVersionListResponse:
    """Every version of one document, oldest first."""
    versions = await service.list_versions(ctx, document_id)
    items = [DocumentVersionResponse.model_validate(v) for v in versions]
    return DocumentVersionListResponse(items=items, count=len(items))


@router.patch("/{document_id}")
async def rename_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_UPDATE))],
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Rename a document. Its versions are untouched."""
    document = await service.rename(ctx, document_id=document_id, title=payload.title)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_DELETE))],
    service: DocumentServiceDep,
) -> None:
    """Remove a document from every read path.

    Admins only — ``document:delete`` is not in the member matrix (§7.6). The row and
    the stored objects are kept: a citation from Phase 19 points at a version, and
    deleting the bytes would strand the provenance of an answer already given.
    """
    await service.delete(ctx, document_id=document_id)


# -- download ----------------------------------------------------------------


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_READ))],
    service: DocumentServiceDep,
) -> StreamingResponse:
    """The current version's bytes, streamed through the API.

    Streaming rather than redirecting to a presigned URL: it keeps the tenant fence in
    the request path, where the scoped repository enforces it on every call, instead of
    in a URL whose only protection is an expiry. The provider can still mint presigned
    URLs — that is a decision for a route that needs one, not a default for all of them.
    """
    version, stream = await service.open_download(ctx, document_id)
    return _download(version, stream)


@router.get("/{document_id}/versions/{version_number}/download")
async def download_document_version(
    document_id: uuid.UUID,
    version_number: int,
    ctx: Annotated[OrgContext, Depends(require(Permission.DOCUMENT_READ))],
    service: DocumentServiceDep,
) -> StreamingResponse:
    """One specific version's bytes.

    This is what makes a citation reproducible: an answer generated from version 2 can
    be checked against version 2 after version 3 has replaced it.
    """
    version, stream = await service.open_download(ctx, document_id, version_number)
    return _download(version, stream)
