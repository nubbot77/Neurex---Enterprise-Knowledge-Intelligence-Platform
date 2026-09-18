# Enterprise Knowledge Intelligence Platform

## 1. Project Overview

Build a production-grade **Enterprise Knowledge Intelligence Platform** that combines:

* Document ingestion
* Document understanding
* OCR
* Structure-aware chunking
* Dense vector search
* Lexical/BM25 search
* Hybrid retrieval
* Reciprocal Rank Fusion (RRF)
* Cross-encoder reranking
* Query rewriting
* Metadata filtering
* Grounded LLM generation
* Citation generation
* Streaming responses
* Conversation memory
* Multi-tenancy
* Document versioning
* Async processing
* Evaluation
* Observability
* Security
* Rate limiting
* Reliability
* Production deployment
* Agentic RAG extension

This project should **not** be implemented as a simple:

> Upload PDF → create embeddings → ask chatbot

Instead, it should demonstrate how a real production AI system is designed, built, evaluated, deployed, monitored, and debugged.

---

# 2. Main Goals

The project has four major goals.

## Goal 1 — Become a Strong AI Engineer

The project should demonstrate knowledge of:

* Python
* FastAPI
* PostgreSQL
* Redis
* Qdrant
* Docker
* Async processing
* APIs
* Distributed systems concepts
* Search systems
* LLM systems
* Evaluation
* Observability
* Security
* CI/CD
* Cloud deployment

---

## Goal 2 — Demonstrate GenAI Engineering

The system should demonstrate:

* RAG
* Hybrid retrieval
* Reranking
* Query rewriting
* Context construction
* Grounded generation
* Citation generation
* LLM abstraction
* Embedding abstraction
* Prompt management
* Conversation memory
* LLM evaluation

---

## Goal 3 — Demonstrate Agentic AI

The final extension should support:

* Query planning
* Tool selection
* Multi-step retrieval
* Search → analyze → retrieve → verify
* Retrieval loops
* Self-correction
* Evidence verification
* Agent memory
* Tool execution
* Agent evaluation

---

## Goal 4 — Build a Resume-Ready Production System

The final system should be deployable and demonstrable.

The resume should be able to honestly describe:

> Built a multi-tenant enterprise knowledge intelligence platform with hybrid retrieval, RRF fusion, cross-encoder reranking, grounded generation, citation tracking, asynchronous ingestion, evaluation pipelines, observability, and an agentic retrieval layer.

Metrics must only be added after actual benchmarking.

---

# 3. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │       User          │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      Frontend       │
                         │   React + Vite      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     API Gateway     │
                         │      FastAPI        │
                         └──────────┬──────────┘
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
               ▼                    ▼                    ▼
        ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
        │ PostgreSQL  │      │    Redis    │      │    Qdrant   │
        │ Metadata    │      │ Queue/Cache │      │ Vector DB   │
        └─────────────┘      └──────┬──────┘      └─────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │ Worker Processes │
                           └────────┬─────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              │                     │                      │
              ▼                     ▼                      ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │  Ingestion  │       │  Embedding  │       │ Evaluation  │
       │   Worker    │       │   Worker    │       │   Worker    │
       └─────────────┘       └─────────────┘       └─────────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │  Cloudflare R2   │
                           │ Object Storage   │
                           └──────────────────┘
