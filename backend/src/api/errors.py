"""The base domain error — introduced in Phase 6.

Phase 4 gave authentication its own error hierarchy carrying the status code and the
body the client sees, mapped to HTTP in exactly one place. Phase 6 needs the same thing
for documents, and two parallel hierarchies would mean two handlers that can disagree
about the response shape.

So the base moves here and ``AuthError`` becomes one of its subclasses. Starlette looks
an exception handler up by walking the exception's MRO, which means a single handler
registered for ``APIError`` serves every domain error in the system — including ones
added by later phases that never touch ``api.main``.

The rule these errors exist to hold is unchanged: a service raises meaning, and only
the handler knows HTTP.
"""

from __future__ import annotations


class APIError(Exception):
    """A domain failure with a status code and a client-facing message.

    ``detail`` is what the client reads. ``reason`` is what the log records. They are
    deliberately allowed to differ — credential failures return one uninformative body
    while the log still says which check failed — and the split is what makes that
    possible without a second exception type per case.
    """

    status_code: int = 400
    detail: str = "Request could not be processed"

    def __init__(self, detail: str | None = None, *, reason: str | None = None) -> None:
        self.detail = detail or type(self).detail
        self.reason = reason or type(self).__name__
        super().__init__(self.detail)
