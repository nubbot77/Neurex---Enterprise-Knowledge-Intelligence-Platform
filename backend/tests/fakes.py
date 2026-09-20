"""Test doubles — Phase 6.

``InMemoryStorage`` is a complete ``StorageProvider``, not a mock: it implements the
same contract the routes are written against, so a test exercises the real service,
the real repositories and the real request path with only the bytes' destination
swapped. A mock asserting that ``put_stream`` was called would prove the service calls
a method, which is not a fact anyone doubts.

It keeps what R2 cannot be asked in a test — which keys exist, what they contain, and
which ones were deleted — so tests can assert that a deduplicated upload stored nothing
and that a soft-deleted document kept its bytes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from shared.storage.base import (
    DOWNLOAD_CHUNK_SIZE,
    ObjectNotFound,
    StorageProvider,
    StoredObject,
)


class InMemoryStorage(StorageProvider):
    """Object storage in a dictionary."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        # Every key ever deleted, in order. Deduplication and failed uploads both
        # clean up after themselves, and "was the orphan removed?" is exactly the
        # kind of thing that silently stops being true.
        self.deleted: list[str] = []

    async def put_stream(
        self,
        *,
        key: str,
        chunks: AsyncIterator[bytes],
        content_type: str,
    ) -> StoredObject:
        buffer = bytearray()
        async for chunk in chunks:
            # No early exit and no size limit here: the meter in the service raises
            # mid-iteration, and letting that exception out is the behaviour under
            # test. Swallowing it would make the size cap untestable.
            buffer.extend(chunk)

        self.objects[key] = bytes(buffer)
        self.content_types[key] = content_type
        return StoredObject(key=key, size=len(buffer), content_type=content_type, etag='"fake"')

    async def open_stream(
        self,
        key: str,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        if key not in self.objects:
            raise ObjectNotFound(key)

        data = self.objects[key]
        for start in range(0, len(data), chunk_size):
            yield data[start : start + chunk_size]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.content_types.pop(key, None)
        self.deleted.append(key)

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def presigned_url(self, key: str, *, expires_in: int = 300) -> str:
        return f"https://storage.invalid/{key}?expires={expires_in}"
