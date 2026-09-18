# Enterprise Knowledge Intelligence Platform — Detailed Architecture

## 1. Architecture Overview

The system is a multi-tenant enterprise knowledge platform.

Its primary workflow is:

```text
User
 ↓
React Application
 ↓
FastAPI API
 ↓
Authentication / Authorization
 ↓
Document / Search / Chat APIs
```

For documents:

```text
Upload
 ↓
Cloudflare R2
 ↓
PostgreSQL metadata
 ↓
Redis Queue
 ↓
Ingestion Worker
 ↓
Parse
 ↓
OCR when required
 ↓
Normalize
 ↓
Clean
 ↓
Chunk
 ↓
Embed
 ↓
Qdrant + Lexical Index
```

For queries:

```text
User Query
 ↓
Authentication + Organization Context
 ↓
Query Analysis
 ↓
Optional Query Rewrite
 ↓
 ┌───────────────┬───────────────┐
 │               │               │
 ▼               ▼               │
BM25         Dense Search        │
 │               │               │
 └───────┬───────┘               │
         ▼                       │
     RRF Fusion                 │
         ↓                      │
     Reranking                  │
         ↓                      │
  Context Selection             │
         ↓                      │
        LLM                     │
         ↓                      │
 Answer + Citation IDs          │
         ↓                       │
Citation Resolution              │
         ↓                       │
       Client                    │
```

---

# 2. Core Architectural Principle

The system should use **modular boundaries**, not unnecessary microservices.

Initial deployable units:

```text
web
api
worker
postgres
redis
qdrant
```

Inside the API and worker, use strong module boundaries.

Only extract a component into a separate service when its:

- scaling requirements
- resource requirements
- deployment lifecycle
- reliability characteristics

justify doing so.

This avoids premature microservice complexity.

---

# 3. Component Architecture

```text
                         ┌─────────────────────┐
                         │     React Web       │
                         │                     │
                         │ Documents           │
                         │ Search              │
                         │ Chat                │
                         │ Evaluations         │
                         │ Admin               │
                         └──────────┬──────────┘
                                    │ HTTPS
                                    ▼
                         ┌─────────────────────┐
                         │     FastAPI API     │
                         │                     │
                         │ Auth                │
                         │ Documents           │
                         │ Search              │
                         │ Chat                │
                         │ Evaluations         │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┼────────────────────┐
                │                   │                    │
                ▼                   ▼                    ▼
          PostgreSQL             Redis                  R2
                │                   │                    │
                │                   ▼                    │
                │             Worker Queue               │
                │                   │                    │
                │                   ▼                    │
                │          Ingestion Worker              │
                │                   │                    │
                │                   ▼                    │
                │         Document Processing             │
                │                   │                    │
                │                   ▼                    │
                │              Embeddings                 │
                │                   │                    │
                │                   ▼                    │
                │                Qdrant                   │
                │                                        │
                └──────────────────┬─────────────────────┘
                                   │
                                   ▼
                             Retrieval Engine
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
                   BM25                        Dense
                     │                           │
                     └─────────────┬─────────────┘
                                   ▼
                                  RRF
                                   ↓
                               Reranker
                                   ↓
                            Context Builder
                                   ↓
                                  LLM
                                   ↓
                           Answer + Citations
```

---

# 4. Frontend Architecture

Use:

```text
React
TypeScript
Vite
TanStack Query
Zustand
Tailwind
```

Suggested structure:

```text
apps/web/
└── src/
    ├── components/
    ├── features/
    │   ├── auth/
    │   ├── documents/
    │   ├── search/
    │   ├── chat/
    │   └── evaluations/
    ├── hooks/
    ├── lib/
    ├── routes/
    ├── stores/
    └── types/
```

Feature modules should contain feature-specific UI and logic.

TanStack Query handles server state.

Zustand handles local application state.

Avoid putting server data into Zustand unnecessarily.

---

# 5. API Architecture

FastAPI should be organized by domain.

```text
app/
├── api/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   ├── search.py
│   │   ├── chat.py
│   │   └── evaluations.py
│   └── dependencies.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── telemetry.py
│
├── domain/
│   ├── auth/
│   ├── documents/
│   ├── retrieval/
│   ├── chat/
│   └── evaluations/
│
├── models/
├── repositories/
├── schemas/
├── services/
└── main.py
```

Routes divide into three scopes, and the scope is visible in the URL:

```text
/api/v1/auth/*                        unauthenticated or identity-only
/api/v1/me/*                          authenticated, no organization context
/api/v1/orgs/{organization_id}/*      authenticated, organization-scoped
```

Everything under `/orgs/{organization_id}/` resolves an organization context before the
handler runs, and every query it issues is filtered by that organization. Section 7.8
defines the resolution; section 7.9 defines why the filter lives in the repository
rather than in the route.

The route should not contain the entire business workflow.

Conceptually:

```text
HTTP Request
 ↓
Route
 ↓
Authentication            → user_id
 ↓
Organization context      → membership, role, permissions
 ↓
Permission check          → declared by the route, default deny
 ↓
Validation
 ↓
Service
 ↓
Repository (organization filter injected) / external provider
 ↓
Response schema
```

