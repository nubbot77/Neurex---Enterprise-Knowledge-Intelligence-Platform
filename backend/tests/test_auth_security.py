"""Phase 4, Task 10 — attack the auth system deliberately.

Auth bugs are silent. Nothing crashes, no alert fires, the wrong people simply get in.
These tests are the only thing that makes such a failure loud, so every one of them
forges something a real attacker would forge.
"""

from __future__ import annotations

import base64
import json
import statistics
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import update

from api.auth.password import DUMMY_HASH, hash_password, needs_rehash, verify_password
from api.models.user import User

PASSWORD = "correct-horse-battery-staple"


def _email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


async def _register(client, email: str | None = None):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email or _email(), "password": PASSWORD, "full_name": "Ada Lovelace"},
    )
    return response.json()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


# -- password hashing ------------------------------------------------------


def test_hash_is_argon2id_and_salted():
    first = hash_password(PASSWORD)
    second = hash_password(PASSWORD)

    assert first.startswith("$argon2id$")
    # A random salt per hash is what makes rainbow tables useless.
    assert first != second
    assert verify_password(PASSWORD, first)
    assert verify_password(PASSWORD, second)


def test_wrong_password_does_not_verify():
    assert not verify_password("not-the-password", hash_password(PASSWORD))


def test_corrupt_hash_returns_false_rather_than_raising():
    # A malformed stored hash must read as "login failed", not as a distinct error —
    # a different failure mode would leak that the account exists.
    assert not verify_password(PASSWORD, "not-a-hash")


def test_current_parameters_do_not_need_rehashing():
    assert not needs_rehash(hash_password(PASSWORD))


# -- token forgery ---------------------------------------------------------


async def test_missing_header_is_rejected(client):
    response = await client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["detail"] == "Not authenticated"


async def test_non_bearer_scheme_is_rejected(client):
    response = await client.get("/api/v1/me", headers={"Authorization": "Basic YWRhOnB3"})

    assert response.status_code == 401


async def test_garbage_token_is_rejected(client):
    response = await client.get("/api/v1/me", headers=_bearer("not.a.token"))

    assert response.status_code == 401


async def test_expired_token_is_rejected(client, settings):
    user_id = (await _register(client))["user"]["id"]
    past = datetime.now(UTC) - timedelta(hours=2)
    expired = jwt.encode(
        {
            "sub": user_id,
            "jti": uuid.uuid4().hex,
            "typ": "access",
            "iat": int(past.timestamp()),
            "exp": int((past + timedelta(minutes=15)).timestamp()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/api/v1/me", headers=_bearer(expired))

    assert response.status_code == 401


async def test_tampered_payload_is_rejected(client):
    tokens = (await _register(client))["tokens"]
    header, payload, signature = tokens["access_token"].split(".")
    claims = json.loads(_b64url_decode(payload))
    claims["sub"] = str(uuid.uuid4())  # become somebody else
    forged = f"{header}.{_b64url_encode(json.dumps(claims).encode())}.{signature}"

    response = await client.get("/api/v1/me", headers=_bearer(forged))

    assert response.status_code == 401


async def test_token_signed_with_another_secret_is_rejected(client, settings):
    user_id = (await _register(client))["user"]["id"]
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": user_id,
            "jti": uuid.uuid4().hex,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        },
        "attacker-key",
        algorithm="HS256",
    )

    response = await client.get("/api/v1/me", headers=_bearer(forged))

    assert response.status_code == 401


async def test_alg_none_token_is_rejected(client):
    """The classic JWT attack: claim the token is unsigned and drop the signature."""
    user_id = (await _register(client))["user"]["id"]
    now = datetime.now(UTC)
    header = _b64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url_encode(
        json.dumps(
            {
                "sub": user_id,
                "jti": uuid.uuid4().hex,
                "typ": "access",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=15)).timestamp()),
            }
        ).encode()
    )

    response = await client.get("/api/v1/me", headers=_bearer(f"{header}.{payload}."))

    assert response.status_code == 401


async def test_token_missing_required_claims_is_rejected(client, settings):
    """No ``typ`` means nothing stops a token being used in the wrong place."""
    now = datetime.now(UTC)
    thin = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": int((now + timedelta(minutes=5)).timestamp())},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/api/v1/me", headers=_bearer(thin))

    assert response.status_code == 401


# -- token type confusion --------------------------------------------------


async def test_refresh_token_cannot_be_used_as_an_access_token(client):
    tokens = (await _register(client))["tokens"]

    response = await client.get("/api/v1/me", headers=_bearer(tokens["refresh_token"]))

    assert response.status_code == 401


