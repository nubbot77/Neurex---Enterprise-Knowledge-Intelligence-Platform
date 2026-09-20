"""Domain errors for authentication.

These are raised by the service and the auth helpers, never by the repository, and are
mapped to HTTP status codes once in ``api.main``. Keeping them out of the service means
the service can be tested without HTTP, and keeping the mapping in one place means the
status code for "bad credentials" cannot drift between routes.
"""

from __future__ import annotations

from api.errors import APIError


class AuthError(APIError):
    """Base class for auth failures. Defaults to 401.

    The ``detail``/``reason`` split lives on ``APIError`` (Phase 6), so one handler in
    ``api.main`` maps every domain error in the system. What is kept here is the
    default status: anything raised by this hierarchy without one is a credential
    failure, and a credential failure is a 401.
    """

    status_code: int = 401
    detail: str = "Could not validate credentials"


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


# --- Authorization — Phase 5 -------------------------------------------------
#
# Authentication answers "who is this?" and fails with 401. Everything below answers
# "may they?" and fails with 403, 404 or 409. They share ``AuthError`` so the single
# handler in ``api.main`` keeps mapping status codes in one place.


class OrganizationNotFound(AuthError):
    """No organization, or no active membership in it — deliberately indistinguishable.

    Architecture §7.8. A 403 here would confirm that the organization exists, which
    leaks the existence and the id space of other tenants to anyone walking UUIDs. The
    two cases are answered identically on purpose: a user with no active membership is
    told exactly what a user asking about a nonexistent tenant is told.
    """

    status_code = 404
    detail = "Organization not found"


class PermissionDenied(AuthError):
    """Membership is established and active, but the role is insufficient.

    403 is correct here, and only here. The caller already knows the organization
    exists — they are in it — so a precise error leaks nothing and saves them guessing.
    """

    status_code = 403
    detail = "You do not have permission to perform this action"


class MembershipNotFound(AuthError):
    """The membership being operated on does not exist in this organization.

    Scoped by organization before it is looked up, so this cannot be used to probe for
    membership ids belonging to another tenant.
    """

    status_code = 404
    detail = "Membership not found"


class MembershipConflict(AuthError):
    """The membership is not in a state this operation accepts.

    Covers inviting someone who is already a member, accepting an invitation that was
    never issued, and suspending a membership that is already suspended.
    """

    status_code = 409
    detail = "That membership is not in a state this operation allows"


class PersonalOrganizationClosed(AuthError):
    """A personal workspace cannot take a second member — architecture §7.3.

    ``kind = 'personal'`` exists so that every user owns a tenant from their first
    second. Letting one grow members would give it the semantics of a team without any
    of the checks a team gets.
    """

    status_code = 409
    detail = "A personal workspace cannot have additional members"


class AdminRangeViolation(AuthError):
    """The operation would leave the organization outside its admin range.

    Architecture §7.7: at least one and at most ``max_admins`` active admins. The
    database enforces this authoritatively — a CHECK constraint for the ceiling and a
    trigger for the floor. This error exists purely so the caller sees a 409 with a
    usable message instead of a constraint violation surfaced as a 500.

    This service-layer check is a courtesy, not the guarantee. On its own it would be a
    bug: two concurrent requests can both pass it, and only the row lock the trigger
    takes decides.
    """

    status_code = 409
    detail = "That change would leave the organization outside its admin range"


class CrossTenantWriteForbidden(AuthError):
    """A super_admin bypass was asked to write — architecture §7.10.

    Cross-tenant reads are support work. Cross-tenant writes have no legitimate use and
    turn one mistaken operation into damage across several customers. The two
    exceptions, admin recovery and organization deletion, are audited operations of
    their own rather than uses of the bypass.
    """

    status_code = 403
    detail = "Cross-tenant access is read-only"
