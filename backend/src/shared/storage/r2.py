"""Cloudflare R2, through the S3 API — Phase 6, Task 2.

R2 speaks S3, so this is an ordinary S3 client pointed at an account-specific endpoint
with ``region_name="auto"``. Nothing above ``StorageProvider`` knows that.

The only non-obvious part is ``put_stream``, which is where "a 500MB upload must not
become a 500MB allocation" is actually delivered:

- Chunks accumulate in one buffer. While it stays under ``PART_SIZE`` the object goes
  up in a single ``put_object`` — the common case, one request.
- The moment it crosses ``PART_SIZE`` the upload switches to S3 multipart and flushes
  full parts as they form, so memory stays bounded by one part regardless of file size.
- Anything raising mid-stream aborts the multipart upload. Parts left behind by an
  abandoned upload are invisible in a bucket listing and are billed until a lifecycle
  rule sweeps them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import aioboto3
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError

from api.config.settings import Settings
from shared.storage.base import (
    DOWNLOAD_CHUNK_SIZE,
    PART_SIZE,
    ObjectNotFound,
    StorageError,
    StorageProvider,
    StoredObject,
)

logger = structlog.get_logger(__name__)

# Status codes R2/S3 use for "that key is not here". head_object answers 404 with no
# error code, get_object answers NoSuchKey — both have to be caught.
_MISSING = {"404", "NoSuchKey", "NotFound"}


class R2Storage(StorageProvider):
    """S3-compatible object storage.

    A client is opened per operation rather than held for the process lifetime.
    ``aioboto3`` clients are async context managers over an aiohttp session, and a
    single long-lived client shared across requests is not obviously safe to reuse
    across event-loop lifecycles. Creation costs about a millisecond and no network
    round trip; if that shows up in a profile, Phase 28 is where it gets fixed, with a
    measurement rather than a guess.
    """

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "auto",
    ) -> None:
        if not bucket or not endpoint_url:
            raise StorageError("R2Storage needs a bucket and an endpoint url")

        self.bucket = bucket
        self._endpoint_url = endpoint_url
        self._session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        # R2 does not implement request checksums the way S3 does; botocore's newer
        # defaults send them on every request and R2 rejects some of those. Asking for
        # SigV4 and leaving retries at the standard mode keeps the client on the subset
        # R2 documents as supported.
        self._config = Config(signature_version="s3v4", retries={"max_attempts": 3})

    @classmethod
    def from_settings(cls, settings: Settings) -> R2Storage:
        return cls(
            bucket=settings.storage_bucket,
            endpoint_url=settings.storage_endpoint_url,
            access_key_id=settings.storage_access_key_id,
            secret_access_key=settings.storage_secret_access_key,
            region=settings.storage_region,
        )

    def _client(self) -> Any:
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            config=self._config,
        )

    # -- writes ------------------------------------------------------------

    async def put_stream(
        self,
        *,
        key: str,
        chunks: AsyncIterator[bytes],
        content_type: str,
    ) -> StoredObject:
        buffer = bytearray()
        total = 0
        upload_id: str | None = None
        parts: list[dict[str, Any]] = []

        async with self._client() as s3:
            try:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    buffer.extend(chunk)
                    total += len(chunk)

                    if len(buffer) < PART_SIZE:
                        continue

                    if upload_id is None:
                        created = await s3.create_multipart_upload(
                            Bucket=self.bucket,
                            Key=key,
                            ContentType=content_type,
                        )
                        upload_id = created["UploadId"]

                    while len(buffer) >= PART_SIZE:
                        body = bytes(buffer[:PART_SIZE])
                        del buffer[:PART_SIZE]
                        parts.append(
                            await self._upload_part(
                                s3,
                                key=key,
                                upload_id=upload_id,
                                number=len(parts) + 1,
                                body=body,
                            )
                        )

                if upload_id is None:
                    # Never grew past one part: a single request, and the whole object
                    # is at most PART_SIZE in memory.
                    written = await s3.put_object(
                        Bucket=self.bucket,
                        Key=key,
                        Body=bytes(buffer),
                        ContentType=content_type,
                    )
                    return StoredObject(
                        key=key,
                        size=total,
                        content_type=content_type,
                        etag=written.get("ETag"),
                    )

                if buffer:
                    parts.append(
                        await self._upload_part(
                            s3,
                            key=key,
                            upload_id=upload_id,
                            number=len(parts) + 1,
                            body=bytes(buffer),
                        )
                    )

                completed = await s3.complete_multipart_upload(
                    Bucket=self.bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
                return StoredObject(
                    key=key,
                    size=total,
                    content_type=content_type,
                    etag=completed.get("ETag"),
                )

            except BaseException:
                # BaseException, not Exception: a cancelled request must clean up too,
                # and cancellation is exactly when an upload is most likely to be
                # abandoned mid-flight.
                if upload_id is not None:
                    await self._abort(s3, key=key, upload_id=upload_id)
                raise

    async def _upload_part(
        self,
        s3: Any,
        *,
        key: str,
        upload_id: str,
        number: int,
        body: bytes,
    ) -> dict[str, Any]:
        written = await s3.upload_part(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            PartNumber=number,
            Body=body,
        )
        return {"ETag": written["ETag"], "PartNumber": number}

    async def _abort(self, s3: Any, *, key: str, upload_id: str) -> None:
        try:
            await s3.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)
        except ClientError:
            # The original failure is what the caller needs to see. A failed abort is
            # logged so the orphaned parts can be swept, and swallowed so it cannot
            # replace the real exception on its way out.
            logger.error("storage.multipart_abort_failed", key=key, upload_id=upload_id)

    # -- reads -------------------------------------------------------------

    async def open_stream(
        self,
        key: str,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        async with self._client() as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
            except ClientError as error:
                raise self._translate(error, key) from error

            async for chunk in response["Body"].iter_chunks(chunk_size):
                yield chunk

    async def exists(self, key: str) -> bool:
        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
            except ClientError as error:
                if _is_missing(error):
                    return False
                raise StorageError(f"head_object failed for {key}") from error
            return True

    async def delete(self, key: str) -> None:
        async with self._client() as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
            except ClientError as error:
                if _is_missing(error):
                    return
                raise StorageError(f"delete_object failed for {key}") from error

    # -- administration ----------------------------------------------------

    async def ensure_bucket(self) -> bool:
        """Create the bucket if it is missing. Returns True when it created one.

        Deliberately **not** on ``StorageProvider``: the interface is what the API is
        written against, and an API that can create buckets is an API whose
        credentials can create buckets. This is here for ``scripts/ensure_bucket.py``,
        run by a person on a fresh machine, and is called by nothing on a request path.
        """
        async with self._client() as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
            except ClientError as error:
                if not _is_missing(error):
                    raise
                await s3.create_bucket(Bucket=self.bucket)
                return True
            return False

    async def presigned_url(self, key: str, *, expires_in: int = 300) -> str:
        async with self._client() as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )

    # -- internals ---------------------------------------------------------

    def _translate(self, error: ClientError, key: str) -> StorageError:
        if _is_missing(error):
            return ObjectNotFound(key)
        return StorageError(f"storage request failed for {key}")


def _is_missing(error: ClientError) -> bool:
    response = error.response or {}
    code = str(response.get("Error", {}).get("Code", ""))
    status = str(response.get("ResponseMetadata", {}).get("HTTPStatusCode", ""))
    return code in _MISSING or status == "404"
