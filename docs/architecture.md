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
Authentication + Tenant Context
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

The route should not contain the entire business workflow.

Conceptually:

```text
HTTP Request
 ↓
Route
 ↓
Validation
 ↓
Service
 ↓
Repository / external provider
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

Do not store original PDFs in PostgreSQL.

---

# 7. Tenant Model

Core relationship:

```text
Organization
    │
    ├── Members
    ├── Documents
    ├── Conversations
    └── Evaluation datasets
```

Every tenant-scoped entity should be associated with an organization.

Conceptually:

```text
organization_id
```

must flow through:

```text
HTTP request
 ↓
authenticated user
 ↓
tenant context
 ↓
service
 ↓
repository
 ↓
database/vector search
```

Tenant isolation must not depend only on the frontend.

The backend must enforce it.

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
Tenant resolution
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
Authentication
 ↓
Authorization
 ↓
Tenant Context
 ↓
Service
 ↓
Data Layer
```

Never trust:

- tenant IDs supplied by clients
- document IDs without authorization checks
- citation IDs without tenant validation
- URL destinations
- uploaded MIME types

All should be validated server-side.

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
 └── Tenant Context
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
