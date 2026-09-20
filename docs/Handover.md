# Handover

**Project:** Neurex — Enterprise Knowledge Intelligence Platform
**Last updated:** 2026-09-19 (Phase 6 closed)
**Progress:** Phases 0–6 complete — **7 of 34 phases**

Task list and full phase breakdown: `docs/backend_tasks.md`
Identity, tenancy and RBAC specification: `docs/architecture.md` §7
Architecture and directory structure: `docs/plan.md`

---

## 1. Where to pick up

**Next task: Phase 7, Task 1 — `shared/queue/base.py`, the `Queue` interface.**

Phase 6 is closed. A file uploads to object storage, is recorded as a `Document` plus
an immutable `DocumentVersion`, and comes back out by streaming download. Nothing reads
the file's contents yet — that is Phase 7 onwards.

What that means for Phase 7, concretely:

- **`job_id` already exists in the upload response and answers `null`.** Phase 7 fills
  it in; adding the field later would have been a breaking change, so it is already
  there (`api/schemas/documents.py`).
- **`DocumentStatus` already declares `processing`, `ready` and `failed`.** Only
  `uploaded` is ever written today. The values are in the CHECK constraint already, so
  driving them is a code change and not another migration.
- **The enqueue point is `DocumentService.upload` and `add_version`**, after the commit
  that writes the rows — a job pointing at an uncommitted document is a job the worker
  cannot find.
- **Idempotency has its inputs ready.** Architecture §12 wants
  `content hash + document/version identity + job identity`; the first two are columns
  on `document_versions` now.
- **`shared/` exists and is on the import path** (`src/shared/storage/`), so
  `shared/queue/` follows the same shape: interface in `base.py`, implementation beside
  it, nothing above it knowing which one is in use.

Still true from Phase 5, and still the rule: every organization-scoped route declares a
permission with `require(...)`, and every new one is added to `SCOPED_ROUTES` in
`tests/test_isolation.py`.

---

## 2. Completed work

### Phase 0 — Backend Foundation ✅

| Task | Notes |
|---|---|
| Remove stray root `pyproject.toml` + `src/` stub | Root is clean |
| `backend/` directory skeleton | Later restructured — see section 3 |
| `backend/pyproject.toml` via uv, Python pinned | `requires-python = ">=3.14"` |
| Core deps | fastapi, uvicorn, pydantic, pydantic-settings |
| Verify `import fastapi` | FastAPI 0.141.1 |
| ruff lint + format | `line-length = 100`, rules `E,F,I,UP,B,SIM` |
| `.env.example` | Three of them — root, `backend/`, `frontend/` |

### Phase 1 — Local Infrastructure ✅

`docker-compose.yml` at repo root. Five services, all healthchecked, all bound to **loopback only**:

| Service | Container | Host port | Notes |
|---|---|---|---|
| Postgres 18 | `rag_postgres` | 5432 | Volume at `/var/lib/postgresql` (see gotcha 5.1) |
| PgBouncer 1.23.1 | `rag_pgbouncer` | 6432 | `pool_mode = transaction`, `LISTEN_PORT: 6432` |
| Redis 8 | `rag_redis` | **6380** | Not 6379 — see gotcha 5.2 |
| Qdrant | `rag_qdrant` | 6333 / 6334 | Still pinned `:latest` — should be pinned properly |
| MinIO | `rag_minio` | **9010** / 9011 | Added in Phase 6. Local S3 standing in for R2; console on 9011 |

**MinIO is a development component, not part of the deployed system.** Phase 6 stores
files in Cloudflare R2, and R2 speaks S3 — so the same `R2Storage` provider drives
both and only `STORAGE_ENDPOINT_URL` changes. It exists so document upload works on a
machine with no Cloudflare account. Against a real bucket, point `backend/.env` at R2
and leave this container stopped. Host ports are 9010/9011 because 9000/9001 are
commonly taken; the container side stays standard, so an API running *inside* compose
later would use `http://minio:9000`.

The bucket is not created by the app — `cd backend && uv run python
scripts/ensure_bucket.py` creates it, idempotently, through the same provider the API
uses, so bad credentials fail there with a readable message rather than at the first
upload.

`infrastructure/postgres/init/01-extension.sql` installs `pg_trgm`, `unaccent`, `btree_gin` on first boot. Verified present in the live database.