```

---

# 4. Repository Structure

Frontend and backend must be maintained as **separate top-level applications**.

```text
enterprise-knowledge-intelligence/
│
├── frontend/
│
├── backend/
│
├── infrastructure/
│
├── docs/
│
├── scripts/
│
├── .github/
│
├── docker-compose.yml
├── Makefile
├── .gitignore
├── .env.example
└── README.md
```

---

# 5. Frontend Directory Structure

The frontend is completely independent from the Python backend.

```text
frontend/
│
├── public/
│   └── assets/
│
├── src/
│   │
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   └── providers.tsx
│   │
│   ├── assets/
│   │
│   ├── components/
│   │   │
│   │   ├── ui/
│   │   │
│   │   ├── layout/
│   │   │
│   │   ├── documents/
│   │   │
│   │   ├── ingestion/
│   │   │
│   │   ├── search/
│   │   │
│   │   ├── chat/
│   │   │
│   │   ├── citations/
│   │   │
│   │   ├── evaluations/
│   │   │
│   │   └── observability/
│   │
│   ├── pages/
│   │   │
│   │   ├── auth/
│   │   │
│   │   ├── dashboard/
│   │   │
│   │   ├── documents/
│   │   │
│   │   ├── search/
│   │   │
│   │   ├── chat/
│   │   │
│   │   ├── evaluations/
│   │   │
│   │   ├── settings/
│   │   │
│   │   └── errors/
│   │
│   ├── features/
│   │   │
│   │   ├── authentication/
│   │   ├── document-management/
│   │   ├── ingestion-monitoring/
│   │   ├── search/
│   │   ├── conversations/
│   │   ├── citations/
│   │   └── evaluations/
│   │
│   ├── hooks/
│   │
│   ├── services/
│   │   │
│   │   ├── api/
│   │   ├── auth/
│   │   └── streaming/
│   │
│   ├── stores/
│   │   ├── authStore.ts
│   │   ├── chatStore.ts
│   │   └── uiStore.ts
│   │
│   ├── types/
│   ├── utils/
│   ├── constants/
│   │
│   └── styles/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
└── .env.example
```

---

# 6. Backend Directory Structure

The backend is completely independent from the frontend.

```text
backend/
│
├── apps/
│   │
│   └── api/
│       │
│       ├── app/
│       │   │
│       │   ├── main.py
│       │   │
│       │   ├── api/
│       │   │   ├── dependencies.py
│       │   │ ├── router.py
│       │   │ │
│       │   │ └── v1/
│       │   │     ├── auth.py
│       │   │     ├── users.py
│       │   │     ├── tenants.py
│       │   │     ├── documents.py
│       │   │     ├── document_versions.py
│       │   │     ├── ingestion_jobs.py
│       │   │     ├── search.py
│       │   │     ├── conversations.py
│       │   │     ├── messages.py
│       │   │     ├── evaluations.py
│       │   │     └── health.py
│       │   │
│       │   ├── auth/
│       │   │   ├── dependencies.py
│       │   │   ├── jwt.py
│       │   │   ├── password.py
│       │   │   └── permissions.py
│       │   │
│       │   ├── config/
│       │   │   ├── settings.py
│       │   │   └── logging.py
│       │   │
│       │   ├── database/
│       │   │   ├── session.py
│       │   │   ├── base.py
│       │   │   │
│       │   │   ├── models/
│       │   │   │   ├── user.py
│       │   │   │   ├── tenant.py
│       │   │   │   ├── document.py
│       │   │   │   ├── document_version.py
│       │   │   │   ├── chunk.py
│       │   │   │   ├── ingestion_job.py
│       │   │   │   ├── conversation.py
│       │   │   │   └── message.py
│       │   │   │
│       │   │   └── repositories/
│       │   │       ├── users.py
│       │   │       ├── tenants.py
│       │   │       ├── documents.py
│       │   │       └── conversations.py
│       │   │
│       │   ├── schemas/
│       │   │   ├── auth.py
│       │   │   ├── users.py
│       │   │   ├── tenants.py
│       │   │   ├── documents.py
│       │   │   ├── ingestion.py
│       │   │   ├── search.py
│       │   │   ├── chat.py
│       │   │   └── evaluations.py
│       │   │
│       │   ├── services/
│       │   │   ├── auth_service.py
│       │   │   ├── document_service.py
│       │   │   ├── conversation_service.py
│       │   │   └── evaluation_service.py
│       │   │
│       │   ├── middleware/
│       │   │   ├── request_id.py
│       │   │   ├── tenant.py
│       │   │   ├── rate_limit.py
│       │   │   └── security.py
│       │   │
│       │   └── streaming/
│       │       └── sse.py
│       │
│       └── tests/
│           ├── unit/
│           ├── integration/
│           └── api/
│
├── workers/
│   │
│   ├── ingestion/
│   │   ├── main.py
│   │   ├── pipeline.py
│   │   │
│   │   ├── detection/
│   │   │   ├── file_detector.py
│   │   │   └── content_detector.py
│   │   │
│   │   ├── parsers/
│   │   │   ├── base.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── html_parser.py
│   │   │   ├── markdown_parser.py
│   │   │   ├── csv_parser.py
│   │   │   └── web_parser.py
│   │   │
│   │   ├── ocr/
│   │   │   ├── base.py
│   │   │   ├── rapidocr_provider.py
│   │   │   ├── tesseract_provider.py
│   │   │   ├── paddleocr_provider.py
│   │   │   └── router.py
│   │   │
│   │   ├── normalization/
│   │   │   ├── canonical_document.py
│   │   │   ├── normalizer.py
│   │   │   └── metadata.py
│   │   │
│   │   ├── cleaning/
│   │   │   ├── cleaner.py
│   │   │   ├── headers.py
│   │   │   ├── footers.py
│   │   │   └── boilerplate.py
│   │   │
│   │   └── chunking/
│   │       ├── base.py
│   │       ├── structure_chunker.py
│   │       ├── contextual_chunker.py
│   │       └── token_counter.py
│   │
│   ├── embeddings/
│   │   ├── main.py
│   │   ├── batcher.py
│   │   └── processor.py
│   │
│   └── evaluation/
│       ├── main.py
│       └── runner.py
│
├── packages/
│   │
│   ├── retrieval/
│   │   ├── interfaces.py
│   │   ├── pipeline.py
│   │   │
│   │   ├── lexical/
│   │   │   ├── retriever.py
│   │   │   └── ranking.py
│   │   │
│   │   ├── dense/
│   │   │   ├── retriever.py
│   │   │   └── filters.py
│   │   │
│   │   ├── fusion/
│   │   │   └── rrf.py
│   │   │
│   │   ├── reranking/
│   │   │   ├── base.py
│   │   │   └── cross_encoder.py
│   │   │
│   │   ├── query/
│   │   │   ├── classifier.py
│   │   │   ├── rewriter.py
│   │   │   └── filters.py
│   │   │
│   │   └── context/
│   │       ├── builder.py
│   │       ├── deduplicator.py
│   │       └── budget.py
│   │
│   ├── llm/
│   │   ├── base.py
│   │   ├── openai_compatible.py
│   │   ├── local.py
│   │   └── factory.py
│   │
│   ├── embeddings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── api.py
│   │   └── factory.py
│   │
│   ├── storage/
│   │   ├── base.py
│   │   └── r2.py
│   │
│   ├── vector_store/
│   │   ├── base.py
│   │   └── qdrant.py
│   │
│   ├── queue/
│   │   ├── base.py
│   │   └── redis_queue.py
│   │
│   └── common/
│       ├── errors/
│       ├── logging/
│       ├── telemetry/
│       ├── security/
│       ├── ids/
│       └── utilities/
│
├── evaluation/
│   │
│   ├── datasets/
│   │   ├── samples/
│   │   └── schemas/
│   │
│   ├── metrics/
│   │   ├── retrieval.py
│   │   ├── generation.py
│   │   ├── citations.py
│   │   ├── latency.py
│   │   └── cost.py
│   │
│   ├── judges/
│   │   ├── groundedness.py
│   │   └── correctness.py
│   │
│   ├── runners/
│   │   └── evaluation_runner.py
│   │
│   └── reports/
│
├── migrations/
│
├── scripts/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── retrieval/
│   └── security/
│
├── pyproject.toml
├── uv.lock
└── .env.example
```

---

# 7. Infrastructure Directory

```text
infrastructure/
│
├── docker/
│   ├── frontend.Dockerfile
│   ├── api.Dockerfile
│   ├── ingestion-worker.Dockerfile
│   └── embedding-worker.Dockerfile
│
├── postgres/
│   ├── init/
│   └── config/
│
├── redis/
│
├── qdrant/
│
└── monitoring/
    │
    ├── prometheus/
    ├── grafana/
    └── otel/