---

# 6. PostgreSQL Architecture

PostgreSQL is the system of record for relational state.

Important tables:

```text
users
organizations
memberships
documents
document_versions
chunks
ingestion_jobs
conversations
messages
message_citations
evaluation_datasets
evaluation_cases
evaluation_runs
audit_logs
```

Use PostgreSQL for:

- metadata
- relationships
- authorization state
- document versions
- ingestion state
- conversation state
- evaluation state

Every table above except `users` and `organizations` carries a `NOT NULL`
`organization_id`. There are no exceptions and no nullable ownership column — see
section 7.3 for why solo users get a personal organization rather than a second
ownership path.

`memberships` is the authorization table. It is read on every organization-scoped
request, so `(user_id, organization_id)` is a unique index, not merely a constraint.

Do not store original PDFs in PostgreSQL.

---

# 7. Identity, Tenancy, and Access Control

This section defines the identity model, the tenant model, and the RBAC rules that
govern every authorization decision in the system. It supersedes the earlier
"User → Tenant" sketch.

## 7.1 Three entities

| Entity | Represents | Lifetime |
|---|---|---|
| `User` | A global identity — one human, one login credential | Independent of any organization |
| `Organization` | A tenant: a company, team, or a single person's private workspace | Independent of any user |
| `Membership` | The link between the two, and the place where authority lives | Exists only while the user belongs to the organization |

```text
User ──────< Membership >────── Organization
(global identity)    (role, account_type, status)    (tenant boundary)
```

`Membership` is not a plain join table. It carries the three facts that authorization
depends on:

| Column | Meaning |
|---|---|
| `role` | What this user may do **inside this organization** |
| `account_type` | How this seat is classified for billing and reporting. **Never consulted for authorization.** |
| `status` | Whether this membership is currently in force |

## 7.2 Why role lives on the membership

A user may belong to several organizations at once, with a different standing in each:
admin at Acme, ordinary member at Globex. A `role` column on `User` cannot express
that — it forces one role per human, which means either duplicating the person as two
accounts or accepting that the role is wrong in one of the organizations.

The authority is a property of the *relationship*, not of the person. So it lives on
the relationship.

Consequence for every authorization check in the system: the role lookup is always
keyed by the pair `(user_id, organization_id)`. There is no such thing as "the user's
role" without an organization in the question.

## 7.3 Individual users — the personal organization

A user may sign up and work alone, with no company. The system supports this without
introducing a second ownership path.

**Every user gets an organization at signup.** For a solo user it is a personal
organization: `Organization.kind = 'personal'`, exactly one member, that member holding
`admin`. A company workspace is `kind = 'team'`.

```text
kind = 'personal'    one member, cannot receive invitations
kind = 'team'        many members, invitations, role management
```

The alternative — letting organization-owned rows carry a nullable `organization_id`
and fall back to a `user_id` owner column — was rejected. It would mean every
tenant-scoped query becomes:

```text
WHERE organization_id = :org
   OR (organization_id IS NULL AND owner_id = :user)
```

That `OR` is exactly the clause a developer forgets, and forgetting it is a
cross-tenant data leak. Section 7.9's mandatory-filter repository cannot defend a rule
it has to express as a disjunction.

With personal organizations:

- `organization_id` is `NOT NULL` on every tenant-scoped table, with no exceptions
- every query filters on one column, with one value
- the isolation invariant the adversarial test suite checks is a single statement
- "upgrade my personal workspace to a team" is a `kind` change plus invitations, not a
  data migration

Cost: signup writes three rows in one transaction (`User`, `Organization`,
`Membership`) instead of one. That is the whole price.

## 7.4 Membership status

```text
pending      invited, invitation not yet accepted
active       in force
suspended    retained for audit and restoration, grants nothing
```

**Only `active` grants anything.** A `pending` or `suspended` membership resolves to
zero permissions. This is checked once, during organization context resolution (7.8),
not repeated at each call site.

Removal from an organization is a `status` transition, not a row delete — audit records
reference the membership, and deleting it would orphan that history.

## 7.5 account_type

`account_type` classifies the seat for billing and reporting:

```text
member       a regular seat, counted against the organization's plan
guest        external collaborator, restricted seat
service      non-human seat backing an API key or integration
```

**Rule: `account_type` carries no permissions.** It never appears in an authorization
decision. Only `role` does.

This rule exists because two attributes that both read as "what kind of user is this"
will otherwise drift into two overlapping permission systems, and every authorization
bug afterwards starts with "which of the two was supposed to win?" If a distinction
genuinely needs to change what someone may do, it belongs in `role`.

## 7.6 Roles and permissions

Three roles exist. Two are organization-scoped, one is not.

| Role | Scope | Stored on |
|---|---|---|
| `admin` | One organization | `Membership.role` |
| `member` | One organization | `Membership.role` |
| `super_admin` | Platform-wide, no organization | `User.is_super_admin` |

`super_admin` is not a membership role. A platform operator has no home organization;
the flag is a fact about the human. Its bypass rules are in 7.10.

