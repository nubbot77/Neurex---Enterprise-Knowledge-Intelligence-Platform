"""Domain errors for authentication.

These are raised by the service and the auth helpers, never by the repository, and are
mapped to HTTP status codes once in ``api.main``. Keeping them out of the service means
the service can be tested without HTTP, and keeping the mapping in one place means the
status code for "bad credentials" cannot drift between routes.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base class. Carries the status and the body the client will see."""

    status_code: int = 401
    detail: str = "Could not validate credentials"

    def __init__(self, detail: str | None = None, *, reason: str | None = None) -> None:
        # ``detail`` is what the client reads. ``reason`` is what the log records — the
        # two are deliberately different for credential failures, so the response stays
        # uninformative while the log stays useful.
        self.detail = detail or type(self).detail
        self.reason = reason or type(self).__name__
        super().__init__(self.detail)


class InvalidCredentials(AuthError):
    """Wrong password, unknown email, or a disabled account.

    One error for all three on purpose. "No account with that email" is a free
    account-existence check for anyone holding a wordlist.
    """

    status_code = 401
    detail = "Incorrect email or password"


class InvalidToken(AuthError):
    """Signature, expiry, type or revocation check failed.

    Every cause returns the same body; only ``reason`` distinguishes them in the log.
    """

    status_code = 401
    detail = "Could not validate credentials"


class TokenReused(AuthError):
    """A refresh token was presented twice.

    Rotation kills a refresh token on use, so a second presentation means two parties
    hold it. The system cannot tell which one is the thief, so every session for that
    user is revoked and both parties must log in again.
    """

    status_code = 401
    detail = "Session ended for security reasons. Please sign in again."


class NotAuthenticated(AuthError):
    """No credentials were supplied at all."""

    status_code = 401
    detail = "Not authenticated"


class EmailAlreadyRegistered(AuthError):
    """Registration hit the unique constraint on ``users.email``.

    Unlike login, registration cannot hide that an account exists — the user has to be
    told why the form failed. The mitigation is rate limiting, not vagueness.
    """

    status_code = 409
    detail = "That email is already registered"