```

Infrastructure should contain deployment-related configuration rather than application business logic.

---

# 8. Documentation Directory

```text
docs/
│
├── plan.md
├── architecture.md
├── project-explanation.md
├── api.md
├── database.md
├── ingestion.md
├── retrieval.md
├── evaluation.md
├── security.md
├── deployment.md
├── debugging.md
│
└── decisions/
    ├── 001-modular-monolith.md
    ├── 002-qdrant.md
    ├── 003-hybrid-retrieval.md
    ├── 004-ocr-strategy.md
    └── 005-sse.md
```

Architecture decisions should be documented using ADRs.

---

# 9. Global Scripts

```text
scripts/
│
├── dev.sh
├── test.sh
├── seed_data.py
└── benchmark.py
```

---

# 10. CI/CD

```text
.github/
│
└── workflows/
    ├── frontend-ci.yml
    ├── backend-ci.yml
    └── deploy.yml
```

Frontend and backend CI pipelines should remain independent.

---

# 11. Technology Stack

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* TanStack Query
* Zustand
* React Router
* SSE client
* Vitest
* Playwright

---

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* Redis
* Qdrant
* Docker

---

## AI

* OpenAI-compatible LLM APIs
* Local/open-source LLMs
* Embedding models
* Cross-encoder rerankers
* Optional local inference server

The AI layer must use provider abstractions so models can be swapped without rewriting the application.

---

## Storage

### PostgreSQL

Used for:

* Users
* Tenants
* Documents
* Document versions
* Chunks
* Ingestion jobs
* Conversations
* Messages
* Evaluation results
* Audit logs

### Qdrant

Used for:

* Dense embeddings
* Vector similarity search
* Metadata filtering

### Redis

Used for:

* Job queues
* Caching
* Rate limiting
* Temporary state

### Cloudflare R2

Used for:

* Original documents
* Processed documents
* Generated artifacts
* Optional extracted assets

---

# 12. Development Phases

The project must be implemented incrementally.

Do NOT attempt to build everything simultaneously.

---

## Phase 0 — Repository Foundation

Create:

```text
frontend/
backend/
infrastructure/
docs/
scripts/
.github/
```

Tasks:

* Initialize Git
* Configure frontend
* Configure backend
* Configure linting
* Configure formatting
* Configure testing
* Configure environment variables
* Configure README
* Configure branch strategy

---

# Phase 1 — Local Infrastructure

Run locally:

* PostgreSQL
* Redis
* Qdrant

Create:

```text
docker-compose.yml
```

Verify:

```text
Frontend
    ↓
