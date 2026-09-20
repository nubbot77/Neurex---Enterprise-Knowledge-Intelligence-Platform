"""Document management over the real HTTP surface — Phase 6.

Everything here goes through the API with the real service, the real repositories and
the real RBAC machinery; only the bytes' destination is swapped for an in-memory
provider. That is what makes these tests worth writing: the interesting failures in
this phase are disagreements *between* layers — a route that reads a row the
repository would not have returned, a deduplicated upload that leaves an orphan behind,
a soft delete that quietly destroys the bytes a citation points at.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest

from helpers import add_member, create_team, register

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"
PDF_REVISED = b"%PDF-1.7\n1 0 obj\n<< /Revised true >>\nendobj\ntrailer\n%%EOF\n"
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"


async def upload(
    client,
    actor,
    org: uuid.UUID,
    *,
    content: bytes = PDF,
    filename: str = "handbook.pdf",
    content_type: str = "application/pdf",
    title: str | None = None,
):
    return await client.post(
        f"/api/v1/orgs/{org}/documents",
        files={"file": (filename, content, content_type)},
        data={"title": title} if title else None,
        headers=actor.headers,
    )


async def upload_version(
    client,
    actor,
    org: uuid.UUID,
    document_id: str,
    *,
    content: bytes,
    filename: str = "handbook.pdf",
):
    return await client.post(
        f"/api/v1/orgs/{org}/documents/{document_id}/versions",
        files={"file": (filename, content, "application/pdf")},
        headers=actor.headers,
    )


@pytest.fixture
async def admin_org(client):
    """A registered admin and the team organization they own."""
    admin = await register(client)
    org = await create_team(client, admin, name="Documented Ltd")
    return admin, org


# -- upload -------------------------------------------------------------------


async def test_upload_stores_the_object_and_records_the_row(client, storage, admin_org):
    admin, org = admin_org

    response = await upload(client, admin, org, title="Employee Handbook")
    assert response.status_code == 201, response.text

    body = response.json()
    document, version = body["document"], body["version"]

    assert document["title"] == "Employee Handbook"
    assert document["status"] == "uploaded"
    assert document["current_version"] == 1
    assert document["created_by"] == str(admin.user_id)

    assert version["version_number"] == 1
    assert version["file_size"] == len(PDF)
    assert version["mime_type"] == "application/pdf"
    assert version["original_filename"] == "handbook.pdf"
    assert version["content_hash"] == hashlib.sha256(PDF).hexdigest()

    # Phase 7 fills this in. Declared now so its arrival is not a breaking change.
    assert body["job_id"] is None
    assert body["deduplicated"] is False

    # Architecture §8: the tenant is the first path segment, and the bytes that
    # arrived are the bytes that were stored.
    key = f"tenant_{org}/documents/{document['id']}/versions/v1/source.pdf"
    assert storage.objects[key] == PDF


async def test_the_title_defaults_to_the_filename(client, admin_org):
    admin, org = admin_org
    response = await upload(client, admin, org, filename="q3-report.pdf")
    assert response.json()["document"]["title"] == "q3-report.pdf"


async def test_a_member_may_upload(client, admin_org):
    """``document:create`` is in the member matrix (§7.6) — uploading is ordinary work."""
    admin, org = admin_org
    member, _ = await add_member(client, admin, org)

    response = await upload(client, member, org)
    assert response.status_code == 201, response.text


async def test_a_path_in_the_filename_does_not_escape_the_tenant_prefix(client, storage, admin_org):
    """The key is built from ids. The client's filename never contributes to it."""
    admin, org = admin_org

    response = await upload(client, admin, org, filename="../../../../etc/passwd.pdf")
    assert response.status_code == 201, response.text

    assert response.json()["version"]["original_filename"] == "passwd.pdf"
    assert all(key.startswith(f"tenant_{org}/") for key in storage.objects)


# -- validation ---------------------------------------------------------------


async def test_an_executable_named_pdf_is_refused_and_stores_nothing(client, storage, admin_org):
    """Task 5's whole reason for existing."""
    admin, org = admin_org

    response = await upload(client, admin, org, content=EXE)

    assert response.status_code == 415
    assert storage.objects == {}


async def test_an_unsupported_extension_is_refused(client, storage, admin_org):
    admin, org = admin_org

    response = await upload(
        client, admin, org, content=EXE, filename="payload.exe", content_type=""
    )

    assert response.status_code == 415
    assert storage.objects == {}


async def test_a_contradictory_content_type_is_refused(client, admin_org):
    admin, org = admin_org
    response = await upload(client, admin, org, content_type="image/png")
    assert response.status_code == 415