All credentials and ports come from the **root** `.env` (Compose reads `.env` from the compose file's directory). Root `.env.example` is committed; `.env` is gitignored.

### Phase 2 — FastAPI App Skeleton ✅ (8/8)

| # | Task | File |
|---|---|---|
| 1 | Packaging fix — library → application | `pyproject.toml` |
| 2 | Settings, env validation | `src/api/config/settings.py` |
| 3 | Structured JSON logging | `src/api/config/logging.py` |
| 4 | `/health` endpoint | `src/api/routes/v1/health.py` |
| 5 | Request-ID middleware | `src/api/middleware/request_id.py` |
| 6 | App factory | `src/api/main.py` |
| 7 | Lifespan hooks | `src/api/main.py` |
| 8 | Verified uvicorn + hot reload | — |

Verified live: startup log fires, `/api/v1/health` returns `200 {"status":"ok"}` with an `X-Request-ID` header, a caller-supplied ID is propagated rather than replaced, hot reload triggers on save, and the app **refuses to boot** when a required setting is missing.

### Phase 3 — Database Layer ✅ (8/8)

| # | Task | Status |
|---|---|---|
| 1 | `db/base.py` — declarative base + `TimestampMixin` | ✅ |
| 2 | `db/session.py` — async engine, session-per-request | ✅ |
| 3 | PgBouncer-compatible engine config | ✅ proven, see 5.3 |
| 4 | Alembic init + wiring | ✅ |
| 5 | First models: `User`, `Organization`, `Membership` | ✅ |
| 6 | First migration + admin-count trigger | ✅ |
| 7 | Repository base class | ✅ `db/repositories/base.py`, `users.py` |
| 8 | Verify migration round-trip | ✅ verified 2026-09-19, see below |

**Round-trip verification, 2026-09-19.** Run against a scratch database
(`rag_roundtrip_check`, created and dropped, dev data untouched):

```
alembic upgrade head    → users, organizations, memberships, alembic_version
alembic downgrade base  → only alembic_version remains; trigger and both
                          functions dropped with it
alembic upgrade head    → clean
alembic revision --autogenerate → empty migration (no model/schema drift)
uv run pytest -q        → 25 passed
```

The scratch database needed `pg_trgm`, `unaccent` and `btree_gin` created by hand —
`infrastructure/postgres/init/` only runs on first boot of the cluster, not per
database. Note also that Alembic goes through `MIGRATION_DATABASE_URL` (direct to
Postgres, port 5432); overriding it as an environment variable is how to point a
migration run at another database without editing `.env`.

Alembic is wired to the live database and reads `Base.metadata` directly, so autogenerate is a real drift check rather than a formality — it currently produces an empty migration against the three models.

---

### Phase 4 — Authentication ✅ (10/10)

Custom, self-hosted auth. No identity vendor: passwords live in `users.password_hash`,
tokens are signed with `JWT_SECRET_KEY`, and every check runs in-process.

| # | Task | File |
|---|---|---|
| 1 | Password hashing (Argon2id) | `src/api/auth/password.py` |
| 2 | JWT encode/decode, claims, expiry | `src/api/auth/jwt.py` |
| 3 | Access + refresh lifecycle, rotation | `src/api/auth/jwt.py`, `services/auth_service.py` |
| 4 | Request/response models | `src/api/schemas/auth.py` |
| 5 | Register / login / refresh / logout logic | `src/api/services/auth_service.py` |
| 6 | Routes | `src/api/routes/v1/auth.py`, `routes/v1/me.py` |
| 7 | `get_current_user` | `src/api/auth/dependencies.py` |
| 8 | Redis client | `src/api/db/redis.py` |
| 9 | Revocation deny-list | `src/api/auth/revocation.py` |
| 10 | Security tests | `tests/test_auth_security.py`, `tests/test_auth_flow.py` |

Endpoints: `POST /api/v1/auth/register` (201), `/login`, `/refresh`, `/logout` (204),
`/logout-all` (204), and `GET /api/v1/me`.

Decisions worth not re-deriving:

- **Claims are `sub`, `jti`, `typ`, `iat`, `exp` — no role, no organization.** §7.8.
  `typ` is checked on every decode, or a 7-day refresh token works as an access token.
- **`algorithms=[...]` is pinned server-side** in `decode_token`, which is what makes
  the `alg: none` and RS256→HS256 confusion attacks fail.
- **Registration writes three rows in one transaction** and sets the membership to
  `active` explicitly — the column default is `pending`, which is for invitations.
- **Login verifies against a dummy hash when the account is absent.** Returning early
  answers in ~1 ms versus ~60 ms and is a working email-enumeration oracle.
- **Refresh rotates, and reuse of a spent `jti` revokes every session for that user.**
- **Revocation stores the exception, not the session**: `revoked:jti:{jti}` with a TTL
  equal to the token's remaining life, plus `revoked:user:{sub}` as a cutoff for
  "log out everywhere". Every authenticated request now costs one Redis round-trip.
- **Errors**: one `AuthError` hierarchy, mapped to responses in `main.py`. The client
  sees a fixed `detail`; the log gets `reason`. Structlog events are `auth.registered`,
  `auth.login`, `auth.login_failed`, `auth.refreshed`, `auth.refresh_reused`,
  `auth.logout`, `auth.token_rejected` — identifiers and reason codes only, never a
  password, hash or whole token.

**Verified 2026-09-19:** 61 tests pass (`uv run pytest -q`), ruff clean, and a live
server on real Postgres + Redis returned 201 for register, 200 for `/me`, 401 with no
token, 204 for logout and 401 for `/me` afterwards — with `revoked:jti:*` keys present
in Redis carrying a TTL, and the three rows written with `active_admin_count = 1`.

New dependencies: `argon2-cffi`, `pyjwt`, `redis`, `pydantic[email]`; dev `httpx`,
`fakeredis`.

---

---

### Phase 5 — Multi-Tenancy and RBAC ✅ (12/12)

| # | Task | File |
|---|---|---|
| 1 | Membership lifecycle — invite, accept, role, suspend, remove, reinstate, leave | `src/api/services/membership_service.py` |
| 2 | `Permission` enum + role matrix | `src/api/auth/permissions.py` |
| 3 | `OrgContext` | `src/api/auth/context.py` |
| 4 | `get_org_context` + Redis membership cache | `src/api/auth/dependencies.py`, `auth/membership_cache.py` |
| 5 | `require(Permission)` + default deny | `src/api/auth/rbac.py` |
| 6 | Organization-scoped base repository | `src/api/db/repositories/org_scoped.py` |
| 7 | Repositories retrofitted | `db/repositories/memberships.py`, `organizations.py` |
| 8 | Admin range — DB layer from Phase 3, service layer here | `membership_service._guard_admin_range` |
| 9 | `super_admin` bypass + `audit_log` | `org_scoped.get_across_tenants`, `models/audit.py` |
| 10 | Routes under `/orgs/{organization_id}/` | `routes/v1/orgs.py`, `routes/v1/members.py`, `routes/v1/me.py` |
| 11 | Cross-tenant isolation suite | `tests/test_isolation.py` (28 tests) |
| 12 | RBAC suite | `tests/test_rbac.py` (63 tests) |

Endpoints added:

```
POST   /api/v1/orgs                                             create a team org (201)
GET    /api/v1/orgs/{org}                                       org:read
PATCH  /api/v1/orgs/{org}                                       org:update
DELETE /api/v1/orgs/{org}                                       org:delete  (deactivates, 204)
POST   /api/v1/orgs/{org}/leave                                 org:read
GET    /api/v1/orgs/{org}/members                               member:read
POST   /api/v1/orgs/{org}/members                               member:invite (201)
GET    /api/v1/orgs/{org}/members/{id}                          member:read
PATCH  /api/v1/orgs/{org}/members/{id}/role                     member:update_role
POST   /api/v1/orgs/{org}/members/{id}/suspend                  member:remove
POST   /api/v1/orgs/{org}/members/{id}/reinstate                member:invite
DELETE /api/v1/orgs/{org}/members/{id}                          member:remove
GET    /api/v1/me/organizations                                 authenticated
POST   /api/v1/me/invitations/{org}/accept                      authenticated
```

Decisions worth not re-deriving:

- **`POST /api/v1/orgs` was added, and is not in the task list.** Nothing else can
  create a team organization — registration only ever makes a personal one, and a
  personal workspace cannot take members (§7.3) — so invitations, the members routes
  and most of the isolation suite would have been unreachable without it. It is not
  organization-scoped (there is no organization yet), so it sits outside default deny
  and requires only authentication.
- **Accepting an invitation lives under `/me`, not under `/orgs/{id}/`.** A pending
  membership resolves to no context, so a route under the scoped prefix would 404 the
  exact person it exists for.
- **Invitations require an existing account.** Inviting an address that has never
  registered needs an emailed invitation token, which belongs with the email
  infrastructure; the endpoint returns 409 rather than writing a row nobody can accept.
- **Two membership repositories, deliberately.** `MembershipRepository` is unscoped
  because it is what *establishes* the scope; `OrgMembershipRepository` inherits the
  mandatory filter for everything after a context exists. One class with a flag would
  be a method that is sometimes scoped, decided by an argument nobody checks.
- **Removal and suspension share an end state** (`suspended`) and differ in the audit
  action. The row is retained because audit rows reference it (§7.4).
- **The admin count moves at accept, not at invite** — a pending admin is not an active
  one — so that is where the ceiling check fires.
- **`audit_log` has no FK on `organization_id` and no `updated_at`.** The row for a
  deletion has to outlive the tenant, and an audit row is not editable.

**Verified 2026-09-19:** 177 tests pass (`uv run pytest -q`), ruff clean, migrations
round-tripped on a scratch database (`rag_roundtrip_check`, created and dropped:
`upgrade head` → 4 tables, `downgrade base` → only `alembic_version`, `upgrade head`
again clean, `--autogenerate` produced an empty migration), and a live server on real
Postgres + real Redis was driven through the whole flow: create team (201,
`active_admin_count: 1`), invite (pending), pending member reading the org (404),
accept (active), member reading (200) and patching (403), outsider reading (404),
promotion to admin (count 2), suspension, suspended member reading (404), and demoting
the last admin (409). A `membership:{user}:{org}` key was present in Redis with a TTL.

### Phase 6 — Document Management ✅ (10/10)

| # | Task | File |
|---|---|---|
| 1 | `StorageProvider` interface + §8 key layout | `src/shared/storage/base.py` |
| 2 | R2 / S3-compatible implementation | `src/shared/storage/r2.py` |
| 3 | `Document` + `DocumentVersion` + migration | `src/api/models/document.py`, `migrations/versions/9c6f36c3bd9b_*.py` |
| 4 | Request / response schemas | `src/api/schemas/documents.py` |
| 5 | Validation — extension, MIME, size, magic bytes | `src/api/services/file_validation.py` |
| 6 | Content-hash dedup, scoped per organization | `db/repositories/documents.py`, `services/document_service.py` |
| 7 | Document service | `src/api/services/document_service.py` |
| 8 | Routes | `src/api/routes/v1/documents.py` |
| 9 | Streaming upload + S3 multipart | `document_service._chunks`, `r2.put_stream` |
| 10 | Organization isolation | `DocumentRepository(OrgScopedRepository)` + `tests/test_isolation.py` |

Endpoints added:

```
POST   /api/v1/orgs/{org}/documents                             document:create (201)
GET    /api/v1/orgs/{org}/documents                             document:read
GET    /api/v1/orgs/{org}/documents/{id}                        document:read
PATCH  /api/v1/orgs/{org}/documents/{id}                        document:update
DELETE /api/v1/orgs/{org}/documents/{id}                        document:delete (204, soft)
GET    /api/v1/orgs/{org}/documents/{id}/versions               document:read
POST   /api/v1/orgs/{org}/documents/{id}/versions               document:update (201)
GET    /api/v1/orgs/{org}/documents/{id}/download               document:read
GET    /api/v1/orgs/{org}/documents/{id}/versions/{n}/download  document:read
```

No permission was added to the matrix — Phase 5 already defined all five
`document:*` permissions. `document:delete` is admin-only; members may upload and
revise. `document:reprocess` is still unused and belongs to Phase 7.

Decisions worth not re-deriving:

- **Storage is written before the database, and a failed database write deletes the
  object.** A row pointing at a missing key is unfixable from outside — nothing can
  tell whether the object was lost or never written. A stored object with no row is
  garbage, and garbage is sweepable.
- **Deduplication runs *after* the upload.** The hash is not knowable until the bytes
  have been read, so a duplicate costs one wasted upload and is then deleted
  (`_discard`). Hashing first would mean buffering the whole file, which is what the
  streaming path exists to prevent.
- **Dedup is scoped to `(organization_id, content_hash)`** — an index, not a unique
  constraint. Global matching would leak the existence of one tenant's document to
  another (invariant 2) and point two customers at one object; a unique constraint
  would reject a version 3 that restores version 1's content, which is legitimate.
- **A duplicate returns the existing document with `deduplicated: true`,** and a match
  whose document was soft-deleted is *not* a duplicate — pointing the caller at a row
  no route will show them is worse than storing the bytes again.
- **Delete is soft, and the objects stay.** From Phase 19 a citation points at a
  version; purging is a retention job with its own audit trail.
- **Download streams through the API.** `presigned_url` exists on the provider and is
  used by nothing: streaming keeps the tenant fence in the request path, where the
  scoped repository enforces it, rather than in a URL whose only protection is expiry.
- **`documents.current_version` is an integer, not a foreign key.** A key to
  `document_versions.id` plus the one pointing back is a circular FK — `use_alter`, a
  `post_update` relationship and a two-step migration — and buys nothing over the
  number the `(document_id, version_number)` unique constraint already resolves.
- **`APIError` is now the base of every domain error** (`src/api/errors.py`), and
  `AuthError` subclasses it. Starlette resolves handlers by walking the MRO, so one
  handler in `api.main` covers Phase 4, Phase 6 and every phase after.
- **Storage is optional at boot.** Missing credentials log `storage.unconfigured` at
  startup and every document route answers **503**. Requiring it would stop the whole
  API starting on a machine with no bucket, taking authentication down with it.
- **URL / web-page ingestion is not in this phase.** `plan.md` lists web pages as a
  supported format, but fetching a URL needs SSRF defence (architecture §18, plan
  Phase 27) and is not an upload.
- **DOCX is verified only as a zip container.** Proving it is really OOXML means
  reading the central directory, which is at the *end* of the file and unavailable to
  a check that must decide before the upload starts. The Phase 8 parser opens the
  package for real; what this check has to stop — an executable wearing a `.docx`
  name — it does stop.

**Verified 2026-09-19:** 264 tests pass (`uv run pytest -q`), ruff clean, the migration
round-trips (`upgrade head` → `downgrade -1` → `upgrade head`) and `--autogenerate`
against the upgraded database produces an empty migration, so the models and the schema
agree.

The storage layer was also driven against a **real S3 API** — MinIO, since there is no
R2 bucket yet. It started as a throwaway container and is now the `minio` service in
`docker-compose.yml` (host port 9010, bucket `neurex-documents`), with `backend/.env`
pointing at it:

- `R2Storage` directly: a 20-byte object took one `put_object`; a 16 MiB object took a
  3-part multipart upload (ETag suffix `-3`); `open_stream` reassembled it byte for
  byte; `exists`, `presigned_url` and a double `delete` behaved; a missing key raised
  `ObjectNotFound`; and a stream that raised mid-upload left **zero** dangling
  multipart uploads.
- The whole API against it: register → create org → upload (201) → duplicate upload
  (`deduplicated: true`, same document id, no second object) → version 2 → download
  current (v2 bytes) and v1 (v1 bytes) → a 12 MiB upload whose download hashed
  identical to the source → 64 random bytes named `.pdf` rejected **415** → delete
  **204** → subsequent GET **404**. The bucket held exactly
  `tenant_{org}/documents/{id}/versions/v{n}/source.pdf` and nothing else.
- With storage unconfigured, upload and list both answered **503** with
  `"Document storage is not configured on this server"`.

The same end-to-end flow was re-run afterwards against the compose service rather than
the throwaway container, with identical results, and the bucket again held only the
three expected `tenant_.../versions/v{n}/source.pdf` keys with no dangling multipart
uploads.

---

---

## 3. Layout and conventions

The backend was restructured from the original `plan.md` layout. The old path for a route file was `backend/apps/api/app/api/v1/health.py` — six levels, `api` twice, plus `apps` and `app`. Now:

```
backend/
├── src/
│   ├── api/          → FastAPI service. Imports read `from api.config.settings import Settings`
│   │   ├── main.py
│   │   ├── config/   settings.py, logging.py
│   │   ├── db/       base.py, session.py
│   │   ├── middleware/
│   │   └── routes/v1/
│   ├── workers/      → ingestion + embedding workers (not started)
│   └── shared/       → library code, imported by api/ and workers/
│       └── storage/  base.py (StorageProvider), r2.py — Phase 6
├── migrations/       → Alembic. Outside src/ — scripts, not importable code
├── tests/
├── alembic.ini
└── pyproject.toml
```

Two rules, recorded in `plan.md`: **one wrapper level only**, and **never repeat a name across nesting levels** (hence `api/routes/`, not `api/api/`).

**Nothing is pip-installed.** `pyproject.toml` sets `[tool.uv] package = false`; `src/` goes on the import path via `pythonpath = ["src"]` for pytest and `--app-dir src` for uvicorn.

### Running things

```bash
cd backend

# API
uv run uvicorn api.main:app --reload --app-dir src

# lint / format
uv run ruff check .
uv run ruff format .

# migrations
uv run alembic current
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

```bash
# storage bucket — once, after the first `docker compose up`
uv run python scripts/ensure_bucket.py
```

```bash
# infrastructure, from repo root
docker compose up -d
docker compose ps          # want "healthy", not just "Up"

# MinIO console (browser): http://127.0.0.1:9011
# credentials: MINIO_ROOT_USER / MINIO_ROOT_PASSWORD in the root .env
```

### Dependencies

Runtime: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `structlog`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `argon2-cffi`, `bcrypt`, `pyjwt`, `redis`, `aioboto3`, `python-multipart`
Dev: `ruff`, `colorama`, `pytest`, `pytest-asyncio`, `httpx`, `fakeredis`

`aioboto3` (Phase 6) pulls `boto3`/`botocore`/`aiohttp` — 21 packages for one S3
client. `python-multipart` is not optional: FastAPI's `UploadFile` does nothing
without it.

**No `python-magic`.** Magic-byte sniffing is a signature table in
`api/services/file_validation.py`. `libmagic` needs a binary on Windows and answers
questions this system never asks; the allowlist is five formats long.

---

## 4. Identity and RBAC model — specified

**Resolved 2026-09-19.** Full specification: `architecture.md` §7. Summary:

```text
User ──────< Membership >────── Organization
(global identity)   (role, account_type, status)   (tenant)
```

| Role | Lives on | Scope |
|---|---|---|
| `super_admin` | `User.is_super_admin` | Platform-wide, **not** organization-scoped |
| `admin` | `Membership.role` | One organization, 1 to `max_admins` (default 2) per org |
| `member` | `Membership.role` | One organization |

Decisions that affect Task 5 directly:

- **Role is on the membership.** One person can be `admin` in one organization and
  `member` in another. A `role` column on `User` cannot express that.
- **Solo users get a personal organization** (`Organization.kind = 'personal'`),
  created in the same transaction as registration. This is what lets
  `organization_id` be `NOT NULL` on every tenant-scoped table with no nullable-owner
  branch — see §7.3 for why the nullable alternative was rejected.
- **`User.is_super_admin` goes in now**, so it lands in the first migration instead of
  needing a backfill.
- **`account_type`** (`member` / `guest` / `service`) is billing metadata and never
  participates in an authorization decision.
- **Admin count is a range, not a cap** — at least one, at most `max_admins`. A cap
  alone lets the last admin strand the organization with nobody who can manage it.
  Enforced by a counter column plus `CHECK` on `organizations`, maintained by a
  trigger; a counting trigger would be racy (§7.7).

`super_admin` is a deliberate hole in tenant isolation. Phase 5 builds a base
repository that forces an `organization_id` filter on every query; a platform operator
needs to bypass it. That bypass must be **explicit** (a named parameter, never an
implicit branch buried in the repository), **audited** (log who read across
organizations and why), and **read-only**. An unaudited bypass is exactly what Phase
5's adversarial test suite exists to catch.

## 5. Gotchas — things that already cost time

### 5.1 Postgres 18 changed its data directory

Postgres 18 sets `PGDATA=/var/lib/postgresql/18/docker` and declares `VOLUME /var/lib/postgresql`. The pre-18 advice of mounting at `/var/lib/postgresql/data` makes the container **refuse to start**. Compose mounts the parent. If you ever hit this again, the volume must be deleted (`docker volume rm rag_postgres_data`) — remounting carries the broken state over.

### 5.2 Redis is on host port 6380

A **native Redis Windows service** (auto-start) owns 6379 on this machine. Docker's bind fails with a misleading *"socket forbidden by its access permissions"* rather than a plain port-in-use error. The container's host port was moved to 6380; container-side is still 6379.

Consequence: plain `redis-cli` connects to the **native** Redis, not yours. Use `redis-cli -h localhost -p 6380 -a <password>`. `backend/.env` already points `REDIS_URL` at 6380.

### 5.3 PgBouncer needs two engine settings — both proven necessary

`db/session.py` sets:

```python
poolclass=NullPool,
connect_args={"statement_cache_size": 0},
```

`NullPool` because pooling on top of a pooler holds idle connections at two layers and multiplies the connection count by the number of app processes.

`statement_cache_size=0` because asyncpg prepares statements that live on one backend connection, while transaction-mode pooling rotates backends underneath you. **This was tested, not assumed:** reusing one connection across 25 sequential transactions passes with the setting and fails with `DuplicatePreparedStatementError` without it. Do not remove it as a "performance cleanup".

If query-planning overhead ever matters (Phase 28, with measurements), the alternative is PgBouncer's `max_prepared_statements` rather than reverting this.

### 5.4 Two database URLs, deliberately

```
DATABASE_URL           → localhost:6432   (PgBouncer)   — the app
MIGRATION_DATABASE_URL → localhost:5432   (Postgres)    — Alembic only
```

Migrations run DDL and take advisory locks that must persist across statements; transaction-mode pooling breaks both. `migrations/env.py` reads `migration_database_url` specifically. `alembic.ini` has `sqlalchemy.url` **blank on purpose** so credentials are never committed.

### 5.5 `colorama` is required on Windows

structlog's `ConsoleRenderer` raises `SystemError` on Windows without it. Dev-group dependency. Production uses `JSONRenderer` and doesn't need it.

### 5.6 Alembic `compare_type` / `compare_server_default`

Both set `True` in `migrations/env.py`. They default to `False`, and with the defaults a column type change (e.g. `String(50)` → `String(200)`) autogenerates a **silently empty** migration.

### 5.7 `backend_tasks.md` was reordered

30 tasks were listed before their own dependencies — `main.py` before the modules it imports, retry logic before idempotency, `token_counter` after the chunkers that use it. Security tasks that had been parked in Phase 27 were moved into the phase that creates the risk (SSRF → Phase 8 with the URL fetcher, magic-byte validation → Phase 6 with uploads, prompt-injection defence → Phase 19). The full change log is at the bottom of `docs/backend_tasks.md`.

---

### 5.8 Test fixtures must share one connection

The `client` fixture (HTTP, through the app) and the `session` fixture (direct SQL)
have to run on the **same** `AsyncConnection`, and its sessions need
`join_transaction_mode="create_savepoint"`.

Two separate connections means two transactions: rows written through the API are
invisible to the test's own session, and a `is_active = false` written by the test is
invisible to the app. Both failure modes look like a logic bug in the code under test
rather than a fixture problem, and cost time to track down. Without `create_savepoint`,
the service's real `commit()` ends the outer transaction and test data survives the
rollback.

### 5.9 `EmailStr` rejects `.test` addresses

`pydantic[email]` refuses special-use domains, so the `@example.test` addresses used in
the repository tests return **422** from any route taking an `EmailStr`. The auth tests
use `@example.com`, which it accepts.

### 5.10 FastAPI 0.141 no longer flattens `include_router`

`app.routes` used to contain every route. It now holds a nested `_IncludedRouter` per
`include_router` call, carrying `.original_router` and an `.include_context` with the
prefix. A scan of `app.routes` looking for `APIRoute` finds **three** built-in routes
and none of ours.

This matters because the default-deny audit is such a scan: written the obvious way it
passes while checking nothing. `api.auth.rbac.iter_api_routes` walks the tree instead
and is what both `scan_permission_declarations` and the
`test_every_org_scoped_route_declares_a_permission` test go through.

Starlette 1.6 also does not set `scope["route"]` — only `scope["endpoint"]` — which is
why the request-time guard matches on the endpoint function rather than the route.

### 5.11 `ctx.log_fields()` already carries `role`

`logger.info("membership.invited", role=role.value, **ctx.log_fields())` raises
`TypeError: got multiple values for keyword argument 'role'` — structlog's bound
method takes the collision as a duplicate argument, and it surfaces as a 500 from the
route rather than as a logging warning. Any new log line naming a role must pick a
distinct key (`invited_role`, `previous_role`, `new_role`).

### 5.12 The admin-count trigger runs after the ORM has read the row

`OrganizationService.create` flushes the organization, inserts the admin membership,
and commits; the trigger then updates `organizations.active_admin_count` underneath.
With `expire_on_commit=False`, the in-memory object still says `0`, so the create
response reported `active_admin_count: 0` for an organization that had one admin —
caught by the live smoke test, not by the suite, because the tests assert the database
value. `await session.refresh(organization)` after the commit is the fix, and the same
applies to any response returning a trigger-maintained column.

### 5.13 A server-side `onupdate` leaves the column expired after `commit()`

`TimestampMixin.updated_at` carries `onupdate=func.now()`, so after an UPDATE the
session does not know the new value and marks the attribute expired — even with
`expire_on_commit=False`, which only governs *commit*, not the flush's own
expiry. Serialising the row then triggers a lazy load outside the async greenlet and
the request dies with:

```
MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here
```

It surfaced at `DocumentResponse.model_validate(document)` in the rename and
add-version routes — far from its cause, and only on paths that UPDATE and then return
the row. `await session.refresh(instance)` after the commit is the fix. Related to
5.12 but a different mechanism: 5.12 is a value a *trigger* wrote, this is a value the
*column* asked the server for.

### 5.14 `func.now()` is the transaction timestamp, and the suite is one transaction

PostgreSQL's `now()` is `transaction_timestamp()`, not the clock. Every test runs
inside the outer transaction opened by the `connection` fixture, so **every row any
test writes shares one `created_at`** — and an assertion like "newest first" has
nothing to sort by and passes or fails on which row the planner happened to return.

It cost a full-suite run to find, because a two-row ordering assertion is a coin flip
that had been landing heads. Ordering is now asserted in
`tests/test_document_repository.py`, which sets `created_at` explicitly; the HTTP suite
asserts membership and totals instead. Anything time-ordered in a later phase has the
same problem.

### 5.15 An abandoned S3 multipart upload is invisible and billed

Parts uploaded to an incomplete multipart upload do not appear in a bucket listing and
are stored — and charged for — until a lifecycle rule removes them. `put_stream`
therefore catches `BaseException`, not `Exception`: a cancelled request is exactly when
an upload gets abandoned mid-flight, and `CancelledError` does not inherit from
`Exception`. Verified against MinIO: after a stream that raised at the first part
boundary, `list_multipart_uploads` returned nothing.

The provider also only opens a multipart upload once the buffer passes `PART_SIZE`
(8 MiB); below that it is a single `put_object`. S3 rejects a completed multipart
upload whose non-final parts are under 5 MiB, so that threshold is a floor, not a
preference.

### 5.16 FastAPI reads a multipart body *before* it solves dependencies

For a route with a `File()` parameter, the body is parsed first and the dependencies —
including `get_org_context` — run after. It does not weaken isolation: a JSON body sent
to a multipart route parses as an empty form, so the outsider still gets the 404 that
`SCOPED_ROUTES` asserts. It does mean an oversized body is read before any
authorization check, which is why `enforce_content_length` rejects on the header. The
byte count taken while streaming remains the only real guarantee, since the header is
client-supplied.


---

## 6. Loose ends

- **`docs/*.bak`** — pre-rewrite backups of `plan.md` and `backend_tasks.md`. Delete or
  gitignore once the rewrites are trusted.
- **Qdrant pinned to `:latest`** in compose. Every other image is pinned; this one
  should be too.
- **Line endings** — git warns `LF will be replaced by CRLF`. Harmless now, but a
  `.gitattributes` with `* text=auto eol=lf` is worth adding before Phase 32, since
  CRLF breaks shell scripts inside Docker images.
- **Invitations need an existing account.** `POST /orgs/{org}/members` returns 409 for
  an address that has never registered. Emailed invitation tokens are the missing
  piece, and they wait on email infrastructure.
- **Organization deactivation is bounded by the cache TTL for other members.** The
  admin who runs it is locked out immediately only because their own key is
  invalidated; everyone else keeps a cached membership for up to
  `membership_cache_ttl_seconds` (30s). Invalidating every member's key needs either a
  per-organization key set or a generation counter — worth doing when deactivation
  becomes a real operation rather than a test.
- **`MembershipService._translate` is not covered by a test.** It maps the trigger's
  and the CHECK's errors onto the same 409 the service-layer guard returns, for the
  concurrent case where two requests both pass the guard. Reproducing that race needs
  two connections committing in lockstep; the DB half is covered by
  `tests/test_admin_count.py`, the translation half is not.
- **R2 itself has never been touched.** The S3 client is verified against MinIO, which
  is S3-compatible but not R2: R2 differs on request checksums and on some multipart
  edge cases, and `R2Storage` sets `signature_version="s3v4"` for that reason. The
  first run against a real bucket is the one to watch, and it needs credentials this
  project does not have yet.
- **No orphan sweep.** `_discard` deletes the object when an upload deduplicates or a
  database write fails, but a process killed between `put_stream` and `commit` leaves
  an object nothing points at. A reconciliation job — list the tenant prefix, drop keys
  with no `document_versions` row — belongs with the retention work, and a bucket
  lifecycle rule for incomplete multipart uploads belongs with it.
- **One S3 client per request.** `R2Storage._client()` opens an aioboto3 client per
  operation. It costs about a millisecond and no round trip, and a long-lived client
  shared across event-loop lifecycles is not obviously safe; if it shows up in a
  profile, Phase 28 is where it changes, with a measurement.
- **`StorageProvider.presigned_url` is implemented and unused.** Kept because the
  decision to hand bytes to something outside the API belongs to a route, but it is
  untested beyond the MinIO run and will rot if nothing calls it.
- **MinIO is an unconditional compose service.** It starts with everything else, which
  is right for now and wrong once there is a real R2: it should move behind a Compose
  profile (`profiles: [dev]`) so `docker compose up -d` in a deployed environment does
  not start a storage server nobody uses. One line, deferred because no deployed
  environment exists yet.
- **The end-to-end runs left data behind** — three objects in the `neurex-documents`
  bucket and a handful of rows (users, organizations, documents) in the dev database,
  from throwaway accounts. Harmless, and not cleaned up because deleting rows other
  rows reference is a worse idea than leaving 12 MiB of test data in a dev volume.
- **Phase 6 is uncommitted.** `src/shared/`, `src/api/errors.py`, the document models,
  schemas, service, repositories, routes, the migration, `scripts/ensure_bucket.py` and
  five test files are all in the working tree, along with `pyproject.toml`/`uv.lock`
  changes for `aioboto3` and `python-multipart`, the `minio` service in
  `docker-compose.yml`, and the new `MINIO_*` keys in the root `.env.example`.
- **Tests:** 264 passing — repositories, admin-count trigger, auth flow and security,
  RBAC (63), cross-tenant isolation (37), membership lifecycle (25), documents over
  HTTP (22), document repositories (11), file validation (42) and the R2 upload path
  (5), on a session-scoped engine through PgBouncer with per-test rollback.