### Permission catalogue

Permissions are named `resource:action`:

```text
org:read             org:update           org:delete
member:invite        member:read          member:update_role      member:remove
document:create      document:read        document:update         document:delete
document:reprocess
conversation:create  conversation:read    conversation:delete
search:execute
evaluation:create    evaluation:read      evaluation:run
apikey:create        apikey:read          apikey:revoke
audit:read
```

### Role to permission matrix

| Permission | `admin` | `member` |
|---|:--:|:--:|
| `org:read` | yes | yes |
| `org:update` | yes | no |
| `org:delete` | yes | no |
| `member:invite` | yes | no |
| `member:read` | yes | yes |
| `member:update_role` | yes | no |
| `member:remove` | yes | no |
| `document:create` | yes | yes |
| `document:read` | yes | yes |
| `document:update` | yes | yes |
| `document:delete` | yes | no |
| `document:reprocess` | yes | yes |
| `conversation:create` | yes | yes |
| `conversation:read` | yes | own only |
| `conversation:delete` | yes | own only |
| `search:execute` | yes | yes |
| `evaluation:create` | yes | no |
| `evaluation:read` | yes | yes |
| `evaluation:run` | yes | no |
| `apikey:create` | yes | no |
| `apikey:read` | yes | no |
| `apikey:revoke` | yes | no |
| `audit:read` | yes | no |

"own only" is a resource-level rule, not a role-level one: the permission is granted,
then the service additionally checks `resource.created_by == user_id`. Role checks and
ownership checks are separate steps and neither replaces the other.

### Where the matrix lives

The matrix is a **constant in application code**, not rows in a database table.

Rationale: with a fixed set of two organization roles, a `roles` / `permissions` /
`role_permissions` schema adds a join to every request and buys nothing a dictionary
does not. It also makes the permission set invisible to code review and to type
checking.

Migration trigger, recorded so the decision is revisited deliberately rather than
argued about: **the first time a customer needs a role the platform does not define**,
the matrix moves into the database as organization-scoped custom roles, and the
built-in roles become seeded rows. Until then it stays in code.

## 7.7 The two-admin rule

An organization has **at least one and at most two** `admin` memberships in `active`
status.

The maximum is stored as `Organization.max_admins`, defaulting to `2`. It is a column,
not a literal, so a plan change is an `UPDATE` rather than a migration plus a code
release. The minimum of one is a fixed invariant.

### Why the minimum matters as much as the maximum

A cap alone allows an organization to reach zero admins — the last admin demotes
themselves, or removes their own membership, and nobody can invite, manage roles, or
delete anything ever again. The organization is stuck, and only a platform operator can
rescue it.

So both ends are enforced. An operation is rejected if it would:

- raise active admins above `max_admins`, or
- drop active admins below one

This covers role changes, membership removal, membership suspension, and a user leaving
voluntarily — every one of them can move the count.

### Enforcement: two layers

**Layer 1 — database, authoritative.** `Organization.active_admin_count` is a
maintained counter with:

```text
CHECK (active_admin_count BETWEEN 1 AND max_admins)
```

A trigger on `Membership` insert, update, and delete adjusts the counter on the parent
organization row.

This is correct under concurrency for a specific reason worth stating, because the
obvious alternative is not. A trigger that runs `SELECT count(*) FROM memberships ...`
is **racy**: two concurrent transactions each see a snapshot that excludes the other's
uncommitted row, both count one admin, both insert, and the organization ends with
three. An `UPDATE organizations SET active_admin_count = active_admin_count + 1`
instead takes a row lock on the organization; the second transaction blocks, then
re-reads the committed value, and the `CHECK` fires. Same rule, different concurrency
behaviour.

The consequence of putting it here is that the rule cannot be bypassed — not by a
second service, not by a worker, not by a hand-typed `INSERT` during an incident.

**Layer 2 — service, for the error message.** The service checks the count first and
returns `409 Conflict` with a usable message. Without it the user sees a constraint
violation surfaced as a 500.

Layer 2 is a courtesy. Layer 1 is the guarantee. Layer 2 alone would be a bug.

### Recovery

If an organization loses both admins through identity-level account deletion, a
`super_admin` promotes a member. That path is audited like every other bypass (7.10).

## 7.8 Organization context resolution

Every request that touches organization-owned data resolves an organization context
before any handler logic runs.

```text
HTTP request
 ↓
authenticate → user_id                     (from JWT)
 ↓
read requested organization_id             (from URL path)
 ↓
load membership (user_id, organization_id)
 ↓
reject if absent or status != 'active'     → 404
 ↓
role → permission set                      (from the code matrix)
 ↓
OrgContext { user_id, organization_id, role, permissions, is_super_admin }
 ↓
service → repository → database / vector search
```

### The organization id comes from the URL

Organization-scoped routes are path-scoped:

```text
/api/v1/orgs/{organization_id}/documents
/api/v1/orgs/{organization_id}/conversations
/api/v1/orgs/{organization_id}/members
```