Backend
    ↓
PostgreSQL
Redis
Qdrant
```

---

# Phase 2 — Authentication

Implement:

* User registration
* Login
* Password hashing
* JWT
* Access tokens
* Refresh tokens
* Logout
* Authentication middleware

---

# Phase 3 — Multi-Tenancy

Implement:

```text
User
  ↓
Tenant
  ↓
Documents
  ↓
Chunks
  ↓
Conversations
```

Every tenant-owned resource must have tenant isolation.

Never rely solely on frontend filtering for tenant security.

---

# Phase 4 — Document Management

Support:

* Upload
* List
* Delete
* Download
* Metadata
* Status
* Document version
* File hash

Supported formats:

```text
PDF
DOCX
HTML
Markdown
CSV
Web pages
```

---

# Phase 5 — Async Ingestion

Uploading a document should NOT block the API request while the document is processed.

Flow:

```text
Upload
   ↓
Create Document
   ↓
Create Ingestion Job
   ↓
Push Job → Redis
   ↓
Worker
```

Job states:

```text
PENDING
QUEUED
PROCESSING
COMPLETED
FAILED
RETRYING
```

Implement:

* Retries
* Exponential backoff
* Idempotency
* Job status
* Failure reason
* Progress tracking

---

# Phase 6 — Document Parsing

Implement parser abstraction:

```text
DocumentParser
```

Implement:

```text
PDFParser
DOCXParser
HTMLParser
MarkdownParser
CSVParser
WebParser
```

All parsers should produce a common internal representation.

---

# Phase 7 — OCR

Implement adaptive OCR.

Architecture:

```text
Document
   ↓
Detect text quality
   ↓
