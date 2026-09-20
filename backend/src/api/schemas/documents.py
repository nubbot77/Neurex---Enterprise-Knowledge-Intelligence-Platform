"""Request and response shapes for document routes — Phase 6, Task 4.

The upload response is the one worth thinking about, because architecture §10 fixes
its shape around something this phase does not build yet:

    {"document_id": "...", "job_id": "...", "status": "queued"}

The ingestion job arrives in Phase 7. Rather than inventing a job id, ``job_id`` is
declared now and answers ``null`` until there is a job to name — a field that appears
later is a breaking change for every client written against this one, while a field
that stops being null is not.

``status`` is not repeated at the top level: it lives on the document, where it is the
column the pipeline actually updates, and two copies of a status in one response is an
invitation to read the stale one.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from api.models.document import DocumentStatus


class DocumentVersionResponse(BaseModel):
    """One stored file.

    ``storage_key`` is deliberately absent. It is an internal pointer, and a client
    that holds one is a client that will eventually be given a way to use it —
    which would move the tenant fence out of the request path and into a string.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    content_hash: str
    mime_type: str
    file_size: int
    original_filename: str
    uploaded_by: uuid.UUID | None
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: DocumentStatus
    current_version: int
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """What an upload returns, immediately.

    ``deduplicated`` is true when the bytes were already in this organization and no
    new object was stored. The client gets the existing document rather than a
    duplicate, and the flag is what lets an uploader tell "saved" from "already had
    it" without diffing ids.
    """

    document: DocumentResponse
    version: DocumentVersionResponse
    job_id: uuid.UUID | None = None
    deduplicated: bool = False


class DocumentListResponse(BaseModel):
    """A page of documents, plus the total the page was taken from.

    ``total`` is the count for the whole organization, not for the page — a client
    cannot build pagination out of ``len(items)`` alone.
    """

    items: list[DocumentResponse]
    count: int
    total: int


class DocumentVersionListResponse(BaseModel):
    items: list[DocumentVersionResponse]
    count: int


class DocumentUpdateRequest(BaseModel):
    """Only the title is editable.

    Everything else about a document describes bytes that were already uploaded.
    Letting a client change ``mime_type`` or ``file_size`` would let them describe a
    file that does not exist, and the pipeline downstream believes these columns.
    """

    title: str = Field(min_length=1, max_length=512)