async def test_an_empty_file_is_refused(client, storage, admin_org):
    """An empty document produces no chunks and no answers; it fails here, loudly."""
    admin, org = admin_org

    response = await upload(client, admin, org, content=b"")

    assert response.status_code == 422
    assert storage.objects == {}


async def test_a_file_over_the_cap_is_refused_and_leaves_nothing_behind(
    client, storage, settings, admin_org, monkeypatch
):
    """The cap is enforced against bytes read, so the check does not trust the client.

    ``monkeypatch`` on the cached settings object rather than the environment: the
    route's guard and the service both resolve ``get_settings()`` to this instance.
    """
    admin, org = admin_org
    monkeypatch.setattr(settings, "max_upload_bytes", 32)

    response = await upload(client, admin, org, content=PDF + b"x" * 1024)

    assert response.status_code == 413
    assert storage.objects == {}


# -- deduplication — Task 6 ---------------------------------------------------


async def test_the_same_bytes_twice_store_one_object(client, storage, admin_org):
    admin, org = admin_org

    first = await upload(client, admin, org, title="Handbook")
    second = await upload(client, admin, org, title="Handbook (copy)")

    assert second.status_code == 201
    assert second.json()["deduplicated"] is True
    assert second.json()["document"]["id"] == first.json()["document"]["id"]

    # The duplicate was uploaded, found to be a duplicate, and removed again — the
    # hash is not knowable before the bytes have been read.
    assert len(storage.objects) == 1
    assert len(storage.deleted) == 1


async def test_deduplication_does_not_cross_organizations(client, storage, admin_org):
    """Invariant 2. A global hash index would leak one tenant's document to another."""
    admin, org = admin_org
    await upload(client, admin, org)

    other = await register(client)
    other_org = await create_team(client, other, name="Somebody Else Inc")
    response = await upload(client, other, other_org)

    assert response.status_code == 201
    assert response.json()["deduplicated"] is False
    assert len(storage.objects) == 2


async def test_re_uploading_deleted_content_creates_a_new_document(client, admin_org):
    """A soft-deleted match is not a duplicate: nothing would show the caller that row."""
    admin, org = admin_org
    first = await upload(client, admin, org)
    document_id = first.json()["document"]["id"]

    deleted = await client.delete(
        f"/api/v1/orgs/{org}/documents/{document_id}", headers=admin.headers
    )
    assert deleted.status_code == 204

    again = await upload(client, admin, org)
    assert again.status_code == 201
    assert again.json()["deduplicated"] is False
    assert again.json()["document"]["id"] != document_id


# -- versions -----------------------------------------------------------------


async def test_a_revision_adds_a_version_and_keeps_the_old_one(client, storage, admin_org):
    """Architecture §9: a citation generated from v1 must still resolve to v1."""
    admin, org = admin_org
    document_id = (await upload(client, admin, org)).json()["document"]["id"]

    revised = await upload_version(client, admin, org, document_id, content=PDF_REVISED)
    assert revised.status_code == 201, revised.text
    assert revised.json()["version"]["version_number"] == 2
    assert revised.json()["document"]["current_version"] == 2

    versions = await client.get(
        f"/api/v1/orgs/{org}/documents/{document_id}/versions", headers=admin.headers
    )
    assert [v["version_number"] for v in versions.json()["items"]] == [1, 2]

    v1 = await client.get(
        f"/api/v1/orgs/{org}/documents/{document_id}/versions/1/download", headers=admin.headers
    )
    assert v1.content == PDF

    current = await client.get(
        f"/api/v1/orgs/{org}/documents/{document_id}/download", headers=admin.headers
    )
    assert current.content == PDF_REVISED


async def test_re_uploading_the_current_bytes_is_a_no_op(client, storage, admin_org):
    admin, org = admin_org
    document_id = (await upload(client, admin, org)).json()["document"]["id"]
    stored_before = dict(storage.objects)

    again = await upload_version(client, admin, org, document_id, content=PDF)

    assert again.json()["deduplicated"] is True
    assert again.json()["version"]["version_number"] == 1
    assert storage.objects == stored_before


async def test_a_version_number_that_does_not_exist_is_404(client, admin_org):
    admin, org = admin_org
    document_id = (await upload(client, admin, org)).json()["document"]["id"]

    response = await client.get(
        f"/api/v1/orgs/{org}/documents/{document_id}/versions/7/download", headers=admin.headers
    )
    assert response.status_code == 404


# -- metadata, listing, rename ------------------------------------------------