The scope is then visible in the route, in access logs, in traces, and in tests. A
header or a JWT claim hides it, and an ambient tenant that nothing in the URL records
is hard to audit after an incident.

A client-supplied `organization_id` is never trusted on its own. It is only ever a
lookup key for the membership query above, and a user with no active membership for
that organization is indistinguishable from a user asking about an organization that
does not exist.

### Absent membership returns 404, not 403

`403 Forbidden` confirms the organization exists. That leaks the existence and the id
space of other tenants to anyone probing. Absent membership returns `404`.

`403` is reserved for the case where membership *is* established and the role is
insufficient — there, the user already knows the organization exists, so a precise
error is useful rather than leaky.

### Role is not carried in the JWT

The access token carries identity (`user_id`), not authority. Membership and role are
resolved per request.

A token that carries `role: admin` keeps saying `admin` until it expires, so a
demotion or a removal does not take effect for the token's remaining lifetime. Since
the point of the two-admin rule and of membership suspension is that they apply
immediately, baking the role into the token would defeat both.

The per-request lookup is cached in Redis under
`membership:{user_id}:{organization_id}` with a short TTL, and the key is deleted
explicitly whenever the membership row changes. Cache invalidation on write is part of
the membership service, not an afterthought.

## 7.9 Two enforcement layers, neither optional

```text
Authorization   →  "may this role perform this action?"      route / service
Isolation       →  "is this row inside my organization?"     repository
```

They answer different questions and neither substitutes for the other:

- authorization without isolation: a `member` of Acme performs a permitted read and
  receives Globex's document, because nothing filtered the row
- isolation without authorization: a `member` of Acme deletes Acme's documents, which
  is correctly scoped and still wrong

**Isolation is structural.** The tenant-scoped base repository injects
`WHERE organization_id = :ctx.organization_id` into every query it issues. A query that
omits the filter is not one a developer can write by accident, because constructing one
requires calling a differently-named method that logs why.

**Authorization is declarative.** Routes declare the permission they require. A route
that declares nothing fails closed — the default is deny, so a forgotten declaration
produces a locked endpoint and a bug report, not a silent hole.

## 7.10 The super_admin bypass

`super_admin` is a deliberate hole in tenant isolation, for platform support and
incident response. Three rules constrain it:

**Explicit.** The bypass is a named argument the caller passes consciously
(`across_tenants=True`). It is never an implicit `if user.is_super_admin` branch inside
the repository — a reader of the call site must be able to see that this query can
cross tenants.

**Audited.** Every cross-tenant access writes an audit row: who, which organization,
which resource, when, and the stated reason. An unaudited bypass cannot answer "did
anyone read this customer's data?", which is the question that actually gets asked.

**Read-only.** Cross-tenant reads are support work. Cross-tenant writes have no
legitimate use and turn one mistaken operation into damage across several customers.
The two exceptions are admin recovery (7.7) and organization deletion, both audited
operations of their own.

## 7.11 Invariants

The statements the adversarial test suite exists to falsify:

1. Every tenant-scoped row has a non-null `organization_id`.
2. No response ever contains a row whose `organization_id` differs from the request's
   organization context, unless an audited `super_admin` bypass was used.
3. A user with no active membership in an organization receives `404` for every route
   scoped to it.
4. An organization always has between one and `max_admins` active admins.
5. `account_type` never changes the outcome of an authorization decision.
6. A route with no declared permission requirement denies all access.
7. Revoking or suspending a membership takes effect on the next request, not on the
   next token expiry.

---

# 8. Object Storage Architecture

Use Cloudflare R2 for source files.

Example logical layout:

```text
tenant_{id}/
    documents/
        {document_id}/
            versions/
                v1/source.pdf
                v2/source.pdf
```

PostgreSQL stores:

```text
storage_key
content_hash
mime_type
file_size
```

The database should never assume a local filesystem path exists.

---

# 9. Document Lifecycle

A document has two related concepts:

```text
Document
```

and:

```text
Document Version
```

Example:

```text
Employee Handbook
 ├── Version 1
 ├── Version 2
 └── Version 3
```

The current version is explicitly tracked.

This allows:

- rollback
- reproducibility
- auditing
- citation stability
- re-indexing

---

# 10. Upload Flow

```text
Browser
  │
  │ upload
  ▼
FastAPI
  │
  ├── authenticate
  ├── authorize
  ├── validate file
  ├── calculate/verify hash
  │
  ▼
R2
  │
  ▼
PostgreSQL
  │
  ├── document
  ├── version
  └── ingestion job
  │
  ▼
Redis
```

The API should return quickly.

Example conceptual response:

```json
{
  "document_id": "...",
  "job_id": "...",
  "status": "queued"
}
```

---

# 11. Worker Architecture

The worker consumes ingestion jobs.

```text
Redis
 ↓
Worker
 ↓
Job
 ↓
Document Processor
```

The worker should update job state as it progresses.

```text
QUEUED
 ↓
PARSING
 ↓
CLEANING
 ↓
CHUNKING
 ↓
EMBEDDING
 ↓
INDEXING
 ↓
COMPLETED
```

Failure:

