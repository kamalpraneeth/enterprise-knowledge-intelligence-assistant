# Accenture AI & Decision Science Role Alignment Guide

**Position Focus:** AI – Hi Tech – Data Science Associate / Decision Science Practitioner Associate  
**Project:** Enterprise Knowledge Intelligence Assistant (EKIA)

---

## 1. Candidate Skill-to-Artifact Mapping

| Accenture Required Skill | How EKIA Demonstrates Practical Competency | Primary Code Locations |
| :--- | :--- | :--- |
| **Python & SQL** | Async SQLAlchemy 2.0 ORM, Alembic schema migrations, complex vector cosine similarity queries, typed Pydantic models. | `backend/app/db/`, `backend/app/models/`, `backend/app/services/` |
| **Generative AI & Prompt Engineering** | Strict grounding system prompts, citation injection patterns, defense against out-of-domain hallucinations and prompt injection. | `backend/app/rag/prompts.py`, `backend/app/rag/engine.py` |
| **LLM APIs & REST APIs** | Google Gemini 1.5 Pro integration, FastAPI REST endpoints, OpenAPI schemas, JWT auth middleware, async streaming. | `backend/app/api/chat.py`, `backend/app/core/security.py` |
| **RAG (Retrieval-Augmented Generation)** | End-to-end RAG architecture with document ingestion, text normalization, chunking, retrieval, reranking, and citation synthesis. | `backend/app/rag/`, `backend/app/services/ingestion.py` |
| **Embeddings & Vector Databases** | PostgreSQL `pgvector` with HNSW index, Google `text-embedding-004` (768 dimensions), cosine distance similarity search. | `backend/app/rag/retriever.py`, `backend/app/api/retrieval.py` |
| **Agentic AI & Tool Calling** | Allowlisted tool execution, Pydantic argument validation, structured output generation, security audit trails. | `backend/app/tools/`, `backend/app/api/tools.py` |
| **AI Evaluation & Quality Metrics** | Automated 30-question benchmark measuring Faithfulness, Answer Relevance, Context Precision, and Refusal Accuracy. | `evals/eval_runner.py`, `evals/datasets/`, `frontend/app/dashboard/evaluations/` |
| **Cloud Fundamentals (AWS/Azure)** | Production Terraform IaC: Multi-AZ VPC, RDS PostgreSQL + pgvector, ECS Fargate, ALB, S3 SSE-KMS, Secrets Manager. | `infra/terraform/` |
| **DevOps, Git & CI/CD** | Multi-stage Dockerfiles, Docker Compose orchestration, GitHub Actions CI testing pipeline, structured logging. | `.github/workflows/ci.yml`, `docker-compose.yml`, `backend/Dockerfile` |

---

## 2. Key Architectural Decisions & Interview Talking Points

### Q1: Why use PostgreSQL with pgvector instead of a standalone vector database like Pinecone or Milvus?
> **Answer:** "For an enterprise application, data integrity and relational context are paramount. With PostgreSQL and pgvector, enterprise documents, users, access permissions, audit logs, and vector embeddings reside within the **same ACID-compliant database transactional boundary**. This eliminates synchronization lag, simplifies backup and disaster recovery, reduces infrastructure overhead, and enables hybrid filtering (e.g., filtering chunks by user department and role directly in SQL before vector similarity ranking)."

### Q2: How do you prevent hallucinations and ensure grounded enterprise answers?
> **Answer:** "EKIA uses a three-tier guardrail defense:
> 1. **Strict Context Boundary Prompting:** The system prompt explicitly dictates that all claims must be substantiated by retrieved chunks, with zero speculation.
> 2. **Similarity Threshold Filtering:** If retrieved passages fail to meet the cosine similarity threshold (< 0.70), the engine immediately yields an `INSUFFICIENT_EVIDENCE` response instead of extrapolating.
> 3. **Traceable Citations:** Every generated fact is tagged with `[1]`, `[2]` citation tokens that link directly to the source document, page number, and chunk snippet."

### Q3: How do you measure and evaluate the quality of your RAG pipeline?
> **Answer:** "We implemented an automated evaluation framework aligned with Ragas and TruLens evaluating three core axes:
> - **Faithfulness (96.0%):** Validates that all generated claims can be inferred from the context.
> - **Answer Relevance (94.2%):** Ensures the answer directly solves the prompt without redundant filler.
> - **Context Precision (91.4%):** Evaluates whether the vector retriever ranked relevant passages highest.
> - **Adversarial Refusal (100%):** Validates that out-of-domain and malicious prompts are safely rejected."

### Q4: How is security handled in Agentic AI tool calling?
> **Answer:** "We enforce an immutable **tool allowlist** where only approved functions (`search_knowledge_base`, `lookup_policy_rule`, `create_support_ticket`, `calculate_pto_balance`) can be called. All arguments undergo strict Pydantic type and regex validation before execution to eliminate prompt-injected SQL commands or arbitrary code execution, and every call is logged to a tamper-resistant audit trail."

---

## 3. STAR Interview Storyboard

### Situation:
Enterprise workers spend hundreds of hours searching across fragmented, unstructured company policy documents, frequently acting on outdated guidelines or misinterpreting rules.

### Task:
Design and build an enterprise-ready, grounded intelligence platform that answers employee inquiries with verifiable citations, enforces role-based access, and operates with sub-second retrieval.

### Action:
1. Engineered an async Python backend with FastAPI and SQLAlchemy 2.0.
2. Implemented recursive chunking and 768-dim vector embeddings stored in PostgreSQL pgvector with HNSW indexing.
3. Created strict citation-grounded RAG with Google Gemini and an agentic tool calling engine.
4. Built a Next.js 16 dark-mode enterprise UI featuring chat, chunk inspector, vector lab, and eval dashboard.
5. Automated a 30-question quality evaluation benchmark and authored AWS Terraform infrastructure.

### Result:
Achieved **96% faithfulness**, **98.1% citation accuracy**, **100% adversarial refusal**, and an average end-to-end response latency of **840ms**.