Is OCR required?
   ├── No → Continue
   │
   └── Yes
        ↓
     OCR Router
        ↓
   ┌────┴─────┐
   │          │
RapidOCR  Tesseract
   │          │
   └────┬─────┘
        ↓
Canonical Document
```

Later benchmark:

* RapidOCR
* Tesseract
* PaddleOCR
* Other OCR providers

Do not OCR every page unnecessarily.

---

# Phase 8 — Normalization & Cleaning

Create canonical document representation.

Normalize:

* Headings
* Paragraphs
* Tables
* Lists
* Page numbers
* Metadata
* Headers
* Footers
* Boilerplate

Remove:

* Repeated headers
* Repeated footers
* Unnecessary whitespace
* Duplicate content

---

# Phase 9 — Chunking

Implement:

### Structure-aware chunking

Respect:

* Heading hierarchy
* Paragraph boundaries
* Tables
* Lists
* Sections

### Contextual chunking

Store metadata such as:

```text
document_id
document_version_id
chunk_id
page_number
section
heading
source
tenant_id
content
```

Every chunk must have a stable identifier.

Example:

```text
chunk_01HXYZ...
```

---

# Phase 10 — Embedding Infrastructure

Create:

```text
EmbeddingProvider
```

Support:

```text
LocalEmbeddingProvider
APIEmbeddingProvider
```

Implement:

* Batch embeddings
* Retry
* Rate limiting
* Model versioning
* Dimension validation
* Caching

---

# Phase 11 — Vector Search

Use Qdrant.

Implement:

```text
VectorStore
```

Operations:

```text
upsert
search
delete
filter
```

Support metadata filters:

```text
tenant_id
document_id
document_version_id
source
department
date
```

---

# Phase 12 — Lexical Search

Implement BM25 / lexical retrieval.

The purpose is to handle queries where exact terminology matters.

Examples:

```text
"API-402"
"ISO 27001"
"Q3 2025 revenue"
"ERR_CONNECTION_RESET"
```

Dense retrieval and lexical retrieval should complement each other.

---

# Phase 13 — Hybrid Retrieval

Run:

```text
Query
  │
  ├── Dense Search
  │
  └── BM25 Search
          ↓
       RRF Fusion
          ↓
      Candidate Set
```

Implement Reciprocal Rank Fusion.

Do not simply concatenate search results.

---

# Phase 14 — Reranking

Use a cross-encoder reranker.

Flow:

```text
Query
  ↓
Hybrid Retrieval
  ↓
Top 50 candidates
  ↓
Cross Encoder
  ↓
Top 10
```

Make `Reranker` an abstraction.

---

# Phase 15 — Query Understanding

Implement:

### Query classification

Examples:

```text
FACTUAL
COMPARISON
SUMMARY
MULTI_HOP
ANALYTICAL
NAVIGATIONAL
```

### Query rewriting

Example:

```text
Original:
"What was their revenue?"

Context:
User previously asked about Microsoft.

Rewrite:
"What was Microsoft's revenue?"
```

### Metadata extraction

Extract:

```text
date
department
document
entity
source
```

---

# Phase 16 — Context Builder

The context builder should:

* Deduplicate chunks
* Order evidence
* Remove redundant content
* Respect token budget
* Preserve citations
* Preserve document hierarchy

Flow:

```text
Reranked Results
      ↓
Deduplication
      ↓
Evidence Ordering
      ↓
Token Budget
      ↓
Context
```

---

# Phase 17 — Grounded Generation

Implement LLM abstraction:

```text
LLMProvider
```

Generation must follow:

```text
Question
   ↓
Retrieved Evidence
   ↓
Context Builder
   ↓
LLM
   ↓
Grounded Answer
```

The LLM should not answer from unsupported knowledge when the task requires document grounding.

---

# Phase 18 — Citation System

Every generated claim should be traceable to retrieved evidence.

Example:

```text
Microsoft reported revenue of X.

[1]
```

Citation metadata:

```text
document_id
document_version_id
chunk_id
page_number
source
```

Frontend should allow the user to click a citation and inspect the supporting chunk.

---

# Phase 19 — Streaming Chat

Implement SSE.

Flow:

```text
Frontend
   ↓
