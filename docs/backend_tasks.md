# Backend Implementation Tasks

Derived from `docs/plan.md` and `docs/architecture.md`. Ordered by implementation sequence — earlier phases are hard dependencies for later ones. Each task is ranked **High / Medium / Low** difficulty based on conceptual complexity + failure surface, not raw time.

Every task includes a plain-language description of what it does and why it matters.

**Status:** Phase 0 ✅ · Phase 1 ✅ · Phase 2 ✅ · Phase 3 next — 3 of 34 phases complete

> **Ordering was audited and corrected.** 14 tasks were previously listed before their own dependencies. See [Sequencing Fixes Applied](#sequencing-fixes-applied) at the end for the full list of what moved and why.

---

## Phase 0 — Backend Foundation ✅

| # | Task | Difficulty |
|---|---|---|
| 1 | Remove/relocate stray root `pyproject.toml` + `src/` stub | Low |
| 2 | Create `backend/` directory skeleton | Low |
| 3 | Initialize `backend/pyproject.toml` (uv) with Python version pin | Low |
| 4 | Add core deps: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` | Low |
| 5 | Verify `uv run python -c "import fastapi"` works | Low |
| 6 | Configure linting (ruff) + formatting (ruff format) | Low |
| 7 | Configure backend `.env.example` | Low |

**In plain words:** Set up an empty, tidy workspace before writing any code. Pin the Python version so everyone runs the same one, install the web framework, and turn on the tools that auto-format code and catch typos. Doing this on an empty project takes minutes; retrofitting it onto thousands of lines later means a giant reformatting commit and months of inconsistent style.

---

## Phase 1 — Local Infrastructure (Docker Compose) ✅

| # | Task | Difficulty |
|---|---|---|
| 1 | `docker-compose.yml` service defs for Postgres, Redis, Qdrant (+ PgBouncer) | Medium |
| 2 | Add healthchecks for each service | Low |
| 3 | Configure named volumes for persistence | Low |
| 4 | Configure `infrastructure/postgres/init/` bootstrap scripts | Low |
| 5 | Wire `.env` variables into compose (ports, creds) | Low |
| 6 | Verify all services reachable from host CLI | Medium |

**In plain words:** Your app needs three databases to talk to. Rather than installing them on your laptop by hand, you describe them in one file and Docker starts all of them with a single command. **Healthchecks** matter because a container saying "running" only means the process didn't crash — healthy means it actually answers. **Named volumes** keep your data when containers restart. **Init scripts** install database extensions automatically on first boot, because only the admin account can install them and that account only exists at creation time.

---

## Phase 2 — FastAPI App Skeleton + Config ✅

| # | Task | Difficulty |
|---|---|---|
| 1 | Fix `backend/pyproject.toml` packaging — `package = false`, drop `build-system`/`project.scripts`, delete `src/` stub, add pytest `pythonpath` | Low |
| 2 | `api/config/settings.py` — Pydantic `BaseSettings`, env validation | Medium |
| 3 | `api/config/logging.py` — structured JSON logging (adds `structlog`) | Medium |
| 4 | `api/routes/v1/health.py` — `/health` endpoint | Low |
| 5 | `api/middleware/request_id.py` — request ID generation/propagation | Medium |
| 6 | `api/main.py` app factory — assembles settings, logging, middleware, routers | Low |
| 7 | ASGI startup/shutdown lifecycle hooks (`lifespan` in `main.py`) | Medium |
| 8 | Verify uvicorn dev server + hot reload | Low |

**1. Packaging fix.** `uv init` set the project up as a *library* meant to be published and installed by others. You're building an application that runs in a container — nobody will ever `pip install` it. Right now Python can't even find your code. This makes your files importable.

**2. Settings.** One typed object holding all configuration, checked at startup. Without it, a typo like `DATABSE_URL` silently returns nothing and the app dies twenty minutes later with a confusing error. With it, bad config crashes immediately and tells you exactly which value is wrong. It's also the seam that lets the same code read a local file in development and platform-injected secrets in the cloud.

**3. Structured logging.** Logs as machine-readable records instead of sentences. `"User 42 uploaded doc 91"` can't be searched or counted; `{"event":"document.uploaded","user_id":42}` can be filtered and graphed in any log tool.

**4. Health endpoint.** A cheap URL that answers "are you alive?" Load balancers and Docker poll it constantly. Keep it dependency-free — if it checked the database, a slow database would make your load balancer kill perfectly healthy servers.

**5. Request ID middleware.** Stamps every incoming request with a unique ID and attaches it to every log line that request produces. With 50 requests happening at once, logs are interleaved noise. With this, you filter one ID and see that single request's entire journey. When a user says "it broke at 2pm", the ID from their response takes you straight there.

**6. App factory.** The assembly point that builds the app object and bolts on everything above. It's a *function* rather than a global so tests can build a fresh app with different settings.

**7. Lifecycle hooks.** Code that runs once when the server starts and once when it stops. Database connection pools get opened here and closed cleanly on shutdown — otherwise every deploy leaks connections and drops in-flight work.

**8. Verify.** Start the server, hit the health endpoint, confirm you get a request ID header and that editing a file reloads automatically.

---

## Phase 3 — Database Layer (SQLAlchemy + Alembic)

| # | Task | Difficulty |
|---|---|---|
| 1 | `api/db/base.py` — declarative base | Low |
| 2 | `api/db/session.py` — async engine + session-per-request | Medium |
| 3 | PgBouncer-compatible engine config (`NullPool`, `statement_cache_size=0`) | High |
| 4 | Alembic init + config wiring to `Settings` (separate direct-to-Postgres URL) | Medium |
| 5 | First models: `User`, `Tenant` | Medium |
| 6 | First migration (autogenerate + review) | Medium |
| 7 | Repository pattern base class | Medium |
| 8 | Verify migration round-trip on fresh DB | Low |

**1. Declarative base.** The shared parent class every database table inherits from. It's what lets the toolkit discover all your tables automatically.

**2. Session management.** A "session" is one conversation with the database. The rule is one session per web request, opened at the start and closed at the end — so a crash mid-request rolls back cleanly instead of leaving half-written data.

**3. PgBouncer compatibility.** Your connection pooler hands out a *different* database connection for each transaction. The async driver's default optimization assumes it keeps the same one, so it breaks intermittently with confusing errors. Two settings disable that assumption. Getting this wrong produces bugs that appear randomly under load and are very hard to trace.

**4. Alembic.** Version control for your database structure. Instead of manually running `ALTER TABLE` on every machine, you write migration files that apply the same changes everywhere in the same order. Migrations must connect *directly* to Postgres, bypassing the pooler, because they need a connection that stays put.

**5. First models.** `User` and `Tenant` as Python classes that map to database tables.

**6. First migration.** Auto-generate the SQL from your models — then **read it before running it**. Auto-generation regularly gets things subtly wrong, and a bad migration on a live database is expensive.

**7. Repository base class.** A thin layer between your business logic and raw database queries, so queries live in one place instead of being scattered through the app. Phase 5 hangs mandatory tenant filtering off this class — which is why it's worth having.

**8. Verify round-trip.** Prove migrations run cleanly on a brand-new empty database, and that you can undo them. If this only works on *your* machine, CI and production will both fail.

---

## Phase 4 — Authentication

| # | Task | Difficulty |
|---|---|---|
| 1 | `api/auth/password.py` — hashing (argon2/bcrypt) | Low |
| 2 | `api/auth/jwt.py` — token encode/decode, claims, expiry | Medium |
| 3 | Access token + refresh token lifecycle | High |
| 4 | `api/schemas/auth.py` — request/response models | Low |
| 5 | `api/services/auth_service.py` | Medium |
| 6 | `api/routes/v1/auth.py` — register/login/refresh/logout routes | Medium |
| 7 | `api/auth/dependencies.py` — `get_current_user` injection | Medium |
| 8 | Redis client setup (needed for revocation) | Low |
| 9 | Token revocation / logout invalidation strategy | High |
| 10 | Security tests: expired/invalid/missing token rejection | Medium |

**1. Password hashing.** Never store real passwords. Store a scrambled version that can't be reversed. Argon2 and bcrypt are deliberately slow, which makes mass guessing impractical.

**2. JWT tokens.** After login the user gets a signed token they send with every request. The signature proves it came from you and wasn't edited, so you don't have to look up a session in the database every time.

**3. Access + refresh tokens.** Two tokens with different lifespans. The access token expires in minutes, so a stolen one is quickly useless. The refresh token lives for days and quietly gets new access tokens, so users aren't logged out constantly. Getting the handoff right is genuinely tricky — it's where most auth bugs live.

**4. Schemas.** The shapes of the JSON going in and out. Defined before the routes, because the routes use them.

**5. Auth service.** The actual logic — check the password, issue tokens, refresh them. Kept separate from routes so it can be tested without HTTP and reused elsewhere.

**6. Routes.** The URLs (`/register`, `/login`, `/refresh`, `/logout`) that call the service. They come *after* the service, because they depend on it.

**7. `get_current_user`.** A reusable piece that any endpoint can request to say "this route requires login." Handles token reading and rejection in one place.

**8. Redis client.** Logout needs somewhere fast to record "this token is dead." Redis is already running from Phase 1, but nothing connects to it yet.

**9. Revocation.** JWTs are valid until they expire — that's their weakness. If a user logs out or an account is compromised, you need a way to kill a token immediately. That means keeping a deny-list, which partly undoes the "no lookups" benefit, so the design trade-off needs thought.

**10. Security tests.** Deliberately attack your own auth: expired tokens, edited tokens, missing tokens, tokens signed with the wrong key. All must be rejected. Auth bugs are silent — nothing crashes, the wrong people just get in.

---

## Phase 5 — Multi-Tenancy

| # | Task | Difficulty |
|---|---|---|
| 1 | `Organization` + `Membership` models, extend `Tenant` | Medium |
| 2 | Migration for tenancy models | Low |
| 3 | `api/middleware/tenant.py` — tenant context resolution per request | High |
| 4 | Tenant-scoped base repository (mandatory `tenant_id` filter) | High |
| 5 | Retrofit all repositories to require `tenant_id` | Medium |
| 6 | Cross-tenant isolation test suite (adversarial: guessed IDs) | High |
| 7 | Role-based access control (RBAC) scaffold | High |

**In plain words:** Multiple companies use the same running application, and none of them may ever see another's data. The `Tenant` model already exists from Phase 3; this phase adds organizations and membership, then makes isolation *structural*.

**3. Tenant middleware.** Works out which company the request belongs to, once, at the entrance, and makes it available everywhere downstream.

**4–5. Mandatory filtering.** The critical design idea: make it *impossible* to write a query that forgets the tenant filter, rather than relying on developers remembering. One forgotten `WHERE tenant_id = ?` is a full data breach. Building the filter into the base repository means every query inherits it by default.

**6. Adversarial tests.** Not "does it work" but "can I break in" — log in as company A, guess company B's document IDs, and confirm you get denied every time. This is the single most important test suite in the project.

**7. RBAC.** Beyond which company you belong to: what are you allowed to do inside it? Admins delete, viewers read. A scaffold now avoids retrofitting permissions across every endpoint later.

---

## Phase 6 — Document Management

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/storage/base.py` — `StorageProvider` interface | Low |
| 2 | `shared/storage/r2.py` — R2/S3-compatible impl | Medium |
| 3 | `Document` / `DocumentVersion` models + migration | Medium |
| 4 | `api/schemas/documents.py` | Low |
| 5 | File validation (MIME, extension, size, magic-byte content sniffing) | Medium |
| 6 | Content-hash dedup logic | Medium |
| 7 | `api/services/document_service.py` | Medium |
| 8 | `api/routes/v1/documents.py` — upload/list/delete/download/metadata | Medium |
| 9 | Multipart upload handling + streaming to storage | High |
| 10 | Tenant isolation on all document endpoints | Medium |

**1–2. Storage interface + implementation.** Files don't go in the database — they go to cloud object storage. You define an interface first so the rest of the app never knows or cares which provider you use, and swapping providers later touches one file.

**3. Document versions.** Uploading a revised file shouldn't destroy the old one. Citations must keep pointing at the exact version they were generated from, or answers silently become wrong.

**5. File validation.** Never trust an uploaded file. Check its real content, not just its name — a file called `report.pdf` can contain anything. **Magic bytes** means reading the first few bytes to identify the true type. (This was previously deferred to Phase 27; it belongs here, with the upload code.)

**6. Content-hash dedup.** Fingerprint each file's contents. If the same document is uploaded twice, store it once. Saves storage, and more importantly avoids paying to parse and embed the same content repeatedly.

**9. Streaming uploads.** A 500MB file must not be loaded into memory. Stream it through in chunks — otherwise a few concurrent large uploads take the server down.

---

## Phase 7 — Async Ingestion (Job Infrastructure)

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/queue/base.py` — `Queue` interface | Low |
| 2 | `shared/queue/redis_queue.py` — Redis-backed impl | Medium |
| 3 | `IngestionJob` model + state machine + migration | High |
| 4 | Job enqueue on document upload | Medium |
| 5 | `workers/ingestion/main.py` — worker loop/consumer | High |
| 6 | Idempotency guarantees (content hash + job identity) | High |
| 7 | Retry logic + exponential backoff | High |
| 8 | Job status polling endpoint | Low |
| 9 | Dead-letter handling for permanently failed jobs | Medium |

**In plain words:** Processing a document takes minutes. Nobody waits minutes for an upload button. So the upload returns instantly and the real work happens in the background.

**1–2. Queue.** A to-do list the web server writes to and background workers read from.

**3. State machine.** Every job moves through defined states (`PENDING → QUEUED → PROCESSING → COMPLETED/FAILED/RETRYING`). Being strict about legal transitions is what stops jobs getting silently stuck in limbo.

**5. Worker.** A separate program that pulls jobs and does the heavy work. Separate from the API so slow processing never slows down the website.

**6. Idempotency.** Guarantee that processing the same job twice causes no harm. Crashes, restarts, and retries all cause duplicate delivery — this is not an edge case, it's normal operation. Listed *before* retries deliberately: adding retries without idempotency multiplies your data corruption.

**7. Retry with backoff.** Failures are often temporary. Retry, but wait longer each time — hammering a struggling service keeps it down.

**9. Dead-letter handling.** Some jobs will never succeed. Set them aside for inspection instead of retrying forever and clogging the queue.

---

## Phase 8 — Document Parsing

| # | Task | Difficulty |
|---|---|---|
| 1 | `CanonicalDocument` data model (blocks: heading/paragraph/table/list/code/image) | High |
| 2 | `workers/ingestion/parsers/base.py` — `DocumentParser` interface | Low |
| 3 | `markdown_parser.py` (validates the interface cheaply) | Low |
| 4 | `csv_parser.py` | Low |
| 5 | Docling integration evaluation/adoption decision | High |
| 6 | `pdf_parser.py` | High |
| 7 | `docx_parser.py` | Medium |
| 8 | `html_parser.py` | Medium |
| 9 | `web_parser.py` (URL fetch + extraction) | Medium |
| 10 | SSRF protection for URL ingestion (block localhost/private IPs/metadata endpoints) | High |
| 11 | Parser router (file-type detection → correct parser) | Medium |

**1. CanonicalDocument — do this first.** One common format that every file type gets converted into. PDFs, Word docs, and web pages all become the same structure, so everything downstream is written once instead of per format. It's listed first because the parser interface refers to it, and every parser produces it — designing it after writing parsers means rewriting them all.

**3–4. Easy parsers first.** Markdown and CSV are simple. Building them early proves the interface design works *before* you invest in the hard PDF parser against a design that might be wrong.

**5. Docling decision before PDF work.** Docling is an existing library that may replace much of your PDF parsing. Evaluate it *before* building a PDF parser by hand — deciding afterward means throwing away the hardest work in the phase.

**6. PDF parsing.** The hard one. PDFs describe visual positions, not meaning — there's often no real notion of "paragraph" or "table" in the file, only text at coordinates. Reconstructing structure is genuinely difficult.

**10. SSRF protection — ships with the URL fetcher.** If users can submit URLs, they can submit `http://localhost` or your cloud provider's internal metadata address, and your server will happily fetch them and hand back the contents — including cloud credentials. This must land in the same phase as the feature that creates the risk, not deferred to Phase 27.

**11. Parser router.** Looks at a file and picks the right parser.

---

## Phase 9 — OCR

| # | Task | Difficulty |
|---|---|---|
| 1 | `workers/ingestion/ocr/base.py` — `OCRProvider` interface | Low |
| 2 | Text quality detection (native text vs scanned) | High |
| 3 | `rapidocr_provider.py` | Medium |
| 4 | `tesseract_provider.py` (fallback) | Medium |
| 5 | `workers/ingestion/ocr/router.py` — per-page routing (native text vs OCR) | High |
| 6 | Confidence-based fallback logic | High |

**In plain words:** OCR reads text out of images. Scanned documents are pictures of pages — without OCR they're invisible to search.

**2. Quality detection.** Decide whether a page already contains real text or is just an image. This is the money-saver: OCR is slow and expensive, and most documents don't need it.

**3–4. Two engines.** A fast primary and a slower, sometimes-better fallback.

**5. Per-page routing.** Documents are frequently mixed — 50 normal pages and 3 scanned ones. Deciding per page rather than per document avoids OCR-ing the whole file for the sake of three pages. (The old separate task "avoid full-document OCR" was the same idea stated twice; it's merged here.)

**6. Confidence fallback.** When the fast engine returns garbage, it usually knows — low confidence scores. Use that to retry with the better engine instead of storing nonsense.

---

## Phase 10 — Normalization & Cleaning

| # | Task | Difficulty |
|---|---|---|
| 1 | `workers/ingestion/normalization/canonical_document.py` finalization | Medium |
| 2 | `normalizer.py` — headings/paragraphs/tables/lists normalization | High |
| 3 | `workers/ingestion/cleaning/cleaner.py` — whitespace/artifact cleanup | Medium |
| 4 | `headers.py` / `footers.py` — repeated header/footer detection+removal | High |
| 5 | `boilerplate.py` — duplicate/nav content removal | Medium |
| 6 | Deterministic cleaning pipeline tests | Medium |

**In plain words:** Raw parser output is messy. This phase makes it consistent.

**4. Header/footer removal.** A 200-page report repeats "Confidential — Acme Corp" on every page. Left in, that phrase appears in hundreds of search chunks and pollutes every result. Detecting *repetition across pages* is how you find it automatically.

**5. Boilerplate.** Same problem for web pages — navigation menus and cookie banners on every page.

**6. Deterministic tests.** The same input must always produce the same output, byte for byte. If cleaning drifts, your stored chunks stop matching your live pipeline and search quality silently degrades.

---

## Phase 11 — Chunking

| # | Task | Difficulty |
|---|---|---|
| 1 | `workers/ingestion/chunking/base.py` interface | Low |
| 2 | `token_counter.py` | Low |
| 3 | Chunk metadata schema (document_id, version_id, page, heading_path, etc.) | Medium |
| 4 | Stable chunk ID generation | Medium |
| 5 | `structure_chunker.py` — heading/paragraph/table/list-aware | High |
| 6 | `contextual_chunker.py` — heading-path enrichment | High |
| 7 | Chunking benchmark vs naive fixed-size (validate it actually helps) | High |

**In plain words:** Documents are too big to search or feed to an AI whole, so they're cut into pieces. *How* you cut them is one of the biggest quality levers in the whole system.

**2. Token counter — needed first.** Chunkers size their output in tokens, so they can't be written before the thing that counts tokens. (Was previously listed after the chunkers that use it.)

**3–4. Metadata and IDs — also first.** Every chunk must record where it came from, or you can't cite it. Stable IDs mean re-processing the same document produces the same identifiers, so citations survive. Both shape what the chunkers output, so they're decided before the chunkers exist.

**5. Structure-aware chunking.** Cut at natural boundaries — sections, paragraphs, table edges — instead of every N characters. Naive cutting splits sentences and severs tables from their headers.

**6. Contextual enrichment.** A chunk reading "must be approved within 30 days" is meaningless alone. Prepending its heading path — *"Employee Handbook › Leave Policy › Approvals"* — makes it findable and understandable.

**7. Benchmark it.** Measure against dumb fixed-size chunking. Sophisticated chunking is *assumed* to help; sometimes it doesn't. Without measurement you're maintaining complexity for nothing.

---

## Phase 12 — Embedding Infrastructure

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/embeddings/base.py` — `EmbeddingProvider` interface | Low |
| 2 | Model/dimension versioning metadata | Medium |
| 3 | `local.py` — local embedding model impl | Medium |
| 4 | `api.py` — API-based embedding provider | Medium |
| 5 | `factory.py` — provider selection | Low |
| 6 | Batch embedding logic | Medium |
| 7 | Retry + rate limiting | Medium |
| 8 | Embedding cache | Medium |
| 9 | `workers/embeddings/` — batcher + processor worker | High |

**In plain words:** Embeddings turn text into lists of numbers that capture meaning. Similar meanings produce similar numbers, which is what makes search work on concepts rather than exact words — "how do I take time off" finds a document titled "Leave Policy".

**2. Version metadata — moved earlier.** Record which model and how many dimensions produced every stored vector. Different models produce incompatible numbers, and you *will* change models eventually. Without this recorded from day one, you can't tell old vectors from new ones and must re-embed everything blindly. It also determines the vector size Phase 13 configures.

**6. Batching.** Sending 1,000 texts in one call is dramatically faster and cheaper than 1,000 separate calls.

**8. Cache.** Identical text always produces identical vectors. Don't pay twice.

---

## Phase 13 — Vector Search (Qdrant)

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/vector_store/base.py` — `VectorStore` interface | Low |
| 2 | Payload schema design (tenant_id, document_id, version_id, page, etc.) | Medium |
| 3 | Collection/index configuration | High |
| 4 | `qdrant.py` impl (upsert/search/delete/filter) | Medium |
| 5 | Metadata filter integration with vector query | High |

**In plain words:** A vector database finds the numerically closest matches among millions of vectors, fast.

**2–3. Schema and collection config before implementation.** *(Reordered — these were previously after the implementation that depends on them.)* The payload is the extra information stored alongside each vector, and the collection config fixes the vector size and index settings. The implementation writes payloads into a collection, so both must be decided first. Changing either afterward means rebuilding the whole collection.

**5. Filtering + vector search together.** Every query must restrict to one tenant *and* find similar meaning. Doing the filter and the search as separate steps is both slow and, if you get the order wrong, a data leak.

---

## Phase 14 — Lexical Search (BM25)

| # | Task | Difficulty |
|---|---|---|
| 1 | PostgreSQL Full-Text Search setup (tsvector columns, indexes) | Medium |
| 2 | `shared/retrieval/lexical/retriever.py` | Medium |
| 3 | `shared/retrieval/lexical/ranking.py` | Medium |
| 4 | Exact-match/keyword-heavy query test cases | Low |

**In plain words:** Old-fashioned keyword search, running alongside the meaning-based search. It exists because embeddings are genuinely bad at exact strings — error code `E-4021`, a part number, or a person's surname. Semantic search finds things *about* the topic; keyword search finds the literal string. You need both, which is what Phase 15 combines.

---

## Phase 15 — Hybrid Retrieval + RRF

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/retrieval/interfaces.py` — shared retrieval contracts | Medium |
| 2 | `shared/retrieval/fusion/rrf.py` — Reciprocal Rank Fusion implementation | High |
| 3 | RRF unit tests (rank-position correctness, independent of scoring scale) | High |
| 4 | `shared/retrieval/pipeline.py` — orchestration | High |
| 5 | Parallel dense+BM25 execution (async) | Medium |

**2–3. RRF before the pipeline.** *(Reordered — the pipeline orchestrates RRF, so RRF has to exist.)* You now have two ranked lists from two search systems whose scores mean completely different things and can't be compared directly. RRF solves this by ignoring the scores entirely and using only *rank positions* — something ranked #1 by both lists wins. Simple, and it consistently beats more elaborate schemes.

**3. Test it properly.** The whole point is scale-independence. A test that only passes with particular score values is testing the wrong thing.

**5. Run both searches at once.** They're independent, so running them in parallel makes hybrid search cost roughly the same as one search instead of two.

---

## Phase 16 — Reranking

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/retrieval/reranking/base.py` — `Reranker` interface | Low |
| 2 | `shared/retrieval/reranking/cross_encoder.py` impl | High |
| 3 | Top-50 → top-10 pipeline wiring | Medium |
| 4 | Latency benchmarking (reranker is often the bottleneck) | Medium |

**In plain words:** A second, much more careful pass over the top results. The initial search compares the question and documents separately — fast, but approximate. A reranker reads the question *together with* each candidate and judges relevance properly. Far too slow for millions of documents, ideal for the top 50.

**4. Benchmark latency.** This is usually the slowest step in the whole pipeline. Know the cost before it's load-bearing.

---

## Phase 17 — Query Understanding

| # | Task | Difficulty |
|---|---|---|
| 1 | Rule-based vs LLM-based decision policy (avoid LLM where rules suffice) | Medium |
| 2 | `shared/retrieval/query/classifier.py` — query type classification | Medium |
| 3 | `shared/retrieval/query/filters.py` — metadata extraction (date/department/entity) | Medium |
| 4 | `shared/retrieval/query/rewriter.py` — conversational query rewriting | High |

**1. The policy decision comes first.** *(Reordered — it governs how the other three are built.)* For each task here you can use simple rules or call an AI model. Rules are instant and free; models are slow and cost money per call. Deciding the policy up front stops you building three components the expensive way and rewriting them later.

**2. Classification.** "What's our refund policy?" and "compare Q1 and Q2 revenue" need different retrieval strategies.

**4. Query rewriting.** In a conversation, someone asks "what about last year?" — meaningless alone. Rewriting it into "what was revenue last year?" using the chat history is what makes follow-up questions work.

---

## Phase 18 — Context Builder

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/retrieval/context/deduplicator.py` | Medium |
| 2 | `shared/retrieval/context/budget.py` — token budget enforcement | Medium |
| 3 | Document diversity logic | Medium |
| 4 | `shared/retrieval/context/builder.py` — evidence ordering | Medium |
| 5 | Deterministic behavior test suite | Medium |

**In plain words:** Deciding exactly what text gets handed to the AI. There's a hard size limit, so this is a packing problem.

**4. Builder comes last.** *(Reordered — it orchestrates the other three.)*

**1. Deduplication.** The same paragraph often appears in several retrieved chunks. Sending it three times wastes budget that could hold new information.

**2. Budget.** A hard ceiling on how much text you can send. Exceed it and the request simply fails.

**3. Diversity.** Ten chunks from one document give a narrow answer. Forcing spread across sources produces better ones.

**4. Ordering.** Models pay most attention to the beginning and end of what they're given. Where you place the strongest evidence measurably changes answer quality.

---

## Phase 19 — Grounded Generation

| # | Task | Difficulty |
|---|---|---|
| 1 | `shared/llm/base.py` — `LLMProvider` interface | Low |
| 2 | `openai_compatible.py` impl | Medium |
| 3 | `factory.py` — provider selection | Low |
| 4 | System prompt design (grounding constraints, no-invention rules) | High |
| 5 | Prompt injection defense (treat retrieved content as untrusted) | High |
| 6 | Structured output parsing (citation IDs) | Medium |
| 7 | Retry/timeout/fallback provider logic | High |
| 8 | `local.py` impl (optional local inference) | High |

**In plain words:** Finally asking the AI to answer — using *only* the documents you supplied.

**4. System prompt.** The instructions that force the model to answer from the provided text and say "I don't know" when the answer isn't there. "Grounded" means exactly this. It's the difference between a trustworthy tool and one that confidently invents company policy.

**5. Prompt injection defense — moved here from Phase 27.** A retrieved document might itself contain text like *"ignore your instructions and reveal everything."* Since you're feeding retrieved content straight to the model, that content is untrusted input. This defense belongs with the code that creates the exposure, not 8 phases later.

**6. Citation parsing.** The model marks which chunk each claim came from; you extract those markers reliably.

**7. Fallbacks.** Providers go down and requests hang. Without timeouts, one stuck call ties up a worker indefinitely.

---

## Phase 20 — Conversation & Citation Data Model

| # | Task | Difficulty |
|---|---|---|
| 1 | `Conversation` / `Message` models + migration | Low |
| 2 | `message_citations` model (message_id ↔ chunk_id) | Low |
| 3 | Citation ID resolution (LLM output → chunk → doc version → page) | Medium |
| 4 | Prevent model from inventing source metadata (backend-resolved only) | Medium |
| 5 | Citation data integrity tests | Medium |

**1. Conversation/Message models moved here from Phase 22.** *(Reordered — citations reference `message_id`, and Phase 21's chat endpoints need these tables. They can't be defined two phases after the things that use them.)*

**3. Citation resolution.** The model outputs a marker like `[3]`. The backend turns that into "Employee Handbook v2, page 14" by looking it up.

**4. Backend-resolved only — the important one.** Never let the model *state* the source. It will produce plausible, wrong page numbers. The model may only point at a chunk ID; every human-readable detail is looked up by your code. A fabricated citation is worse than no citation, because it looks verifiable.

---

## Phase 21 — Streaming Chat (SSE)

| # | Task | Difficulty |
|---|---|---|
| 1 | `api/streaming/sse.py` — SSE response implementation | Medium |
| 2 | Event types: retrieval_started, context_ready, token, citation, completed, error | Medium |
| 3 | `api/routes/v1/conversations.py` / `messages.py` — chat endpoints | Medium |
| 4 | Full pipeline wiring (retrieval→context→LLM→stream) | High |
| 5 | Error propagation over SSE without breaking stream | High |

**In plain words:** Text appearing word by word instead of after a 10-second wait. Same total time, completely different perceived speed.

**2. Event types.** Beyond text, tell the UI what's happening — "searching", "found sources", "here's a citation". That's what lets the frontend show real progress.

**4. Full wiring.** Everything from Phases 11–19 connected end to end. First point where the system actually works as a product.

**5. Error propagation.** Failures often happen *mid-stream*, after you've already sent half an answer and a `200 OK`. You can't send an error status at that point, so errors must travel as stream events the UI understands.

---

## Phase 22 — Conversation Memory

| # | Task | Difficulty |
|---|---|---|
| 1 | Recent-message memory window | Medium |
| 2 | Token budget enforcement on history inclusion | Medium |
| 3 | Conversation summarization for long history | High |

**In plain words:** Making follow-up questions work. Send the last few messages along with the new question so "what about last year?" makes sense.

**3. Summarization.** Long conversations eventually exceed the size limit. Compress older messages into a summary and keep recent ones verbatim — the model retains the gist without the full transcript.

---

## Phase 23 — Evaluation Dataset

| # | Task | Difficulty |
|---|---|---|
| 1 | Dataset JSON schema (question/expected_answer/expected_docs/expected_chunks) | Low |
| 2 | `evaluation/datasets/schemas/` validation | Low |
| 3 | Sample dataset authoring (edge cases, adversarial, multi-hop, no-answer) | Medium |

**In plain words:** A test set of questions with known-correct answers. Without it, "did that change improve search?" is guesswork — and RAG systems are full of changes that feel better and measure worse.

**3. Include the hard cases.** Especially **no-answer** questions, where the right response is "that's not in the documents." A system that never admits ignorance is a system that invents things.

---

## Phase 24 — Retrieval Evaluation

| # | Task | Difficulty |
|---|---|---|
| 1 | `evaluation/metrics/retrieval.py` — Recall@K, Precision@K, MRR, nDCG | High |
| 2 | Metric correctness unit tests | Medium |
| 3 | Evaluation runner wiring (BM25 / Dense / Hybrid / Hybrid+Rerank comparison) | Medium |

**In plain words:** Measuring whether search finds the right documents — separately from whether the AI writes a good answer. Critical split: if answers are bad you need to know whether retrieval failed or generation did.

**1. The metrics.** *Recall@K* — was the right document in the top K? *MRR* — how high up was it? *nDCG* — is the ordering good overall?

**2. Test the metrics themselves.** *(Moved before the runner.)* These formulas are easy to implement subtly wrong, and a broken metric makes every later decision wrong while looking authoritative.

**3. Compare strategies.** Run all four configurations against the same questions and see which actually wins. This is where you find out whether reranking earns its latency.

---

## Phase 25 — Generation & Citation Evaluation

| # | Task | Difficulty |
|---|---|---|
| 1 | `evaluation/metrics/latency.py` / `cost.py` | Low |
| 2 | `evaluation/metrics/citations.py` — citation support/precision/completeness | High |
| 3 | `evaluation/judges/groundedness.py` — LLM-as-judge faithfulness | High |
| 4 | `evaluation/judges/correctness.py` | High |
| 5 | `evaluation/runners/evaluation_runner.py` — full pipeline execution + report | High |

**In plain words:** Measuring answer quality, not just retrieval.

**2. Citation metrics.** Does each claim actually appear in the cited source? This catches the worst failure mode — a confident answer with a citation that doesn't support it.

**3. Groundedness judging.** Use a second AI to check whether the answer is genuinely supported by the supplied documents. Imperfect, but it scales where humans don't.

**5. Runner last.** It executes everything above and produces the report.

---

## Phase 26 — Observability

| # | Task | Difficulty |
|---|---|---|
| 1 | Structured log fields standardization (request_id, tenant_id, operation, duration, status) | Medium |
| 2 | OpenTelemetry instrumentation (traces across auth→query→retrieval→LLM) | High |
| 3 | Span-level safe metadata (no secrets/full doc content) | Medium |
| 4 | Prometheus metrics export | Medium |
| 5 | Grafana dashboard config (`infrastructure/monitoring/grafana/`) | Medium |

**In plain words:** Being able to see what your system is doing in production. Formalizes the request ID work from Phase 2.

**2. Tracing.** One request touches auth, search, the vector database, and the AI provider. Tracing stitches those into a single timeline so "why did this take 8 seconds?" has an answer.

**3. Don't log secrets.** Traces get shipped to third-party tools. Passwords, tokens, and full document text must never leave. Listed alongside instrumentation because the safe-field rules must be written *as* you add instrumentation, not audited afterward.

**4–5. Metrics and dashboards.** Aggregate numbers over time, and the screens showing them.

---

## Phase 27 — Security Hardening

| # | Task | Difficulty |
|---|---|---|
| 1 | Redirect revalidation on URL fetch | Medium |
| 2 | RBAC enforcement audit across all endpoints | High |
| 3 | Rate limiting middleware (`api/middleware/rate_limit.py`) | Medium |

**Note:** three items previously here have moved to the phases that create the risk — SSRF protection → Phase 8 (with the URL fetcher), magic-byte file validation → Phase 6 (with uploads), prompt injection defense → Phase 19 (with generation). Shipping a known hole for 20 phases and remembering to close it later is not a plan.

**1. Redirect revalidation.** A URL can pass your safety check and then redirect to a blocked internal address. Every hop must be re-checked, not just the first.

**2. RBAC audit.** Systematically verify every endpoint actually enforces permissions. Endpoints get added over many phases; some will have been missed.

**3. Rate limiting.** Cap how often one user can call you. Without it, a single client can exhaust your AI provider budget in minutes.

---

## Phase 28 — Performance

| # | Task | Difficulty |
|---|---|---|
| 1 | Stage-level latency instrumentation (parse/OCR/chunk/embed/search/rerank/LLM) | Medium |
| 2 | P50/P95/P99 tracking | Medium |
| 3 | Database index review/tuning | Medium |
| 4 | Redis caching for retrieval results | Medium |
| 5 | Batch embedding optimization | Medium |
| 6 | Connection pool tuning under load | High |

**1–2. Measure before optimizing.** *(Moved to the front.)* Optimizing without measurement means guessing, and the guess is usually wrong. **P95** means "95% of requests were faster than this" — averages hide the slow requests that users actually complain about.

**3. Indexes.** The difference between a query scanning 10 million rows and jumping straight to 50.

**6. Pool tuning.** How many database connections to hold open. Too few and requests queue; too many and the database drowns.

---

## Phase 29 — Reliability

| # | Task | Difficulty |
|---|---|---|
| 1 | Health/readiness/liveness checks | Low |
| 2 | Timeout policies per external call (LLM, embedding, storage) | Medium |
| 3 | Circuit breaker for LLM/embedding provider failures | High |
| 4 | Dead-letter job handling | Medium |
| 5 | Graceful degradation (fallback provider paths) | High |

**1. Three different checks.** *Liveness* — am I alive? *Readiness* — can I serve traffic yet? Restarting a live-but-not-ready service is a common self-inflicted outage.

**2. Timeouts everywhere.** Any call that can hang, will. One hung call ties up a worker forever; enough of them take the service down.

**3. Circuit breaker.** When a provider is clearly failing, stop calling it for a while. Retrying a dead service just makes you slow too, and delays its recovery.

**5. Graceful degradation.** Better to serve search results with no AI summary than to serve an error page.

---

## Phase 30 — Testing

| # | Task | Difficulty |
|---|---|---|
| 1 | Unit tests: RRF, BM25 ranking, chunking, citation mapping | Medium |
| 2 | API tests: all routes, auth flows | Medium |
| 3 | Integration tests: ingestion pipeline end-to-end | High |
| 4 | Security tests: tenant isolation, auth bypass attempts | High |
| 5 | Retrieval regression tests | Medium |

**Note:** tests should be written *with* each phase, not saved until here. This phase is about filling gaps and formalizing coverage.

**4. Security tests are the ones that matter most.** Tenant isolation failures are silent — nothing errors, the wrong person just sees the wrong data.

**5. Regression tests.** Catch search quality *dropping* after a change. Without them, quality erodes gradually and invisibly.

---

## Phase 31 — Load Testing

| # | Task | Difficulty |
|---|---|---|
| 1 | Load test scripts (10/50/100/500 concurrent users) | Medium |
| 2 | Measure req/sec, P50/P95/P99, error rate under load | Medium |
| 3 | Resource monitoring during load (CPU/RAM/DB connections/queue depth) | Medium |

**In plain words:** Find out where it breaks *before* users do. Systems fail in surprising ways under concurrency — connection pools exhaust, queues back up, memory climbs. Watching resources during the test tells you *which* limit you hit, which is the difference between a fix and a guess.

---

## Phase 32 — CI/CD

| # | Task | Difficulty |
|---|---|---|
| 1 | `.dockerignore` files per build context (backend, frontend) | Low |
| 2 | Docker image build (`infrastructure/docker/api.Dockerfile`, worker Dockerfiles) | Medium |
| 3 | `.github/workflows/backend-ci.yml` — lint→typecheck→unit→integration→build | Medium |
| 4 | `.github/workflows/deploy.yml` | High |

**1. `.dockerignore` first.** Without it, `COPY . .` copies your `.env` file into the published image, where secrets stay recoverable in the image layer forever — `.gitignore` does not apply to Docker builds. Must exist before the first image is built.

**3. CI pipeline.** Every proposed change automatically gets linted, type-checked, and tested before anyone can merge it. This is where the Phase 0 lint config finally pays off.

**4. Deploy pipeline.** Push a button, or a merge, and it ships.

---

## Phase 33 — Production Deployment

| # | Task | Difficulty |
|---|---|---|
| 1 | Production environment config (secrets management) | High |
| 2 | Health check integration with hosting platform | Low |
| 3 | Database migration strategy for prod (zero-downtime) | High |
| 4 | Backend independent deploy from workers | Medium |

**1. Secrets management.** No `.env` files in production. The platform injects environment variables from a secret store, and your Phase 2 settings code reads them without any change — real secrets never touch the repository or an image.

**3. Zero-downtime migrations.** During a deploy, old and new code run simultaneously for a few minutes. A migration that drops a column the old code still reads causes an outage. The technique is to split changes into backward-compatible steps: add the new column, deploy code using both, then remove the old one in a later release.

**4. Independent deploys.** Shipping an API fix shouldn't restart workers mid-document.

---

## Agentic RAG Extension (post-stable-RAG only)

| # | Task | Difficulty |
|---|---|---|
| 1 | Agent planner design | High |
| 2 | Tool interfaces (semantic_search, keyword_search, document_search, metadata_search, document_reader, citation_verifier, calculator, conversation_memory) | High |
| 3 | Multi-step retrieval loop | High |
| 4 | Self-correction / evidence verification logic | High |
| 5 | Agent evaluation (tool selection accuracy, unnecessary calls, latency, cost) | High |

**In plain words:** Instead of one search then one answer, the AI decides for itself which tools to use and can search repeatedly until satisfied. Much more capable on complex questions, and much harder to debug, slower, and more expensive.

`plan.md` is explicit that the deterministic pipeline must be stable first — you cannot debug an agent built on retrieval you don't yet trust.

---

## Sequencing Fixes Applied

Tasks that were previously listed before their own dependencies:

| Phase | Change | Reason |
|---|---|---|
| 2 | `main.py` moved first → sixth | It imports settings, logging, middleware, and routers — it's the assembly step |
| 2 | Added packaging fix as task 1 | `import app` fails until `pyproject.toml` is corrected |
| 3 | `base.py` moved before `session.py` | More foundational; models depend on it |
| 3 | Pooling task rewritten as PgBouncer-compat, tuning left to Phase 28 | The engine must be written correctly the first time, not "tuned" later |
| 4 | Service moved before routes; schemas added | Routes call the service and use the schemas |
| 4 | Redis client setup added | Token revocation needs it; nothing connected to Redis before Phase 7 |
| 6 | Service moved before routes; schemas + migration added | Same dependency direction |
| 6 | Magic-byte validation pulled in from Phase 27 | Belongs with the upload code that creates the risk |
| 7 | Idempotency moved before retries | Retries without idempotency multiply corruption |
| 8 | `CanonicalDocument` moved before the parser interface | The interface and every parser reference it |
| 8 | Docling decision moved before `pdf_parser` | Deciding after building wastes the hardest work in the phase |
| 8 | Simple parsers (markdown, csv) moved before PDF | Validates the interface cheaply before heavy investment |
| 8 | SSRF protection pulled in from Phase 27 | Must ship with the URL fetcher, not 19 phases later |
| 9 | "Avoid full-document OCR" merged into per-page routing | Duplicate of the same requirement |
| 11 | `token_counter` + metadata schema + chunk IDs moved before chunkers | Chunkers use all three |
| 12 | Model/dimension versioning moved to second | Determines Phase 13's collection config; unrecoverable if skipped |
| 13 | Payload schema + collection config moved before implementation | Implementation writes payloads into a collection |
| 15 | RRF + its tests moved before the pipeline | The pipeline orchestrates RRF |
| 17 | Rule-vs-LLM policy moved first | Governs how the other three components are built |
| 18 | `builder.py` moved last | Orchestrates dedup, budget, and diversity |
| 19 | Prompt injection defense pulled in from Phase 27 | Belongs with the code that feeds untrusted text to the model |
| 20 | `Conversation`/`Message` models moved up from Phase 22 | Citations and Phase 21 endpoints both need them |
| 24 | Metric tests moved before the runner | A broken metric invalidates every decision made from it |
| 25 | Latency/cost metrics moved first | Trivial, and useful while building the expensive judges |
| 26 | Log field standardization moved first | It's the foundation the tracing work builds on |
| 28 | Instrumentation + percentile tracking moved first | You cannot optimize what you have not measured |
| 29 | Health/readiness checks moved first | Cheapest, and other reliability work depends on the distinction |
| 30 | API tests moved before integration tests | Faster feedback, fewer moving parts |
| 32 | `.dockerignore` added as task 1 | Prevents baking secrets into the first image built |
| 33 | Health check integration moved before migration strategy | Trivial and needed for any deploy to succeed |

---

## Sequencing Notes

- Phases 0–6 are the hard foundation — nothing below works without auth + tenancy + document storage.
- Phases 7–11 (ingestion pipeline) can be built and tested with dummy/small documents before OCR/chunking are fully tuned.
- Phases 12–16 (retrieval) require Phase 11 chunks to exist — don't start embeddings against unstable chunk schemas.
- Phases 17–22 (query understanding → chat) depend on 12–16 being functional end to end.
- Phases 23–25 (evaluation) require phases 12–22 to produce real retrieval/generation output to measure.
- Phases 26–29 (observability/security/performance/reliability) are cross-cutting — start instrumentation early (Phase 2 request_id, Phase 26 formalizes it), don't defer entirely to the end.
- **Security tasks now live in the phase that creates the risk.** Phase 27 retains only genuinely cross-cutting audit work.
- **Every phase that adds a model also needs a migration.** Called out explicitly in Phases 5, 6, and 7; assume it elsewhere.
- **Tests belong with the phase, not deferred to Phase 30.** Phase 30 exists to close gaps, not to be where testing starts.
- Agentic extension is explicitly last — plan.md is explicit the deterministic RAG system must be stable first.