```text
Any stage
 ↓
FAILED
 ↓
Retry
```

Retries must be safe.

---

# 12. Idempotent Ingestion

Use:

```text
content hash
+
document/version identity
+
job identity
```

to prevent accidental duplicate processing.

If:

```text
same source
+
same version
```

is submitted twice, the system should detect it.

Do not blindly generate duplicate chunks and vectors.

---

# 13. Document Parsing Architecture

The parser layer should normalize heterogeneous sources.

```text
PDF
DOCX
HTML
Markdown
CSV
URL
```

becomes:

```text
CanonicalDocument
```

The canonical representation might contain:

```text
Document
 ├── metadata
 └── blocks[]
      ├── heading
      ├── paragraph
      ├── table
      ├── list
      ├── code
      └── image
```

This is the key abstraction between parsing and retrieval.

---

# 14. Docling

Docling is the primary document-understanding/normalization candidate.

It can handle multiple document formats and preserve structural information such as:

- reading order
- layout
- tables
- headings
- document structure

Use it as the main normalization layer where appropriate.

Individual libraries can still be used for specialized tasks.

---

# 15. OCR Architecture

OCR is a first-class component.

```text
Page
 ↓
Text quality analysis
 ↓
Does usable native text exist?
 ├── Yes → Native extraction
 └── No  → OCR
```

OCR provider abstraction:

```text
OCRProvider
    │
    ├── RapidOCR
    ├── Tesseract
    ├── PaddleOCR
    └── Advanced vision OCR
```

Start with:

```text
RapidOCR
```

and use:

```text
Tesseract
```

as a fallback.

Advanced OCR engines can be introduced later after benchmarking.

---

# 16. Why Adaptive OCR?

OCR is expensive compared with extracting an existing text layer.

Consider a 100-page document:

```text
Pages 1–70 → digital
Pages 71–75 → scanned
Pages 76–100 → digital
```

A good pipeline performs:

```text
70 pages → native extraction
5 pages → OCR
25 pages → native extraction
```

rather than:

```text
100 pages → OCR
```

This reduces:

- compute
- latency
- processing cost

---

# 17. OCR Confidence

OCR output can include:

```text
text
confidence
bounding boxes
page
language
engine
```

If confidence is low:

```text
RapidOCR
 ↓
low confidence
 ↓
fallback OCR
```

Future design:

```text
RapidOCR
 ↓
confidence
 ├── high → accept
 └── low → second engine
```

Do not add this complexity until the baseline OCR pipeline works.

---

# 18. URL Ingestion

If users can submit webpages:

```text
URL
 ↓
URL validation
 ↓
SSRF protection
 ↓
Fetch
 ↓
HTML extraction
 ↓
Canonical document
```

Never allow unrestricted internal-network requests.

Block:

- localhost
- private IP ranges
- internal service addresses
- cloud metadata endpoints
- unsafe redirects

Revalidate redirects too.

---

# 19. Cleaning Pipeline

Raw parser output often contains:

- repeated headers
- footers
- navigation
- duplicated text
- whitespace noise
- OCR artifacts

Pipeline:

```text
Parsed document
 ↓
Normalize whitespace
 ↓
Remove repeated boilerplate
 ↓
Normalize headings
 ↓
Repair text artifacts
 ↓
Canonical clean representation
```

Keep cleaning deterministic where possible.

---

# 20. Chunking Architecture

Chunking should be structure-aware.

Instead of:

```text
characters 0–1000
characters 1000–2000
```

use:

```text
Document
 ↓
Sections
 ↓
Paragraphs
 ↓
Tables/lists
 ↓
Token-aware chunking
```

Chunk metadata:

```text
chunk_id
document_id
version_id
text
page_number
heading_path
token_count
block_types
metadata
```

---

# 21. Contextual Chunking

The system can enrich a chunk with its structural context.

Example:

```text
Employee Policies
  >
Remote Work
  >
International Work
```

then:

```text
Employees working outside their home country must obtain prior approval.
```

becomes a contextually meaningful retrieval unit.

Benchmark this instead of assuming it always improves retrieval.

---

# 22. Embedding Architecture

Use an interface:

```text
EmbeddingProvider
```

Possible implementations:

```text
LocalEmbeddingProvider
APIEmbeddingProvider
```

The rest of the system should only know:

```text
embed(texts)
```

Important metadata:

```text
embedding_model
embedding_version
embedding_dimension
```

Changing the model may require rebuilding the vector index.

---

# 23. Qdrant Architecture

Each vector point contains:

```text
id
vector
payload
```

Payload should contain filtering information:

```text
organization_id
document_id
version_id
page
document_type
language
created_at
heading_path
```

A vector search should combine semantic similarity with payload filtering.

Conceptually:

```text
query vector
+
organization_id = current tenant
+
optional metadata filters
```

---

# 24. Lexical Search Architecture

Use PostgreSQL Full-Text Search initially.

The lexical index should support exact/keyword-heavy queries.

Good examples:

```text
TR-19
Policy 7.4.2
AWS-SEC-004
```

Later, OpenSearch/Elasticsearch can be introduced if scale requires it.