POST /chat
   ↓
FastAPI
   ↓
Retrieval
   ↓
LLM
   ↓
SSE Stream
   ↓
Frontend
```

Stream:

* Tokens
* Citations
* Status
* Errors
* Completion

---

# Phase 20 — Conversation Memory

Store:

```text
Conversation
Message
Role
Content
Timestamp
```

Implement:

* Recent message memory
* Conversation summaries
* Context limits
* Conversation retrieval

Avoid sending the entire conversation to the LLM indefinitely.

---

# Phase 21 — Evaluation Dataset

Create dataset format:

```json
{
  "question": "...",
  "expected_answer": "...",
  "expected_documents": [],
  "expected_chunks": []
}
```

Create:

* Training-like examples
* Evaluation examples
* Edge cases
* Adversarial questions
* Multi-hop questions
* No-answer questions

---

# Phase 22 — Retrieval Evaluation

Implement:

### Recall@K

Measures whether relevant evidence appears in top K.

### Precision@K

Measures how many retrieved results are relevant.

### MRR

Measures the ranking position of the first relevant result.

### nDCG

Measures ranking quality while accounting for relevance levels.

Evaluate:

```text
BM25
Dense
Hybrid
Hybrid + Reranker
```

Compare the systems.

---

# Phase 23 — Generation Evaluation

Evaluate:

### Correctness

Is the answer correct?

### Faithfulness / Groundedness

Is the answer supported by retrieved evidence?

### Context relevance

Was useful evidence retrieved?

---

# Phase 24 — Citation Evaluation

Measure:

* Citation correctness
* Citation support
* Citation completeness
* Citation precision

Example:

```text
Claim
 ↓
Citation
 ↓
Chunk
 ↓
Does chunk support claim?
```

---

# Phase 25 — Evaluation Dashboard

Frontend dashboard should display:

```text
Retrieval Metrics
Generation Metrics
Citation Metrics
Latency
Token Usage
Cost
Failure Rate
```

Allow comparison:

```text
Dense
vs
BM25
vs
Hybrid
vs
Hybrid + Reranker
```

---

# Phase 26 — Observability

Implement:

```text
OpenTelemetry
Prometheus
Grafana
```

Track:

### API

* Request count
* Error rate
* Latency

### Retrieval

* Search latency
* Candidate count
* Reranking latency

### LLM

* Input tokens
* Output tokens
* Model
* Latency
* Cost

### Ingestion

* Processing time
* Failed documents
* OCR usage
* Chunk count

---

# Phase 27 — Security

Implement:

### Authentication

JWT.

### Authorization

Role-based access control.

### Multi-tenant isolation

Users must only access their tenant's data.

### File security

Validate:

* MIME type
* File extension
* File size
* File content

### SSRF protection

Required for webpage ingestion.

Prevent requests to:

```text
localhost
127.0.0.1
private IP ranges
metadata endpoints
internal services
```

### Prompt injection defense

Treat retrieved documents as untrusted data.

Never allow document content to directly override system instructions.

---

# Phase 28 — Performance

Benchmark:

```text
API latency
Retrieval latency
Embedding latency
Reranking latency
LLM latency
End-to-end latency
```

Track:

```text
P50
P95
P99
```

Optimize:

* Database indexes
* Connection pooling
* Redis caching
* Batch embeddings
* Qdrant configuration
* Context size
* Async processing

---

# Phase 29 — Reliability

Implement:

* Retries
* Timeouts
* Circuit breakers where appropriate
* Idempotency
* Dead-letter jobs
* Graceful failure
* Health checks
* Readiness checks
* Liveness checks

Example:

```text
LLM failure
   ↓
Retry
   ↓
Retry
   ↓
Fallback provider
   ↓
Return controlled error
```

---

# Phase 30 — Testing

Testing layers:

```text
Unit Tests
    ↓
Integration Tests
    ↓
API Tests
    ↓
Retrieval Tests
    ↓
Security Tests
    ↓
