"""Password hashing — Phase 4, Task 1.

Passwords are never stored, not even encrypted: encryption is reversible by whoever
holds the key, so a database dump plus a leaked key would expose every account. What
goes in ``users.password_hash`` is a one-way Argon2id hash.

Argon2id is deliberately slow and memory-hungry (roughly 50-100 ms and 64 MiB per
attempt with the library defaults). That is unnoticeable once at login and ruinous for
an attacker doing it a billion times on a GPU, which is exactly why a fast hash like
SHA-256 is the wrong tool here.
"""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Library defaults: argon2id, m=65536 (64 MiB), t=3, p=4. They are the maintained
# recommendation and are encoded into every hash string, so raising them later needs no
# migration — old hashes still describe how they were made.
_hasher = PasswordHasher()

# Used when the account does not exist, so login spends the same time either way.
# Computed once at import rather than per request. See ``auth_service.login``.
DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))


def hash_password(plain: str) -> str:
    """Hash a plaintext password.

    The returned string is self-describing — variant, version, parameters, salt and
    digest — for example::

        $argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG

    The salt is random per password, so two people who chose the same password get
    different hashes and precomputed rainbow tables are worthless.
    """
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a password against a stored hash.

    Returns ``False`` rather than raising, including for a corrupt or non-Argon2 hash:
    the caller's job is to reject the login, and a distinct exception for "this row's
    hash is malformed" would leak that the account exists.
    """
    try:
        _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True


def needs_rehash(hashed: str) -> bool:
    """True when the stored hash was made with weaker parameters than current ones.

    Login is the only moment the plaintext is available, so it is the only moment a
    hash can be upgraded. Call this after a successful verify.
    """
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        # Unreadable hash — treat as needing replacement rather than crashing a login
        # that has already been verified against it (it cannot have been).
        return True