---

# 25. Hybrid Retrieval

Run two retrieval paths:

```text
                 Query
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
      BM25                Dense
        │                   │
        ▼                   ▼
   lexical ranks       semantic ranks
        │                   │
        └─────────┬─────────┘
                  ▼
                 RRF
                  ↓
            Candidate list
```

Keep the retrieval components independent so they can be benchmarked separately.

---

# 26. Reciprocal Rank Fusion

RRF combines ranked lists without requiring scores from different systems to be directly comparable.

This matters because:

```text
BM25 score
```

and:

```text
vector similarity score
```

do not necessarily have compatible scales.

RRF operates primarily on rank positions.

The implementation should be tested independently.

---

# 27. Reranking

Initial retrieval may return:

```text
50 candidates
```

Reranking evaluates:

```text
query + candidate
```

and produces a more precise relevance score.

Pipeline:

```text
Dense
+
BM25
 ↓
RRF
 ↓
Top 50
 ↓
Cross-encoder
 ↓
Top 10
```

The reranker is a precision optimization after broad candidate retrieval.

---

# 28. Context Builder

The context builder is responsible for the final LLM input.

It should consider:

```text
relevance score
token budget
duplicate chunks
document diversity
metadata filters
source version
```

Example:

```text
Top 10
 ↓
Remove duplicates
 ↓
Apply score threshold
 ↓
Token budget
 ↓
Top 5–8
```

This component should be deterministic and heavily tested.

---

# 29. Query Understanding

The query analyzer can produce:

```json
{
  "query_type": "policy_lookup",
  "requires_retrieval": true,
  "filters": {
    "document_type": ["policy"]
  }
}
```

It may determine:

- query type
- filters
- retrieval requirement
- need for rewriting

Do not use an LLM where a deterministic rule is sufficient.

---

# 30. Query Rewriting

For difficult queries:

```text
"What are rules for international remote work?"
```

may produce multiple retrieval formulations:

```text
international remote work policy
working remotely from foreign country
cross-border employee work policy
```

But rewriting introduces:

- latency
- token cost
- possible query drift

Therefore the system should only rewrite when useful.

---

# 31. LLM Architecture

Use an abstraction:

```text
LLMProvider
```

Potential implementations:

```text
OpenAICompatibleProvider
LocalLLMProvider
OtherProvider
```

The retrieval system should not contain provider-specific code.

LLM configuration should include:

```text
model
temperature
max_tokens
timeout
retry_policy
```

---

# 32. Grounded Generation

The LLM receives:

```text
System instructions
+
User query
+
Retrieved evidence
```

The system instructions should enforce:

```text
Use supplied evidence.
Do not invent unsupported facts.
State when evidence is insufficient.
Produce citation IDs.
```

Use structured output whenever supported.

---

# 33. Citation Resolution

The LLM should output identifiers:

```text
chunk_123
chunk_456
```

The backend resolves them:

```text
chunk_id
 ↓
chunk
 ↓
document version
 ↓
page
 ↓
section
```

This prevents the model from inventing source metadata.

---

# 34. Citation Data Model

Conceptually:

```text
message_citations
    message_id
    chunk_id
```

The chunk itself links to:

```text
document_version
```

Therefore:

```text
message
 ↓
citation
 ↓
chunk
 ↓
document version
 ↓
source file
```

This creates an auditable chain.

---

# 35. Chat Architecture

```text
React
 ↓
POST /chat
 ↓
Authentication
 ↓
Organization context resolution
 ↓
Conversation retrieval
 ↓
Query processing
 ↓
Retrieval pipeline
 ↓
Context builder
 ↓
LLM
 ↓
SSE
 ↓
React
```

Store the final assistant message and citation relationships.

---

# 36. Conversation Memory

Don't send unlimited history.

Use:

```text
conversation summary
+
recent messages
+
current query
+
retrieved evidence
```

A token budget should determine how much history is included.

Long conversations can be summarized.

---

# 37. Streaming Architecture

Use Server-Sent Events.

Conceptually:

```text
Server
 │
 ├── event: retrieval_started
 ├── event: context_ready
 ├── event: token
 ├── event: token
 ├── event: citation
 ├── event: token
 └── event: completed
```

This gives the frontend enough information to render a responsive experience.

---

# 38. Redis Architecture

Redis should have explicit responsibilities.

### Queue

```text
document ingestion jobs
```

### Rate limiting

```text
user / tenant / IP
```

### Cache

Potentially:

```text
retrieval results
```

### Locks

For operations where concurrent processing must be prevented.

Avoid using Redis as the permanent source of truth.

---

# 39. Evaluation Architecture

The evaluation system should run the actual retrieval/generation pipeline.

```text
Dataset
 ↓
Evaluation Runner
 ↓
Question
 ↓
Retrieval
 ↓
Generation
 ↓
Metrics
 ↓
Report
```

Each run should store:

```text
configuration
model versions
retrieval configuration
metrics
timestamp
```

This makes experiments reproducible.

---

# 40. Evaluation Dataset

Each test case can contain:

```json
{
  "question": "...",
  "expected_answer": "...",
  "expected_documents": ["..."],
  "expected_chunks": ["..."]
}
```

This allows independent evaluation of:

```text
retrieval
generation
citations
```

---

# 41. Observability Architecture

Use distributed traces.

```text
Request
 │
 ├── auth
 ├── query analysis
 ├── rewrite
 ├── BM25
 ├── dense
 ├── RRF
 ├── reranking
 ├── context
 └── LLM
```

Each span should include safe, useful metadata.

Do not log secrets.

Be careful about logging full enterprise document contents.

---

# 42. Metrics

Operational metrics:

```text
request_count
error_count
request_latency
retrieval_latency
reranker_latency
llm_latency
queue_latency
worker_failures
```

AI metrics:

```text
retrieval_recall
reranker_scores
faithfulness
citation_accuracy
```

Cost:

```text
input_tokens
output_tokens
embedding_tokens
estimated_cost
```

---

# 43. Security Architecture

Security boundaries:

```text
Browser
 ↓
HTTPS
 ↓
Authentication              who is this?          → user_id
 ↓
Organization context        where are they?       → membership, must be active
 ↓
Authorization               may they do this?     → role → permission, default deny
 ↓
Service
 ↓
Data Layer                  isolation filter injected, not optional
```

The four steps are distinct and none of them covers for another. Authentication
without organization context lets a valid user act on a tenant they do not belong to.
Organization context without authorization lets any member perform any action inside
their tenant. Authorization without the data-layer filter lets a permitted action
return another tenant's rows. Section 7.9 has the failure cases in full.

Never trust:

- organization IDs supplied by clients — they are lookup keys for a membership check,
  never an assertion of access
- roles or permissions carried in a token — they go stale the moment a membership
  changes, so they are resolved per request (7.8)
- document IDs without authorization checks
- citation IDs without organization validation
- URL destinations
- uploaded MIME types
- `account_type` as an authorization input — it is billing metadata and carries no
  permissions (7.5)

All should be validated server-side.

Authorization rules that hold across every endpoint:

| Rule | Consequence of breaking it |
|---|---|
| A route with no declared permission denies all access | A forgotten declaration locks an endpoint instead of opening one |
| No active membership returns `404`, not `403` | `403` confirms the organization exists and leaks the tenant id space |
| Insufficient role returns `403` | Membership is already established, so precision is safe and useful |
| Every cross-tenant `super_admin` read is audited | Otherwise "did anyone read this customer's data?" is unanswerable |
| Cross-tenant writes are refused outright | One mistaken operation would damage several customers at once |

---

# 44. Error Handling

Errors should be categorized.

Examples:

```text
ValidationError
AuthenticationError
AuthorizationError
StorageError
ParsingError
OCRError
EmbeddingError
VectorStoreError
LLMError
RateLimitError
```

API responses should be consistent.

Workers should persist useful error information without exposing internal secrets.

---

# 45. Reliability Model

For ingestion:

```text
At-least-once execution
+
idempotent processing
```

is a practical target.

If a worker crashes:

```text
Job remains retryable
```

If the same job executes twice:

```text
No duplicate final state
```

This is more important than pretending distributed execution is exactly-once.

---

# 46. Performance Architecture

Potential bottlenecks:

```text
PDF parsing
OCR
embedding
vector search
reranking
LLM generation
database queries
```

Do not optimize before measuring.

Track stage-level latency:

```text
Total
 ├── Parse
 ├── OCR
 ├── Chunk
 ├── Embed
 ├── Search
 ├── Rerank
 └── LLM
```

---

# 47. Scaling Strategy

At low traffic:

```text
1 API
1 worker
1 Redis
1 PostgreSQL
1 Qdrant
```

At higher traffic:

```text
Load Balancer
 ├── API 1
 ├── API 2
 └── API 3

Workers
 ├── Worker 1
 ├── Worker 2
 └── Worker 3
```

Heavy workloads such as OCR/embedding can eventually receive dedicated worker pools.

For example:

```text
general workers
OCR workers
embedding workers
```

Only introduce separate pools when measurements justify them.

---

# 48. Data Consistency

Important relationships:

```text
Document
 ↓
Version
 ↓
Chunks
 ↓
Vectors
```

If a document version is deleted or re-indexed, the system must know what happens to:

```text
chunks
vectors
citations
evaluation references
```

Citations should remain reproducible for historical messages whenever possible.

---

# 49. Reindexing

When changing:

```text
embedding model
chunking algorithm
normalization
metadata
```

you may need re-indexing.

Therefore store:

```text
chunking_version
embedding_model
embedding_version
pipeline_version
```

A future reindexing job can then identify outdated vectors.

---

# 50. Versioned Retrieval Configuration

A retrieval result depends on:

```text
embedding model
chunking
top K
BM25 configuration
RRF parameters
reranker
context limits
```

Store configuration/version information in evaluation runs.

This makes experiments reproducible.

---

# 51. Final End-to-End Ingestion Flow