async def test_listing_returns_this_organizations_documents(client, admin_org):
    """Both documents, and a total that counts the whole organization.

    Order is **not** asserted here. ``created_at`` defaults to ``now()``, which
    PostgreSQL resolves to the transaction start time, and the whole suite runs inside
    one outer transaction (see the ``connection`` fixture) — so every row written by a
    test shares one timestamp and "newest first" has nothing to sort by. The ordering
    itself is covered in ``test_document_repository.py`` with explicit timestamps.
    """
    admin, org = admin_org
    await upload(client, admin, org, title="First")
    await upload(client, admin, org, content=PDF_REVISED, title="Second")

    response = await client.get(f"/api/v1/orgs/{org}/documents", headers=admin.headers)

    body = response.json()
    assert body["total"] == 2
    assert body["count"] == 2
    assert {item["title"] for item in body["items"]} == {"First", "Second"}


async def test_rename_changes_the_title_and_nothing_else(client, admin_org):
    admin, org = admin_org
    uploaded = (await upload(client, admin, org)).json()
    document_id = uploaded["document"]["id"]

    response = await client.patch(
        f"/api/v1/orgs/{org}/documents/{document_id}",
        json={"title": "Staff Handbook 2026"},
        headers=admin.headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Staff Handbook 2026"
    assert response.json()["current_version"] == 1


# -- download -----------------------------------------------------------------


async def test_download_returns_the_bytes_with_the_original_filename(client, admin_org):
    admin, org = admin_org
    document_id = (await upload(client, admin, org)).json()["document"]["id"]

    response = await client.get(
        f"/api/v1/orgs/{org}/documents/{document_id}/download", headers=admin.headers
    )

    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"].startswith("application/pdf")
    assert "handbook.pdf" in response.headers["content-disposition"]
    # One organization's private content must not be cached by anything in between.
    assert response.headers["cache-control"] == "private, no-store"


# -- delete -------------------------------------------------------------------


async def test_delete_hides_the_document_but_keeps_the_bytes(client, storage, admin_org):
    """Soft delete: a citation from Phase 19 points at a version that still resolves."""
    admin, org = admin_org
    document_id = (await upload(client, admin, org)).json()["document"]["id"]
    keys_before = set(storage.objects)

    response = await client.delete(
        f"/api/v1/orgs/{org}/documents/{document_id}", headers=admin.headers
    )
    assert response.status_code == 204

    gone = await client.get(f"/api/v1/orgs/{org}/documents/{document_id}", headers=admin.headers)
    assert gone.status_code == 404

    listed = await client.get(f"/api/v1/orgs/{org}/documents", headers=admin.headers)
    assert listed.json()["total"] == 0

    assert set(storage.objects) == keys_before


async def test_a_member_may_not_delete_a_document(client, admin_org):
    """``document:delete`` is admin-only in the §7.6 matrix."""
    admin, org = admin_org
    member, _ = await add_member(client, admin, org)
    document_id = (await upload(client, admin, org)).json()["document"]["id"]

    response = await client.delete(
        f"/api/v1/orgs/{org}/documents/{document_id}", headers=member.headers
    )

    assert response.status_code == 403


# -- isolation — Task 10 ------------------------------------------------------


async def test_another_organizations_document_is_not_reachable_by_id(client, admin_org):
    """Invariant 2, on every document route that takes an id."""
    victim, victim_org = admin_org
    document_id = (await upload(client, victim, victim_org)).json()["document"]["id"]

    attacker = await register(client)
    attacker_org = await create_team(client, attacker, name="Attacker Inc")

    # Their own organization, someone else's document id: the scoped repository
    # answers as it would for an id that does not exist anywhere.
    for path in (
        f"/api/v1/orgs/{attacker_org}/documents/{document_id}",
        f"/api/v1/orgs/{attacker_org}/documents/{document_id}/download",
        f"/api/v1/orgs/{attacker_org}/documents/{document_id}/versions",
    ):
        response = await client.get(path, headers=attacker.headers)
        assert response.status_code == 404, path

    # The victim's own organization id in the path is refused earlier still, by
    # context resolution, with the same 404 (§7.8).
    response = await client.get(
        f"/api/v1/orgs/{victim_org}/documents/{document_id}", headers=attacker.headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"


async def test_an_outsider_cannot_delete_or_revise_another_tenants_document(client, admin_org):
    victim, victim_org = admin_org
    document_id = (await upload(client, victim, victim_org)).json()["document"]["id"]

    attacker = await register(client)

    deleted = await client.delete(
        f"/api/v1/orgs/{victim_org}/documents/{document_id}", headers=attacker.headers
    )
    assert deleted.status_code == 404

    revised = await upload_version(client, attacker, victim_org, document_id, content=PDF_REVISED)
    assert revised.status_code == 404

    # Still there, still theirs, still version 1.
    intact = await client.get(
        f"/api/v1/orgs/{victim_org}/documents/{document_id}", headers=victim.headers
    )
    assert intact.status_code == 200
    assert intact.json()["current_version"] == 1
