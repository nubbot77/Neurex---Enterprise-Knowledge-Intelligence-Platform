"""The happy paths — registration, login, refresh, logout.

Attacks live in ``test_auth_security.py``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from api.models.membership import Membership, MembershipRole, MembershipStatus
from api.models.organization import Organization, OrganizationKind
from api.models.user import User

PASSWORD = "correct-horse-battery-staple"


def _email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


async def _register(client, email: str | None = None, password: str = PASSWORD):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email or _email(), "password": password, "full_name": "Ada Lovelace"},
    )


async def test_register_returns_user_organization_and_tokens(client):
    response = await _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"].endswith("@example.com")
    assert body["organization_id"]
    assert body["tokens"]["token_type"] == "bearer"
    # 15 minutes, from access_token_expire_minutes.
    assert body["tokens"]["expires_in"] == 900


async def test_register_writes_three_rows_in_one_transaction(client, session):
    email = _email()

    await _register(client, email)

    user = (await session.execute(select(User).where(User.email == email))).scalar_one()
    membership = (
        await session.execute(select(Membership).where(Membership.user_id == user.id))
    ).scalar_one()
    organization = (
        await session.execute(
            select(Organization).where(Organization.id == membership.organization_id)
        )
    ).scalar_one()

    assert organization.kind is OrganizationKind.PERSONAL
    assert membership.role is MembershipRole.ADMIN
    # Not the column default: ``pending`` is for invitations, and only ``active``
    # memberships are counted by the admin-count trigger.
    assert membership.status is MembershipStatus.ACTIVE
    assert membership.joined_at is not None
    # The trigger ran inside the same transaction.
    assert organization.active_admin_count == 1


async def test_register_never_returns_the_password_or_its_hash(client):
    response = await _register(client)

    assert PASSWORD not in response.text
    assert "password" not in response.json()["user"]
    assert "$argon2" not in response.text


async def test_duplicate_email_is_rejected(client):
    email = _email()
    await _register(client, email)

    response = await _register(client, email)

    assert response.status_code == 409


async def test_email_is_normalised_to_lowercase(client):
    email = _email()
    await _register(client, email.upper())

    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200


async def test_login_returns_a_token_pair(client):
    email = _email()
    await _register(client, email)

    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


async def test_me_returns_the_caller(client):
    email = _email()
    tokens = (await _register(client, email)).json()["tokens"]

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["is_super_admin"] is False


async def test_refresh_returns_a_new_pair(client):
    tokens = (await _register(client)).json()["tokens"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    fresh = response.json()
    # Rotation: the refresh token is replaced, not reused.
    assert fresh["refresh_token"] != tokens["refresh_token"]


async def test_refreshed_access_token_works(client):
    tokens = (await _register(client)).json()["tokens"]
    fresh = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    ).json()

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {fresh['access_token']}"}
    )

    assert response.status_code == 200


async def test_logout_returns_204(client):
    tokens = (await _register(client)).json()["tokens"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 204