```text
                    File Upload
                         │
                         ▼
                  FastAPI API
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Cloudflare R2          PostgreSQL
              │                     │
              └──────────┬──────────┘
                         ▼
                    Redis Queue
                         │
                         ▼
                   Worker
                         │
                         ▼
                File Inspection
                         │
                         ▼
                Document Parser
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         Native Text               OCR
              │                     │
              └──────────┬──────────┘
                         ▼
                  Normalization
                         │
                         ▼
                     Cleaning
                         │
                         ▼
                Structural Chunking
                         │
                         ▼
                    Embeddings
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           Qdrant                 BM25
              │                     │
              └──────────┬──────────┘
                         ▼
                      Indexed
```

---

# 52. Final End-to-End Query Flow

```text
User
 │
 ▼
React
 │
 ▼
FastAPI
 │
 ├── Authentication
 ├── Authorization
 └── Organization Context
 │
 ▼
Query Analyzer
 │
 ▼
Optional Rewrite
 │
 ├───────────────┐
 ▼               ▼
BM25           Dense
 │               │
 └───────┬───────┘
         ▼
        RRF
         ▼
      Top 50
         ▼
     Reranker
         ▼
      Top 10
         ▼
 Context Builder
         ▼
      Top 5–8
         ▼
        LLM
         ▼
Answer + Citation IDs
         ▼
Citation Resolver
         ▼
SSE Stream
         ▼
React
```

---

# 53. Final Deployment Architecture

```text
                         Internet
                            │
                            ▼
                       Cloudflare
                       │       │
                       │       └── R2
                       │
                       ▼
                      Vercel
                       │
                       ▼
                   React Frontend
                       │
                       │ HTTPS
                       ▼
                  ┌─────────────┐
                  │   FastAPI   │
                  └──────┬──────┘
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
     PostgreSQL        Redis          Qdrant
          │              │
          │              ▼
          │          Worker(s)
          │              │
          │              ▼
          │       Document Processing
          │              │
          │              ▼
          │          Embeddings
          │
          └──────────────┐
                         ▼
                    Evaluation
                         │
                         ▼
                OpenTelemetry
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          Prometheus              Grafana
```

---

# 54. Architectural Trade-offs

## Qdrant vs pgvector

Qdrant:

- dedicated vector database
- strong vector-search functionality
- useful portfolio experience

pgvector:

- simpler infrastructure
- fewer services
- excellent for smaller systems

Start with Qdrant, then optionally implement a vector-store interface that allows pgvector experimentation.

## PostgreSQL FTS vs OpenSearch

PostgreSQL FTS:

- simpler
- fewer services
- good for initial deployment

OpenSearch:

- more specialized search capabilities
- more operational complexity

Start with PostgreSQL FTS.

## SSE vs WebSockets

SSE:

- simple
- ideal for server-to-client token streaming
- easy to integrate with HTTP APIs

WebSockets:

- bidirectional
- more complexity

Start with SSE.

## Modular monolith vs microservices

Start modular.

Extract services only after identifying a real scaling/deployment reason.

## Local vs API models

Local models:

- potentially lower marginal cost
- privacy
- more operational complexity

API models:

- simpler
- strong quality
- variable cost
- external dependency

Use provider abstractions so the architecture can support both.

---

# 55. Core Interfaces

The implementation should eventually revolve around interfaces such as:

```text
DocumentParser
OCRProvider
DocumentNormalizer
Chunker
EmbeddingProvider
VectorStore
LexicalRetriever
Reranker
LLMProvider
StorageProvider
Queue
```

This makes the system replaceable and testable.

For example:

```text
VectorStore
    ├── QdrantVectorStore
    └── PgVectorStore
```

and:

```text
OCRProvider
    ├── RapidOCRProvider
    └── TesseractProvider
```

The retrieval pipeline should depend on abstractions, not concrete vendors.

---

# 56. Important Non-Goals

Do not initially build:

- Kubernetes
- dozens of microservices
- custom LLM training
- custom vector database
- custom OCR model
- elaborate agent framework
- unnecessary event-bus infrastructure

The goal is to demonstrate strong engineering decisions, not maximum technology count.

---

# 57. What the Architecture Should Demonstrate

By the end, the repository should visibly demonstrate:

```text
AI Engineering
 ├── RAG
 ├── Retrieval
 ├── Embeddings
 ├── Reranking
 ├── Grounding
 └── Evaluation

Backend Engineering
 ├── FastAPI
 ├── PostgreSQL
 ├── Redis
 ├── APIs
 └── Authentication

Distributed Systems
 ├── Queues
 ├── Retries
 ├── Idempotency
 ├── Caching
 └── Scaling

Information Retrieval
 ├── BM25
 ├── Dense retrieval
 ├── RRF
 ├── Reranking
 └── Ranking metrics

Document AI
 ├── Parsing
 ├── Layout
 ├── OCR
 ├── Tables
 └── Chunking

Production Engineering
 ├── Docker
 ├── CI/CD
 ├── Observability
 ├── Security
 └── Deployment
```

The resulting project should be something you can defend in an AI Engineer interview from both the **model/retrieval side** and the **software/system engineering side**.
