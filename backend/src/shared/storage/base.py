"""The storage contract — Phase 6, Task 1.

Architecture §8. Source files live in object storage; PostgreSQL keeps a pointer and
nothing else. Everything above this module is written against ``StorageProvider`` and
never learns which provider is underneath, so swapping R2 for S3, MinIO or a local
filesystem touches one file.

Two properties of this interface matter more than its method list:

**Everything is a stream.** No method takes or returns ``bytes`` for an object body. A
``put(key, data: bytes)`` would be shorter and would quietly make a 500MB upload a
500MB allocation — the failure arrives as an OOM kill with no traceback, under load,
in production. The shape of the interface is what rules that out for every caller.

**Keys are built here, not by callers.** ``document_version_key`` is the single place
the §8 layout is written down. A route composing its own key is one typo away from
writing another tenant's prefix, and no repository filter can catch that.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

# 8 MiB parts. S3 multipart requires every part except the last to be at least 5 MiB,
# and this is the largest buffer a single upload is allowed to hold in memory.
PART_SIZE = 8 * 1024 * 1024

# What a download reads per iteration. Smaller than a part: nothing accumulates.
DOWNLOAD_CHUNK_SIZE = 64 * 1024


class StorageError(Exception):
    """Base class for storage failures the API layer may want to distinguish."""


class ObjectNotFound(StorageError):
    """The key does not exist.

    Raised rather than returning ``None`` because a caller reaching this point has a
    database row pointing at the key: the object should be there, and a missing one is
    an inconsistency worth a stack trace, not an ordinary empty result.
    """


@dataclass(frozen=True, slots=True)
class StoredObject:
    """What the provider observed while storing an object.

    ``size`` is the byte count the provider actually wrote — not what the client
    claimed in ``Content-Length``, which is an attacker-controlled string.
    """

    key: str
    size: int
    content_type: str
    etag: str | None = None


def tenant_prefix(organization_id: UUID) -> str:
    """Every key for a tenant starts here — architecture §8.

    The tenant is the first path segment on purpose: a misrouted key is visible at a
    glance in a bucket listing, and a bucket-level prefix policy stays possible later.
    Object storage has no repository to filter it, so this prefix is the only fence
    the bytes themselves have.
    """
    return f"tenant_{organization_id}"


def document_version_key(
    *,
    organization_id: UUID,
    document_id: UUID,
    version: int,
    extension: str,
) -> str:
    """The §8 layout: ``tenant_{id}/documents/{document_id}/versions/vN/source.ext``.

    The extension is carried for human legibility in a bucket listing only. Nothing
    reads it back — ``mime_type`` in the database is authoritative, because the
    extension came from the client and was only ever cross-checked, never trusted.
    """
    suffix = f".{extension.lstrip('.')}" if extension else ""
    return (
        f"{tenant_prefix(organization_id)}/documents/{document_id}"
        f"/versions/v{version}/source{suffix}"
    )


class StorageProvider(ABC):
    """Object storage, as everything above it sees it."""

    @abstractmethod
    async def put_stream(
        self,
        *,
        key: str,
        chunks: AsyncIterator[bytes],
        content_type: str,
    ) -> StoredObject:
        """Write an object from an async stream of chunks.

        The implementation must hold no more than one part in memory, and must clean
        up after itself if ``chunks`` raises — a cancelled upload that leaves parts
        behind is billed for, indefinitely, with nothing pointing at it.
        """

    @abstractmethod
    def open_stream(
        self,
        key: str,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        """Read an object back, one chunk at a time.

        Deliberately not ``async def``: implementations are async generator functions,
        so calling this returns the iterator without an ``await`` and the caller writes
        ``async for chunk in storage.open_stream(key)``.

        Raises ``ObjectNotFound`` when the key is absent.
        """

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove an object. Deleting a key that is already gone is not an error."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Whether the key is present."""

    @abstractmethod
    async def presigned_url(self, key: str, *, expires_in: int = 300) -> str:
        """A time-limited direct URL to the object.

        Not used by the download route, which streams through the API so that the
        tenant fence stays in the request path rather than in a URL's expiry. It exists
        for the cases that genuinely need to hand bytes to something outside the API
        (a browser fetching a large original), and so the decision is a route's to
        make rather than a provider capability nobody has.
        """