async def test_access_token_cannot_be_used_to_refresh(client):
    tokens = (await _register(client))["tokens"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401


# -- revocation ------------------------------------------------------------


async def test_logout_kills_the_access_token(client):
    tokens = (await _register(client))["tokens"]

    await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_bearer(tokens["access_token"]),
    )
    response = await client.get("/api/v1/me", headers=_bearer(tokens["access_token"]))

    assert response.status_code == 401


async def test_logout_kills_the_refresh_token_too(client):
    """Otherwise a seven-day credential survives in storage the user just cleared."""
    tokens = (await _register(client))["tokens"]

    await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=_bearer(tokens["access_token"]),
    )
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 401


async def test_rotated_refresh_token_cannot_be_reused(client):
    tokens = (await _register(client))["tokens"]
    await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 401


async def test_refresh_reuse_revokes_every_session_for_that_user(client):
    """Two parties hold the same token and the server cannot tell which is knocking."""
    tokens = (await _register(client))["tokens"]
    fresh = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).json()

    # The thief (or the legitimate client) replays the spent token.
    replay = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert replay.status_code == 401
    # The pair handed out a moment ago is dead too.
    assert (
        await client.get("/api/v1/me", headers=_bearer(fresh["access_token"]))
    ).status_code == 401
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": fresh["refresh_token"]})
    ).status_code == 401


async def test_logout_all_kills_other_sessions(client):
    email = _email()
    first = (await _register(client, email))["tokens"]
    second = (
        await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    ).json()

    await client.post("/api/v1/auth/logout-all", headers=_bearer(second["access_token"]))

    assert (
        await client.get("/api/v1/me", headers=_bearer(first["access_token"]))
    ).status_code == 401
    assert (
        await client.get("/api/v1/me", headers=_bearer(second["access_token"]))
    ).status_code == 401


# -- account state ---------------------------------------------------------


async def test_deactivated_account_is_rejected_before_its_token_expires(client, session):
    """The reason ``get_current_user`` still reads the database on every request."""
    body = await _register(client)
    await session.execute(
        update(User).where(User.id == uuid.UUID(body["user"]["id"])).values(is_active=False)
    )
    await session.commit()

    response = await client.get("/api/v1/me", headers=_bearer(body["tokens"]["access_token"]))

    assert response.status_code == 401


async def test_deleted_user_token_is_rejected(client, settings):
    """A signature proves issuance, not that the subject still exists."""
    now = datetime.now(UTC)
    orphan = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "jti": uuid.uuid4().hex,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get("/api/v1/me", headers=_bearer(orphan))

    assert response.status_code == 401


async def test_deactivated_account_cannot_log_in(client, session):
    email = _email()
    body = await _register(client, email)
    await session.execute(
        update(User).where(User.id == uuid.UUID(body["user"]["id"])).values(is_active=False)
    )
    await session.commit()

    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 401


# -- credential handling ---------------------------------------------------


async def test_wrong_password_and_unknown_email_are_indistinguishable(client):
    email = _email()
    await _register(client, email)

    wrong_password = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password-entirely"}
    )
    unknown_email = await client.post(
        "/api/v1/auth/login", json={"email": _email(), "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_login_never_echoes_the_password(client):
    email = _email()
    await _register(client, email)

    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})

    assert PASSWORD not in response.text
    assert "$argon2" not in response.text


def test_dummy_hash_is_a_real_argon2_hash():
    """The timing defence only works if the dummy costs what a real verify costs."""
    assert DUMMY_HASH.startswith("$argon2id$")
    assert not verify_password(PASSWORD, DUMMY_HASH)


@pytest.mark.slow
async def test_unknown_email_takes_as_long_as_a_wrong_password(client):
    """Enumeration by stopwatch.

    Returning early for an unknown account answers in about a millisecond while a wrong
    password costs a full Argon2 verify. Asserted on medians over several runs, not on
    one pair of timings, because a single sample is mostly scheduler noise.
    """
    email = _email()
    await _register(client, email)

    async def timed(payload: dict[str, str]) -> float:
        start = time.perf_counter()
        await client.post("/api/v1/auth/login", json=payload)
        return time.perf_counter() - start

    known = statistics.median(
        [await timed({"email": email, "password": "wrong-password"}) for _ in range(5)]
    )
    unknown = statistics.median(
        [await timed({"email": _email(), "password": "wrong-password"}) for _ in range(5)]
    )

    # Both paths run one Argon2 verify, so neither should be close to free.
    assert min(known, unknown) > 0.4 * max(known, unknown)
