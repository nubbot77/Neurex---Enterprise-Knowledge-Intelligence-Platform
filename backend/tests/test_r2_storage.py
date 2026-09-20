"""The R2 provider's upload path — Phase 6, Tasks 2 and 9.

``InMemoryStorage`` stands in for R2 everywhere else in the suite, which leaves the
part-splitting logic — the one piece of Phase 6 rated High — with no coverage at all.
It cannot be exercised against a real bucket in a test run, so the S3 client is
replaced with a recorder and the provider's own decisions are asserted:

* a small object takes one ``put_object`` and never opens a multipart upload;
* a large one is cut into parts of exactly ``PART_SIZE``, with the remainder last, and
  reassembles to the original bytes;
* a stream that raises aborts the multipart upload instead of leaving parts behind,
  which are invisible in a bucket listing and billed until something sweeps them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from shared.storage.base import PART_SIZE
from shared.storage.r2 import R2Storage


class _FakeS3:
    """Records what the provider asked S3 to do."""

    def __init__(self) -> None:
        self.parts: list[bytes] = []
        self.put_object_body: bytes | None = None
        self.completed: list[dict] | None = None
        self.created_multipart = False
        self.aborted = False

    async def create_multipart_upload(self, **kwargs) -> dict:
        self.created_multipart = True
        return {"UploadId": "upload-1"}

    async def upload_part(self, **kwargs) -> dict:
        self.parts.append(kwargs["Body"])
        return {"ETag": f'"part-{kwargs["PartNumber"]}"'}

    async def complete_multipart_upload(self, **kwargs) -> dict:
        self.completed = kwargs["MultipartUpload"]["Parts"]
        return {"ETag": '"complete"'}

    async def put_object(self, **kwargs) -> dict:
        self.put_object_body = kwargs["Body"]
        return {"ETag": '"single"'}

    async def abort_multipart_upload(self, **kwargs) -> None:
        self.aborted = True


class _FakeClient:
    def __init__(self, s3: _FakeS3) -> None:
        self._s3 = s3

    async def __aenter__(self) -> _FakeS3:
        return self._s3

    async def __aexit__(self, *exc_info) -> None:
        return None


class RecordingR2(R2Storage):
    """The real provider with its S3 client swapped for the recorder."""

    def __init__(self) -> None:
        super().__init__(
            bucket="test-bucket",
            endpoint_url="https://account.r2.cloudflarestorage.com",
            access_key_id="key",
            secret_access_key="secret",
        )
        self.s3 = _FakeS3()

    def _client(self) -> _FakeClient:
        return _FakeClient(self.s3)


async def _stream(*chunks: bytes) -> AsyncIterator[bytes]:
    for chunk in chunks:
        yield chunk


@pytest.fixture
def storage() -> RecordingR2:
    return RecordingR2()


async def test_a_small_object_takes_one_request(storage: RecordingR2):
    """The common case must not pay for a three-request multipart dance."""
    stored = await storage.put_stream(
        key="tenant_x/doc.pdf",
        chunks=_stream(b"%PDF-1.7", b" small"),
        content_type="application/pdf",
    )

    assert storage.s3.created_multipart is False
    assert storage.s3.put_object_body == b"%PDF-1.7 small"
    assert stored.size == len(b"%PDF-1.7 small")


async def test_an_object_larger_than_a_part_is_uploaded_in_parts(storage: RecordingR2):
    payload = b"a" * (PART_SIZE + 1024)

    stored = await storage.put_stream(
        key="tenant_x/big.pdf",
        # Chunks deliberately do not align with PART_SIZE: the provider has to
        # accumulate across them rather than assume one chunk is one part.
        chunks=_stream(*[payload[i : i + 700_000] for i in range(0, len(payload), 700_000)]),
        content_type="application/pdf",
    )

    assert storage.s3.created_multipart is True
    assert storage.s3.put_object_body is None

    # Every part but the last is exactly PART_SIZE — S3 rejects a completed upload
    # whose non-final parts are under 5 MiB.
    assert [len(part) for part in storage.s3.parts] == [PART_SIZE, 1024]
    assert b"".join(storage.s3.parts) == payload

    assert storage.s3.completed == [
        {"ETag": '"part-1"', "PartNumber": 1},
        {"ETag": '"part-2"', "PartNumber": 2},
    ]
    assert stored.size == len(payload)


async def test_nothing_is_buffered_beyond_one_part(storage: RecordingR2):
    """Parts are flushed as they form, so several parts' worth never accumulates."""
    payload = b"b" * (PART_SIZE * 3)

    await storage.put_stream(
        key="tenant_x/bigger.pdf",
        chunks=_stream(payload),
        content_type="application/pdf",
    )

    assert [len(part) for part in storage.s3.parts] == [PART_SIZE, PART_SIZE, PART_SIZE]


async def test_a_failing_stream_aborts_the_multipart_upload(storage: RecordingR2):
    """Abandoned parts are invisible in a listing and billed until something sweeps them.

    This is the path the size cap takes: the meter raises mid-stream, and the upload
    must not be left half-open.
    """

    async def failing() -> AsyncIterator[bytes]:
        yield b"c" * PART_SIZE
        raise RuntimeError("upload limit exceeded")

    with pytest.raises(RuntimeError):
        await storage.put_stream(
            key="tenant_x/doomed.pdf",
            chunks=failing(),
            content_type="application/pdf",
        )

    assert storage.s3.aborted is True
    assert storage.s3.completed is None


async def test_a_failure_before_any_part_needs_no_abort(storage: RecordingR2):
    """There is no multipart upload to abort, and asking S3 to abort one would error."""

    async def failing() -> AsyncIterator[bytes]:
        yield b"tiny"
        raise RuntimeError("client went away")

    with pytest.raises(RuntimeError):
        await storage.put_stream(
            key="tenant_x/doomed.pdf",
            chunks=failing(),
            content_type="application/pdf",
        )

    assert storage.s3.aborted is False
    assert storage.s3.put_object_body is None
