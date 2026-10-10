# Enterprise Knowledge Intelligence Assistant (EKIA) — Architecture Specification

## 1. Architectural Overview

The **Enterprise Knowledge Intelligence Assistant (EKIA)** is a production-grade Generative AI and Decision Science application built for high-reliability enterprise document querying, compliance policy navigation, and agentic task execution.

```mermaid
flowchart TD
    subgraph Client["Client Tier (Next.js 16 + Tailwind CSS)"]
        UI[Enterprise Web UI]
        Chat[Knowledge Chat Console]
        DocMgr[Document Ingestion & Chunk Inspector]
        VecLab[Vector Retrieval Lab]
        ToolsUI[Agentic Tools Console]
        EvalUI[RAG Evaluation Dashboard]
    end

    subgraph Gateway["API Gateway / Security Tier (FastAPI)"]
        Router[API Router]
        AuthGuard[JWT & RBAC Middleware]
        AuditLog[Structured Security Logger]
        RateLimit[Rate Limiter & Input Validator]
    end

    subgraph RAG["Retrieval-Augmented Generation Engine"]
        Chunker[Recursive Character Chunker (500 tokens, 50 overlap)]
        Embedder[Google text-embedding-004 (768-dim)]
        Retriever[pgvector Cosine Distance Search (HNSW)]
        Reranker[Heuristic MMR / Score Filter]
        PromptEngine[Grounded Prompt Template (Strict Citations)]
        LLM[Google Gemini 1.5 Pro / Flash]
    end

    subgraph Data["Persistence & Vector Tier"]
        PG[(PostgreSQL 16 + pgvector)]
        S3[(AWS S3 / Local Storage - Raw Documents)]
        Alembic[Database Migrations]
    end

    subgraph Tools["Agentic AI Tool Execution Engine"]
        Allowlist[Tool Allowlist Registry]
        PydanticVal[Pydantic Argument Validator]
        KBTool[search_knowledge_base]
        PolicyTool[lookup_policy_rule]
        PTOTool[calculate_pto_balance]
        TicketTool[create_support_ticket]
    end

    UI --> Router
    Router --> AuthGuard
    AuthGuard --> AuditLog
    AuthGuard --> RateLimit
    RateLimit --> RAG
    RateLimit --> Tools

    DocMgr --> Chunker
    Chunker --> Embedder
    Embedder --> PG

    Chat --> Retriever
    Retriever --> PG
    Retriever --> PromptEngine
    PromptEngine --> LLM
    LLM --> Chat

    Tools --> Allowlist
    Allowlist --> PydanticVal
    PydanticVal --> KBTool
    PydanticVal --> PolicyTool
    PydanticVal --> PTOTool
    PydanticVal --> TicketTool
```

---

## 2. Core Subsystems

### 2.1 Ingestion & Embedding Pipeline
1. **File Parsing**: Ingests PDF, DOCX, and TXT files via PyPDF and docx parsers.
2. **Text Normalization**: Strips excessive whitespace, extracts header metadata, and preserves section headings.
3. **Semantic Chunking**: Employs recursive character chunking (target window: 500 tokens, overlap: 50 tokens) to ensure contextual continuity across boundaries.
4. **Vector Embedding**: Generates 768-dimensional dense vector embeddings using Google's `text-embedding-004` model.
5. **Storage**: Stores text chunks, document foreign keys, chunk offsets, and vector embeddings in PostgreSQL using the `pgvector` extension.

### 2.2 Vector Search & Retrieval Engine
- **Indexing**: Uses an **HNSW (Hierarchical Navigable Small World)** vector index on PostgreSQL for sub-10ms nearest-neighbor search.
- **Distance Metric**: Evaluates Cosine Distance (`vector_cosine_ops`) between query embeddings and stored passage vectors.
- **Top-K Retrieval**: Defaults to Top-5 passages, dynamically tunable between 3 and 10 based on query intent.

### 2.3 Grounded Generation & Citation Verification
- **System Prompt**: Enforces strict evidence boundary conditions. The LLM is explicitly forbidden from introducing knowledge outside the provided retrieved context.
- **Citation Tracing**: Each fact synthesized in the response maps directly to `[1]`, `[2]` citation markers referencing the exact document title, page number, and chunk ID.
- **Refusal Mechanism**: If retrieved chunks lack sufficient semantic similarity (< 0.70 threshold) or fail to address the query, the engine returns an explicit `INSUFFICIENT_EVIDENCE` disclaimer rather than hallucinating.

### 2.4 Agentic AI Tool Execution
- Controlled tool calling enables the assistant to take deterministic actions:
  - `search_knowledge_base`: Retrieves chunks based on refined query.
  - `lookup_policy_rule`: Fetches official compliance rules by ID.
  - `calculate_pto_balance`: Deterministic HR mathematical calculation.
  - `create_support_ticket`: Emits support ticket with audit logging.
- Every parameter is strictly validated using Pydantic schemas before invocation, preventing injection attacks.

---

## 3. Security & Governance Architecture

| Dimension | Implementation Details |
| :--- | :--- |
| **Authentication** | Stateless JWT tokens with HS256 signatures, configurable expiration (60 mins), and password hashing via bcrypt. |
| **Role-Based Access Control (RBAC)** | Three distinct privilege tiers: **Admin** (user & role administration), **Knowledge Manager** (document upload, reindexing, evaluations), and **Employee** (querying & chat). |
| **Data Privacy** | Raw API keys never exposed to client; stored in environment variables / AWS Secrets Manager. |
| **Audit Trails** | All tool calls, queries, and document modifications logged with user identity, timestamp, and duration via structured logging (`structlog`). |
