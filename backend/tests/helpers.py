"""Shared fixtures-by-function for the Phase 5 suites.

Everything here goes through the real HTTP surface rather than writing rows directly.
An isolation test that sets up its world with raw INSERTs proves the repository filters
rows; going through the API proves the route, the context resolution and the repository
agree — which is where the interesting failures are.

``@example.com``, not ``@example.test``: ``pydantic[email]`` refuses special-use
domains, so a ``.test`` address returns 422 from any route taking an ``EmailStr``.
"""

from __future__ import annotations

import uuid
from typing import Any

PASSWORD = "correct-horse-battery-staple"


def an_email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


def bearer(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class Actor:
    """A registered user, their tokens and their personal organization."""

    __slots__ = ("email", "headers", "organization_id", "tokens", "user_id")

    def __init__(self, body: dict[str, Any], email: str) -> None:
        self.email = email
        self.user_id = uuid.UUID(body["user"]["id"])
        self.organization_id = uuid.UUID(body["organization_id"])
        self.tokens = body["tokens"]
        self.headers = bearer(body["tokens"])


async def register(client, email: str | None = None, full_name: str = "Ada Lovelace") -> Actor:
    address = email or an_email()
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": address, "password": PASSWORD, "full_name": full_name},
    )
    assert response.status_code == 201, response.text
    return Actor(response.json(), address)


async def create_team(client, actor: Actor, name: str = "Acme") -> uuid.UUID:
    """A team organization with ``actor`` as its first (and only) admin."""
    response = await client.post("/api/v1/orgs", json={"name": name}, headers=actor.headers)
    assert response.status_code == 201, response.text
    return uuid.UUID(response.json()["id"])


async def invite(client, admin: Actor, org_id: uuid.UUID, invitee: Actor, role: str = "member"):
    return await client.post(
        f"/api/v1/orgs/{org_id}/members",
        json={"email": invitee.email, "role": role},
        headers=admin.headers,
    )


async def accept(client, invitee: Actor, org_id: uuid.UUID):
    return await client.post(
        f"/api/v1/me/invitations/{org_id}/accept",
        headers=invitee.headers,
    )


async def add_member(
    client, admin: Actor, org_id: uuid.UUID, role: str = "member"
) -> tuple[Actor, uuid.UUID]:
    """Register someone, invite them, have them accept. Returns them and their membership id."""
    member = await register(client)
    invited = await invite(client, admin, org_id, member, role=role)
    assert invited.status_code == 201, invited.text

    accepted = await accept(client, member, org_id)
    assert accepted.status_code == 200, accepted.text
    return member, uuid.UUID(accepted.json()["id"])


async def own_membership_id(client, actor: Actor, org_id: uuid.UUID) -> uuid.UUID:
    response = await client.get("/api/v1/me/organizations", headers=actor.headers)
    assert response.status_code == 200, response.text
    for row in response.json():
        if row["organization"]["id"] == str(org_id):
            return uuid.UUID(row["membership_id"])
    raise AssertionError(f"{actor.email} has no membership in {org_id}")