E2E Tests
```

Test:

* RRF
* BM25
* Retrieval filters
* Chunking
* Citation mapping
* Tenant isolation
* Authentication
* Ingestion idempotency
* Retry behavior

---

# Phase 31 — Load Testing

Simulate:

```text
10 users
50 users
100 users
500 users
```

Measure:

* Requests/sec
* P50
* P95
* P99
* Error rate
* CPU
* RAM
* Database connections
* Redis queue depth

---

# Phase 32 — CI/CD

Frontend pipeline:

```text
Install
 ↓
Lint
 ↓
Typecheck
 ↓
Unit tests
 ↓
Build
 ↓
Deploy
```

Backend pipeline:

```text
Install
 ↓
Lint
 ↓
Typecheck
 ↓
Unit tests
 ↓
Integration tests
 ↓
Build Docker image
 ↓
Deploy
```

Frontend and backend should be independently deployable.

---

# Phase 33 — Production Deployment

Target architecture:

```text
                    Internet
                       │
                       ▼
                  Cloudflare
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
       Frontend                Backend
        Hosting               FastAPI
                                  │
             ┌────────────────────┼───────────────────┐
             │                    │                   │
             ▼                    ▼                   ▼
         PostgreSQL             Redis              Qdrant
             │
             │
             ▼
        Cloudflare R2
```

Frontend and backend must be deployable independently.

---

# 13. Agentic AI Extension

After the production RAG system is stable, add an agentic layer.

Do NOT start with agents.

The deterministic RAG system must work first.

---

## Agent Architecture

```text
User Question
      ↓
Agent Planner
      ↓
┌─────┼─────────────┐
│     │             │
▼     ▼             ▼
Search  Metadata   Document
Tool    Tool       Tool
│
▼
Evidence
      ↓
Reasoning
      ↓
Verification
      ↓
Final Answer
```

---

# 14. Agent Tools

Potential tools:

```text
semantic_search
keyword_search
document_search
metadata_search
document_reader
citation_verifier
calculator
conversation_memory
```

---

# 15. Agentic Retrieval Example

Question:

> "Compare the security policies of Company A and Company B and identify where they differ."

Agent:

```text
1. Identify entities
2. Search Company A policies
3. Search Company B policies
4. Retrieve relevant sections
5. Compare evidence
6. Detect missing information
7. Perform additional retrieval
8. Verify claims
9. Generate answer
10. Attach citations
```

---

# 16. Agent Evaluation

Evaluate:

* Tool selection
* Planning accuracy
* Number of unnecessary tool calls
* Retrieval quality
* Final answer correctness
* Groundedness
* Citation accuracy
* Agent latency
* Agent cost
* Failure recovery

---

# 17. Development Philosophy

This project should NOT be built by asking an AI:

> "Build the entire project."

Instead, use AI as:

```text
Architect
Teacher
Code Reviewer
Debugger
Test Designer
Research Assistant
Documentation Assistant
```

---

# 18. Implementation Loop

For every subsystem:

```text
Understand
    ↓
Research
    ↓
Design
    ↓
Document
    ↓
Define Interfaces
    ↓
Write Pseudocode
    ↓
Implement
    ↓
Write Tests
    ↓
Run Tests
    ↓
Debug
    ↓
Review
    ↓
Refactor
    ↓
Commit
```

You should understand why every major component exists.

---

# 19. Git Branch Strategy

Use feature branches.

Examples:

```text
feat/frontend-foundation
feat/backend-foundation
feat/auth
feat/multi-tenancy
feat/document-upload
feat/ingestion-worker
feat/document-parsing
feat/ocr
feat/chunking
feat/embeddings
feat/vector-search
feat/lexical-search
feat/hybrid-retrieval
feat/reranking
feat/query-understanding
feat/chat
feat/citations
feat/evaluation
feat/observability
feat/security
feat/performance
feat/agentic-rag
```

---

# 20. Commit Convention

Use conventional commits.

Examples:

```text
feat: add document upload API

feat: implement hybrid retrieval

fix: prevent duplicate ingestion jobs

fix: isolate tenant document queries

test: add RRF ranking tests

test: add citation verification tests

perf: optimize embedding batching

docs: document OCR architecture

