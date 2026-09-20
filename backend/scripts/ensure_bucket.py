"""Create the storage bucket if it is missing — Phase 6.

    cd backend
    uv run python scripts/ensure_bucket.py

Nothing in the application creates a bucket, and nothing should: an API process that
can create buckets is an API process whose credentials can create buckets, and the one
that matters already exists in every environment but a fresh laptop. So this is a
script, run once by a person.

It reads the same ``STORAGE_*`` settings the app does and goes through the same
``R2Storage`` provider, so a misconfiguration fails here — with a readable message —
rather than at the first upload. Idempotent: an existing bucket is reported and left
alone.

Works against the local MinIO and against Cloudflare R2. On R2 the bucket is usually
created in the dashboard, and running this is then a credentials check rather than a
creation.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Run by a person from the shell, not by the app, so src/ is not on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from botocore.exceptions import ClientError, EndpointConnectionError  # noqa: E402

from api.config.settings import get_settings  # noqa: E402
from shared.storage.r2 import R2Storage  # noqa: E402


async def main() -> int:
    settings = get_settings()

    if not settings.storage_bucket or not settings.storage_endpoint_url:
        print("STORAGE_BUCKET and STORAGE_ENDPOINT_URL are empty in backend/.env.")
        print("The API boots without them, but every document route answers 503.")
        return 1

    storage = R2Storage.from_settings(settings)
    print(f"endpoint: {settings.storage_endpoint_url}")
    print(f"bucket:   {settings.storage_bucket}")

    try:
        created = await storage.ensure_bucket()
    except EndpointConnectionError:
        print(f"\nCannot reach {settings.storage_endpoint_url}.")
        print("If this is the local MinIO: docker compose up -d minio")
        return 1
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "")
        # A 403 here is almost always the access key or the secret, not the name.
        print(f"\nRefused by the storage service: {code or error}")
        return 1

    print("created." if created else "already exists - nothing to do.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
