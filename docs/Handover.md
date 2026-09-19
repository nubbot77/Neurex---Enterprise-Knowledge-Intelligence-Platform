# Handover

**Project:** Neurex — Enterprise Knowledge Intelligence Platform
**Last updated:** 2026-09-19 (Phase 5 closed)
**Progress:** Phases 0–5 complete — **6 of 34 phases**

Task list and full phase breakdown: `docs/backend_tasks.md`
Identity, tenancy and RBAC specification: `docs/architecture.md` §7
Architecture and directory structure: `docs/plan.md`

---

## 1. Where to pick up

**Next task: Phase 6, Task 1 — `shared/storage/base.py`, the `StorageProvider`
interface.**

Phase 5 is closed. Organization context, the role→permission matrix, `require()` with
default deny, the organization-scoped repository and the audited `super_admin` bypass
are all in place, and `/api/v1/orgs/{organization_id}/…` is the shape every
organization-owned route takes from here on.

What that means for Phase 6: a `Document` repository subclasses
`OrgScopedRepository`, not `BaseRepository`, and gets `WHERE organization_id = ?` for
free. Every document route declares a permission with `require(...)` — a route that
forgets is refused at runtime and logged as an error at boot, so the omission is loud
rather than silent. Add each new scoped route to `SCOPED_ROUTES` in
`tests/test_isolation.py`; that list is what "every route scoped to it" in invariant 3
actually means.

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

`docker-compose.yml` at repo root. Four services, all healthchecked, all bound to **loopback only**:

| Service | Container | Host port | Notes |
|---|---|---|---|
| Postgres 18 | `rag_postgres` | 5432 | Volume at `/var/lib/postgresql` (see gotcha 5.1) |
| PgBouncer 1.23.1 | `rag_pgbouncer` | 6432 | `pool_mode = transaction`, `LISTEN_PORT: 6432` |
| Redis 8 | `rag_redis` | **6380** | Not 6379 — see gotcha 5.2 |
| Qdrant | `rag_qdrant` | 6333 / 6334 | Still pinned `:latest` — should be pinned properly |

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
│   └── shared/       → was `packages/` (not started)
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
# infrastructure, from repo root
docker compose up -d
docker compose ps          # want "healthy", not just "Up"
```

### Dependencies

Runtime: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `structlog`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
Dev: `ruff`, `colorama`

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
- **Tests:** 177 passing — repositories, admin-count trigger, auth flow and security,
  RBAC (63), cross-tenant isolation (28) and membership lifecycle (25), on a
  session-scoped engine through PgBouncer with per-test rollback.
