"""Domain errors for documents — Phase 6.

Raised by the service and by file validation, never by a repository, and mapped to
HTTP once in ``api.main`` through the shared ``APIError`` handler.

Unlike the auth errors, these are allowed to be specific. The caller is an
authenticated member of the organization by the time any of them can be raised, so
saying exactly what was wrong with their upload leaks nothing and saves them guessing.
"""

from __future__ import annotations

from api.errors import APIError


class DocumentNotFound(APIError):
    """No such document in this organization.

    Covers "does not exist", "belongs to another tenant" and "was deleted" with one
    answer. The first two are indistinguishable by design — the scoped repository
    returns ``None`` for another tenant's id exactly as it does for a made-up one, and
    a distinct error would confirm the row exists.
    """

    status_code = 404
    detail = "Document not found"


class DocumentVersionNotFound(APIError):
    """The document exists, but not at that version number."""

    status_code = 404
    detail = "Document version not found"


class DocumentVersionConflict(APIError):
    """Two uploads to the same document raced for the same version number.

    The unique constraint on ``(document_id, version_number)`` decides, and whichever
    transaction loses raises this instead of surfacing an IntegrityError as a 500.
    Retrying succeeds: the next attempt reads a higher number.
    """

    status_code = 409
    detail = "Another version of this document was uploaded at the same time. Try again."


class UnsupportedFileType(APIError):
    """The extension is not on the allowlist.

    An allowlist, never a denylist: a denylist is a list of the attacks someone
    thought of, and the interesting upload is always the one nobody thought of.
    """

    status_code = 415
    detail = "That file type is not supported"


class FileContentMismatch(APIError):
    """The bytes are not what the extension claims.

    A file named ``report.pdf`` can contain anything, and both the name and the
    declared ``Content-Type`` are strings the client chose. This is raised after
    reading the leading bytes and finding they do not match the claimed format.
    """

    status_code = 415
    detail = "The file's contents do not match its extension"


class FileTooLarge(APIError):
    """The upload exceeded the configured size cap.

    413, and raised from two places: once early from the ``Content-Length`` header, and
    once definitively from the byte count taken while streaming. Only the second is a
    guarantee — the header is client-supplied — but the first is what stops a large
    body being read at all.
    """

    status_code = 413
    detail = "That file is larger than the upload limit"


class EmptyUpload(APIError):
    """Zero bytes.

    Rejected rather than stored: an empty document produces no chunks, no embeddings
    and no answers, so it would sit in the pipeline failing quietly at a later stage
    where the cause is much harder to see.
    """

    status_code = 422
    detail = "The uploaded file is empty"


class StorageNotConfigured(APIError):
    """Object storage credentials are missing, so no document route can work.

    503 rather than 500: nothing is broken, a dependency is absent, and the operator
    can fix it without a deploy. The app still boots without storage on purpose — the
    alternative takes authentication and every other phase down with it — so this is
    the one place the omission surfaces.
    """

    status_code = 503
    detail = "Document storage is not configured on this server"