refactor: extract embedding provider interface
```

---

# 21. Definition of Done

The project is considered complete when:

### Frontend

* Authentication works
* Document management works
* Search works
* Chat works
* Citations work
* Evaluation dashboard works
* Observability dashboard is accessible

### Backend

* FastAPI APIs work
* Authentication works
* Multi-tenancy works
* Async ingestion works
* OCR works
* Parsing works
* Chunking works
* Embeddings work
* Hybrid retrieval works
* Reranking works
* Grounded generation works
* Citations work
* Evaluation works

### Infrastructure

* PostgreSQL works
* Redis works
* Qdrant works
* R2 works
* Docker works
* CI/CD works
* Monitoring works

### Production

* Frontend independently deployable
* Backend independently deployable
* Workers independently deployable
* Database migrations work
* Health checks work
* Logging works
* Metrics work
* Error handling works

### AI

* Retrieval evaluated
* Generation evaluated
* Citations evaluated
* Agentic retrieval implemented
* Agent evaluated

---

# 22. Resume Positioning

Do not describe the project as:

> Built a RAG chatbot.

Instead:

> **Enterprise Knowledge Intelligence Platform**

Highlight:

* Multi-tenancy
* Async ingestion
* Document versioning
* Adaptive OCR
* Structure-aware chunking
* Hybrid retrieval
* BM25
* Dense retrieval
* RRF
* Cross-encoder reranking
* Query rewriting
* Grounded generation
* Citation verification
* Evaluation framework
* OpenTelemetry
* Prometheus
* Grafana
* Docker
* CI/CD
* Agentic retrieval

Only include numerical performance claims after running real benchmarks.

---

# 23. Final System

The final architecture should look approximately like:

```text
                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │  FRONTEND   │
                    │ React/Vite  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   FASTAPI   │
                    │ API Gateway │
                    └──────┬──────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
        PostgreSQL       Redis         Qdrant
             │             │             │
             │             ▼             │
             │        ┌──────────┐       │
             │        │ Workers  │       │
             │        └────┬─────┘       │
             │             │             │
             │      ┌──────┴───────┐     │
             │      │              │     │
             │      ▼              ▼     │
             │   Ingestion     Embedding │
             │      │              │     │
             │      └──────┬───────┘     │
             │             │             │
             │             ▼             │
             │       Cloudflare R2       │
             │                           │
             └──────────────┬────────────┘
                            │
                            ▼
                     Retrieval Engine
                            │
                ┌───────────┼───────────┐
                │           │           │
                ▼           ▼           ▼
             BM25        Dense        Query
                │           │       Rewriting
                └─────┬─────┘           │
                      ▼                 │
                    RRF ◄───────────────┘
                      │
                      ▼
                  Reranker
                      │
                      ▼
                Context Builder
                      │
                      ▼
                    LLM
                      │
                      ▼
             Citation Verification
                      │
                      ▼
                SSE Streaming
                      │
                      ▼
                  FRONTEND


              ───── AGENTIC LAYER ─────

                    User Query
                        │
                        ▼
                   Agent Planner
                        │
             ┌──────────┼───────────┐
             ▼          ▼           ▼
          Search     Metadata    Document
           Tool        Tool        Tool
             │          │           │
             └──────────┼───────────┘
                        ▼
                    Reasoning
                        │
                        ▼
                   Verification
                        │
                        ▼
                  Final Answer
```

---

# 24. Core Principle

The most important principle of this project is:

> **Build the simplest correct system first, measure it, understand its weaknesses, and then make it more sophisticated.**

Do not add:

* Agents
* Microservices
* Complex orchestration
* Multiple LLMs
* Multiple vector databases
* Kubernetes
* Distributed infrastructure

just because they sound impressive.

Every architectural component must solve a real problem.

The final project should demonstrate that you can take an AI system from:

```text
Idea
 ↓
Architecture
 ↓
Implementation
 ↓
Testing
 ↓
Evaluation
 ↓
Debugging
 ↓
Optimization
 ↓
Observability
 ↓
Security
 ↓
Deployment
 ↓
Production
```

That is the actual objective of this project.
