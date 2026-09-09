# Backend Implementation Tasks

Derived from `docs/plan.md` and `docs/architecture.md`. Ordered by implementation sequence — earlier phases are hard dependencies for later ones. Each task is ranked **High / Medium / Low** difficulty based on conceptual complexity + failure surface, not raw time.

Current state: `backend/` is empty. Root has a stray `uv init` stub (`pyproject.toml`, `src/`) that does not match the planned `backend/pyproject.toml` layout — needs correcting in Phase 0.

---

## Phase 0 — Backend Foundation

| Task | Difficulty |
|---|---|
| Remove/relocate stray root `pyproject.toml` + `src/` stub | Low |
| Create `backend/` directory skeleton (`apps/api`, `workers`, `packages`, `evaluation`, `tests`, `migrations`) | Low |
| Initialize `backend/pyproject.toml` (uv/poetry) with Python version pin | Low |
| Add core deps: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` | Low |
| Verify `uv run python -c "import fastapi"` works | Low |
| Configure linting (ruff) + formatting (black/ruff format) | Low |
| Configure backend `.env.example` | Low |

---

## Phase 1 — Local Infrastructure (Docker Compose)

| Task | Difficulty |
|---|---|
| Write `docker-compose.yml` service defs for Postgres, Redis, Qdrant | Medium |
| Add healthchecks for each service | Low |
| Configure named volumes for persistence | Low |
| Configure `infrastructure/postgres/init/` bootstrap scripts | Low |
| Wire `.env` variables into compose (ports, creds) | Low |
| Verify all 3 containers reachable from host CLI (`psql`, `redis-cli`, Qdrant `/collections`) | Medium |

---

## Phase 2 — FastAPI App Skeleton + Config

| Task | Difficulty |
|---|---|
| `app/main.py` app factory | Low |
| `config/settings.py` — Pydantic `BaseSettings`, env validation | Medium |
| `config/logging.py` — structured JSON logging setup | Medium |
| `api/v1/health.py` — `/health` endpoint | Low |
| ASGI startup/shutdown lifecycle hooks | Medium |
| `middleware/request_id.py` — request ID generation/propagation | Medium |
| Verify uvicorn dev server + hot reload | Low |

---

## Phase 3 — Database Layer (SQLAlchemy + Alembic)

| Task | Difficulty |
|---|---|
| `database/session.py` — async engine + session-per-request | Medium |
| `database/base.py` — declarative base | Low |
| Alembic init + config wiring to `Settings` | Medium |
| First models: `User`, `Tenant` | Medium |
| First migration (autogenerate + review) | Medium |
| Repository pattern base class | Medium |
| Connection pooling config/tuning | High |
| Verify migration round-trip on fresh DB | Low |

---

## Phase 4 — Authentication

| Task | Difficulty |
|---|---|
| `auth/password.py` — hashing (argon2/bcrypt) | Low |
| `auth/jwt.py` — token encode/decode, claims, expiry | Medium |
| Access token + refresh token lifecycle | High |
| `auth/dependencies.py` — `get_current_user` injection | Medium |
| `api/v1/auth.py` — register/login/refresh/logout routes | Medium |
| `services/auth_service.py` | Medium |
| Token revocation / logout invalidation strategy | High |
| Security tests: expired/invalid/missing token rejection | Medium |

---

## Phase 5 — Multi-Tenancy

| Task | Difficulty |
|---|---|
| `Tenant`/`Organization` + `Membership` models | Medium |
| `middleware/tenant.py` — tenant context resolution per request | High |
| Tenant-scoped base repository (mandatory `tenant_id` filter) | High |
| Retrofit all repositories to require `tenant_id` | Medium |
| Cross-tenant isolation test suite (adversarial: guessed IDs) | High |
| Role-based access control (RBAC) scaffold | High |

---

## Phase 6 — Document Management

| Task | Difficulty |
|---|---|
| `packages/storage/base.py` — `StorageProvider` interface | Low |
| `packages/storage/r2.py` — R2/S3-compatible impl | Medium |
| `Document` / `DocumentVersion` models | Medium |
| File validation (MIME, extension, size, content sniffing) | Medium |
| Content-hash dedup logic | Medium |
| `api/v1/documents.py` — upload/list/delete/download/metadata | Medium |
| `services/document_service.py` | Medium |
| Multipart upload handling + streaming to storage | High |
| Tenant isolation on all document endpoints | Medium |

---

## Phase 7 — Async Ingestion (Job Infrastructure)

| Task | Difficulty |
|---|---|
| `packages/queue/base.py` — `Queue` interface | Low |
| `packages/queue/redis_queue.py` — Redis-backed impl | Medium |
| `IngestionJob` model + state machine (PENDING→QUEUED→PROCESSING→COMPLETED/FAILED/RETRYING) | High |
| Job enqueue on document upload | Medium |
| `workers/ingestion/main.py` — worker loop/consumer | High |
| Retry logic + exponential backoff | High |
| Idempotency guarantees (content hash + job identity) | High |
| Job status polling endpoint | Low |
| Dead-letter handling for permanently failed jobs | Medium |

---

## Phase 8 — Document Parsing

| Task | Difficulty |
|---|---|
| `workers/ingestion/parsers/base.py` — `DocumentParser` interface | Low |
| `CanonicalDocument` data model (blocks: heading/paragraph/table/list/code/image) | High |
| `pdf_parser.py` | High |
| `docx_parser.py` | Medium |
| `html_parser.py` | Medium |
| `markdown_parser.py` | Low |
| `csv_parser.py` | Low |
| `web_parser.py` (URL fetch + extraction) | Medium |
| Docling integration evaluation/adoption | High |
| Parser router (file-type detection → correct parser) | Medium |

---

## Phase 9 — OCR

| Task | Difficulty |
|---|---|
| `ocr/base.py` — `OCRProvider` interface | Low |
| Text quality detection (native text vs scanned) | High |
| `rapidocr_provider.py` | Medium |
| `tesseract_provider.py` (fallback) | Medium |
| `ocr/router.py` — page-level routing (native vs OCR) | High |
| Confidence-based fallback logic | High |
| Avoid full-document OCR when unnecessary (per-page decision) | Medium |

---

## Phase 10 — Normalization & Cleaning

| Task | Difficulty |
|---|---|
| `normalization/canonical_document.py` finalization | Medium |
| `normalizer.py` — headings/paragraphs/tables/lists normalization | High |
| `cleaning/cleaner.py` — whitespace/artifact cleanup | Medium |
| `headers.py` / `footers.py` — repeated header/footer detection+removal | High |
| `boilerplate.py` — duplicate/nav content removal | Medium |
| Deterministic cleaning pipeline tests | Medium |

---

## Phase 11 — Chunking

| Task | Difficulty |
|---|---|
| `chunking/base.py` interface | Low |
| `structure_chunker.py` — heading/paragraph/table/list-aware | High |
| `contextual_chunker.py` — heading-path enrichment | High |
| `token_counter.py` | Low |
| Stable chunk ID generation | Medium |
| Chunk metadata schema (document_id, version_id, page, heading_path, etc.) | Medium |
| Chunking benchmark vs naive fixed-size (validate it actually helps) | High |

---

## Phase 12 — Embedding Infrastructure

| Task | Difficulty |
|---|---|
| `packages/embeddings/base.py` — `EmbeddingProvider` interface | Low |
| `local.py` — local embedding model impl | Medium |
| `api.py` — API-based embedding provider | Medium |
| `factory.py` — provider selection | Low |
| Batch embedding logic | Medium |
| Retry + rate limiting | Medium |
| Model/dimension versioning metadata | Medium |
| Embedding cache | Medium |
| `workers/embeddings/` — batcher + processor worker | High |

---

## Phase 13 — Vector Search (Qdrant)

| Task | Difficulty |
|---|---|
| `packages/vector_store/base.py` — `VectorStore` interface | Low |
| `qdrant.py` impl (upsert/search/delete/filter) | Medium |
| Payload schema design (tenant_id, document_id, version_id, page, etc.) | Medium |
| Metadata filter integration with vector query | High |
| Collection/index configuration tuning | High |

---

## Phase 14 — Lexical Search (BM25)

| Task | Difficulty |
|---|---|
| PostgreSQL Full-Text Search setup (tsvector columns, indexes) | Medium |
| `lexical/retriever.py` | Medium |
| `lexical/ranking.py` | Medium |
| Exact-match/keyword-heavy query test cases | Low |

---

## Phase 15 — Hybrid Retrieval + RRF

| Task | Difficulty |
|---|---|
| `retrieval/interfaces.py` — shared retrieval contracts | Medium |
| `retrieval/pipeline.py` — orchestration | High |
| `fusion/rrf.py` — Reciprocal Rank Fusion implementation | High |
| RRF unit tests (rank-position correctness, independent of scoring scale) | High |
| Parallel dense+BM25 execution (async) | Medium |

---

## Phase 16 — Reranking

| Task | Difficulty |
|---|---|
| `reranking/base.py` — `Reranker` interface | Low |
| `reranking/cross_encoder.py` impl | High |
| Top-50 → top-10 pipeline wiring | Medium |
| Latency benchmarking (reranker is often the bottleneck) | Medium |

---

## Phase 17 — Query Understanding

| Task | Difficulty |
|---|---|
| `query/classifier.py` — query type classification | Medium |
| `query/rewriter.py` — conversational query rewriting | High |
| `query/filters.py` — metadata extraction (date/department/entity) | Medium |
| Rule-based vs LLM-based decision logic (avoid LLM where rules suffice) | Medium |

---

## Phase 18 — Context Builder

| Task | Difficulty |
|---|---|
| `context/deduplicator.py` | Medium |
| `context/builder.py` — evidence ordering | Medium |
| `context/budget.py` — token budget enforcement | Medium |
| Document diversity logic | Medium |
| Deterministic behavior test suite | Medium |

---

## Phase 19 — Grounded Generation

| Task | Difficulty |
|---|---|
| `packages/llm/base.py` — `LLMProvider` interface | Low |
| `openai_compatible.py` impl | Medium |
| `local.py` impl (optional local inference) | High |
| `factory.py` — provider selection | Low |
| System prompt design (grounding constraints, no-invention rules) | High |
| Structured output parsing (citation IDs) | Medium |
| Retry/timeout/fallback provider logic | High |

---

## Phase 20 — Citation System

| Task | Difficulty |
|---|---|
| `message_citations` model (message_id ↔ chunk_id) | Low |
| Citation ID resolution (LLM output → chunk → doc version → page) | Medium |
| Prevent model from inventing source metadata (backend-resolved only) | Medium |
| Citation data integrity tests | Medium |

---

## Phase 21 — Streaming Chat (SSE)

| Task | Difficulty |
|---|---|
| `streaming/sse.py` — SSE response implementation | Medium |
| Event types: retrieval_started, context_ready, token, citation, completed, error | Medium |
| `api/v1/conversations.py` / `messages.py` — chat endpoints | Medium |
| Full pipeline wiring (retrieval→context→LLM→stream) | High |
| Error propagation over SSE without breaking stream | High |

---

## Phase 22 — Conversation Memory

| Task | Difficulty |
|---|---|
| `Conversation` / `Message` models | Low |
| Recent-message memory window | Medium |
| Conversation summarization for long history | High |
| Token budget enforcement on history inclusion | Medium |

---

## Phase 23 — Evaluation Dataset

| Task | Difficulty |
|---|---|
| Dataset JSON schema (question/expected_answer/expected_docs/expected_chunks) | Low |
| Sample dataset authoring (edge cases, adversarial, multi-hop, no-answer) | Medium |
| `evaluation/datasets/schemas/` validation | Low |

---

## Phase 24 — Retrieval Evaluation

| Task | Difficulty |
|---|---|
| `evaluation/metrics/retrieval.py` — Recall@K, Precision@K, MRR, nDCG | High |
| Evaluation runner wiring (BM25 / Dense / Hybrid / Hybrid+Rerank comparison) | Medium |
| Metric correctness unit tests | Medium |

---

## Phase 25 — Generation & Citation Evaluation

| Task | Difficulty |
|---|---|
| `evaluation/judges/groundedness.py` — LLM-as-judge faithfulness | High |
| `evaluation/judges/correctness.py` | High |
| `evaluation/metrics/citations.py` — citation support/precision/completeness | High |
| `evaluation/metrics/latency.py` / `cost.py` | Low |
| `evaluation/runners/evaluation_runner.py` — full pipeline execution + report | High |

---

## Phase 26 — Observability

| Task | Difficulty |
|---|---|
| OpenTelemetry instrumentation (traces across auth→query→retrieval→LLM) | High |
| Prometheus metrics export | Medium |
| Structured log fields standardization (request_id, tenant_id, operation, duration, status) | Medium |
| Span-level safe metadata (no secrets/full doc content) | Medium |
| Grafana dashboard config (`infrastructure/monitoring/grafana/`) | Medium |

---

## Phase 27 — Security Hardening

| Task | Difficulty |
|---|---|
| SSRF protection for URL ingestion (block localhost/private IPs/metadata endpoints) | High |
| Redirect revalidation on URL fetch | Medium |
| File content validation beyond MIME (magic bytes) | Medium |
| Prompt injection defense (treat retrieved content as untrusted) | High |
| RBAC enforcement audit across all endpoints | High |
| Rate limiting middleware (`middleware/rate_limit.py`) | Medium |

---

## Phase 28 — Performance

| Task | Difficulty |
|---|---|
| Stage-level latency instrumentation (parse/OCR/chunk/embed/search/rerank/LLM) | Medium |
| Database index review/tuning | Medium |
| Connection pool tuning under load | High |
| Redis caching for retrieval results | Medium |
| Batch embedding optimization | Medium |
| P50/P95/P99 tracking | Medium |

---

## Phase 29 — Reliability

| Task | Difficulty |
|---|---|
| Timeout policies per external call (LLM, embedding, storage) | Medium |
| Circuit breaker for LLM/embedding provider failures | High |
| Dead-letter job handling | Medium |
| Health/readiness/liveness checks | Low |
| Graceful degradation (fallback provider paths) | High |

---

## Phase 30 — Testing

| Task | Difficulty |
|---|---|
| Unit tests: RRF, BM25 ranking, chunking, citation mapping | Medium |
| Integration tests: ingestion pipeline end-to-end | High |
| API tests: all routes, auth flows | Medium |
| Security tests: tenant isolation, auth bypass attempts | High |
| Retrieval regression tests | Medium |

---

## Phase 31 — Load Testing

| Task | Difficulty |
|---|---|
| Load test scripts (10/50/100/500 concurrent users) | Medium |
| Measure req/sec, P50/P95/P99, error rate under load | Medium |
| Resource monitoring during load (CPU/RAM/DB connections/queue depth) | Medium |

---

## Phase 32 — CI/CD

| Task | Difficulty |
|---|---|
| `.github/workflows/backend-ci.yml` — lint→typecheck→unit→integration→build | Medium |
| Docker image build (`infrastructure/docker/api.Dockerfile`, worker Dockerfiles) | Medium |
| `.github/workflows/deploy.yml` | High |

---

## Phase 33 — Production Deployment

| Task | Difficulty |
|---|---|
| Production environment config (secrets management) | High |
| Database migration strategy for prod (zero-downtime) | High |
| Backend independent deploy from workers | Medium |
| Health check integration with hosting platform | Low |

---

## Agentic RAG Extension (post-stable-RAG only)

| Task | Difficulty |
|---|---|
| Agent planner design | High |
| Tool interfaces (semantic_search, keyword_search, document_search, metadata_search, document_reader, citation_verifier, calculator, conversation_memory) | High |
| Multi-step retrieval loop | High |
| Self-correction / evidence verification logic | High |
| Agent evaluation (tool selection accuracy, unnecessary calls, latency, cost) | High |

---

## Sequencing Notes

- Phases 0–6 are the hard foundation — nothing below works without auth + tenancy + document storage.
- Phases 7–11 (ingestion pipeline) can be built and tested with dummy/small documents before OCR/chunking are fully tuned.
- Phases 12–16 (retrieval) require Phase 11 chunks to exist — don't start embeddings against unstable chunk schemas.
- Phases 17–22 (query understanding → chat) depend on 12–16 being functional end to end.
- Phases 23–25 (evaluation) require phases 12–22 to produce real retrieval/generation output to measure.
- Phases 26–29 (observability/security/performance/reliability) are cross-cutting — start instrumentation early (Phase 2 request_id, Phase 26 formalizes it), don't defer entirely to the end.
- Agentic extension is explicitly last — plan.md is explicit the deterministic RAG system must be stable first.
