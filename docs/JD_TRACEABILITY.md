# Job Description Traceability Matrix (`docs/JD_TRACEABILITY.md`)

**Target Role:** Decision Science Practitioner Associate (0–2 years)  
**Evaluation Scope:** Complete functional verification of technical requirements, architectural patterns, and testing artifacts in EKIA.

---

## 1. Core Technical Requirements (Must Have)

| JD Requirement | Implementation File(s) | Test File(s) | Documentation | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Python** | `backend/app/**/*.py`, `scripts/*.py`, `evals/*.py` | `backend/tests/test_*.py` (69 tests) | `docs/ARCHITECTURE.md` | **Done** | Python 3.12+ async FastAPI backend, typed Pydantic models, SQLAlchemy async. |
| **SQL** | `backend/app/db/session.py`, `backend/app/models/*.py`, `backend/migrations/` | `backend/tests/test_security_accounts.py`, `backend/tests/test_tools.py` | `docs/ARCHITECTURE.md` | **Done** | PostgreSQL 16 schema, Alembic migrations, parameterized queries preventing SQL injection. |
| **JSON** | `backend/app/api/*.py`, `evals/reports/*.json`, `backend/app/services/llm.py` | `backend/tests/test_bedrock_llm.py`, `backend/tests/test_tools.py` | `docs/API.md` | **Done** | Pydantic JSON schemas, AWS Bedrock JSON payload serialization, evaluation JSON reporting. |
| **REST APIs** | `backend/app/api/auth.py`, `chat.py`, `documents.py`, `retrieval.py`, `tools.py` | `backend/tests/test_auth.py`, `backend/tests/test_tools.py`, `test_security_accounts.py` | `docs/API.md` | **Done** | OpenAPI-compliant REST endpoints with JWT bearer auth, error handling, and rate limits. |
| **Generative AI Fundamentals** | `backend/app/services/llm.py`, `backend/app/rag/pipeline.py` | `backend/tests/test_rag.py`, `backend/tests/test_bedrock_llm.py` | `docs/ARCHITECTURE.md` | **Done** | Modular LLM abstraction (Gemini 2.0 Flash & AWS Bedrock Claude 3), temperature tuning, streaming. |
| **Prompt Engineering** | `backend/app/rag/prompts.py`, `backend/app/rag/prompts/answer_v1.txt`, `answer_v2.txt` | `backend/tests/test_rag.py::test_prompt_version_is_set`, `evals/eval_runner.py` | `docs/PROMPT_LOG.md` | **Done** | Versioned prompts (`PROMPT_VERSION`), grounding instructions, empirical regression logging. |
| **LLM Applications** | `backend/app/rag/pipeline.py`, `backend/app/agents/graph.py` | `backend/tests/test_rag.py`, `backend/tests/test_agent_graph.py` | `README.md`, `docs/ARCHITECTURE.md` | **Done** | Complete end-to-end enterprise knowledge assistant with UI chat, streaming, and tool execution. |
| **Basic RAG & AI Assistants** | `backend/app/rag/pipeline.py`, `backend/app/rag/retrieval.py` | `backend/tests/test_rag.py` | `docs/ARCHITECTURE.md`, `docs/EVALUATION.md` | **Done** | Document chunking, vector search, formatted context, verified citations (`[Source 1]`). |

---

## 2. Advanced & Differentiating Competencies (Good to Have)

| JD Requirement | Implementation File(s) | Test File(s) | Documentation | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LangChain / LangGraph** | `backend/app/agents/graph.py` | `backend/tests/test_agent_graph.py` (4 tests) | `docs/AGENT_GRAPH.md` | **Done** | Pinned `langgraph==1.2.14`. Implemented typed `StateGraph` with router, retrieve, generate, tool_node, guardrail, fallback. |
| **Agentic AI Concepts** | `backend/app/agents/graph.py`, `backend/app/tools/tools.py` | `backend/tests/test_agent_graph.py` | `docs/AGENT_GRAPH.md` | **Done** | Autonomous intent routing, tool selection, conditional fallback on hallucination/failure. |
| **Tool Calling** | `backend/app/tools/tools.py`, `backend/app/api/tools.py` | `backend/tests/test_tools.py` (12 tests) | `docs/API.md`, `docs/AGENT_GRAPH.md` | **Done** | Allowlisted tools (`search_knowledge_base`, `lookup_policy_record`, `create_support_request`), Pydantic validation, RBAC. |
| **Workflow Orchestration** | `backend/app/agents/graph.py` | `backend/tests/test_agent_graph.py` | `docs/AGENT_GRAPH.md` | **Done** | Deterministic cyclic/branching StateGraph returning structured execution trace with step timings. |
| **Vector Databases (pgvector)** | `backend/app/models/document.py`, `backend/migrations/` | `backend/tests/test_ingestion.py`, `backend/tests/test_evaluation_runner.py` | `docs/ARCHITECTURE.md` | **Done** | PostgreSQL 16 `pgvector` extension, 768-dim vector embeddings, HNSW indexing support. |
| **Embeddings** | `backend/app/services/embedding.py` | `backend/tests/test_ingestion.py::test_fake_embedding_*` | `docs/ARCHITECTURE.md` | **Done** | Google `models/gemini-embedding-001` (768-dim MRL), deterministic normalized fake embeddings for tests. |
| **Enterprise Knowledge Retrieval** | `backend/app/rag/retrieval.py`, `backend/app/services/ingestion.py` | `backend/tests/test_rag.py`, `backend/tests/test_kb_validation.py` | `docs/ARCHITECTURE.md` | **Done** | Document extraction (PDF, TXT, DOCX), chunking with overlap, cosine similarity retrieval. |
| **Scikit-learn** | `scripts/validate_kb.py` | `backend/tests/test_kb_validation.py` (6 tests) | `docs/FINDINGS_REPORT.md` | **Done** | `TfidfVectorizer` and `cosine_similarity` used for automated near-duplicate knowledge detection (>85% threshold). |
| **AWS AI Services** | `backend/app/services/llm.py` (`BedrockLLMProvider`) | `backend/tests/test_bedrock_llm.py` (5 tests) | `docs/DEPLOYMENT.md` | **Done** | Amazon Bedrock Claude 3 Haiku & Titan integration via `boto3` default credential chain. |
| **Azure AI Services** | - | - | - | **Not done** | AWS Bedrock and Google Gemini implemented; Azure OpenAI / Azure AI Search not implemented. |
| **Git & Version Control** | Repository git history, branch management | - | `README.md` | **Done** | Clean feature branches (`feature/knowledge-validation`, `feature/aws-bedrock-provider`), conventional commits. |
| **Docker & Multi-Container** | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | Tested via `docker compose config` | `docs/DEPLOYMENT.md` | **Done** | Multi-container setup for FastAPI, Next.js, and PostgreSQL pgvector. |
| **CI/CD Pipeline** | `.github/workflows/ci.yml` | GitHub Actions workflow execution | `README.md` | **Done** | Automated GitHub Actions CI workflow running linting, formatting, and pytest test suite. |
| **Software Development Lifecycle (SDLC)** | Environment configs, migrations, logging | `backend/tests/` | `docs/FINDINGS_REPORT.md` | **Done** | Safe defaults, config tiers (`development`, `test`, `production`), Alembic migrations. |
| **Technical Documentation** | `README.md`, `docs/*.md` (8 markdown guides) | - | All doc files | **Done** | Complete system blueprints, API schemas, evaluation reports, and deployment guides. |

---

## 3. Operational Responsibilities Traceability

| JD Responsibility | Code Artifact | Test Artifact | Documentation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Build LLM Apps with Prompts & APIs** | `backend/app/api/chat.py`, `backend/app/rag/pipeline.py` | `backend/tests/test_rag.py` | `docs/API.md`, `docs/PROMPT_LOG.md` | **Done** |
| **Prepare, Organize & Validate Knowledge Sources** | `scripts/validate_kb.py`, `backend/app/services/ingestion.py` | `backend/tests/test_kb_validation.py` | `docs/FINDINGS_REPORT.md` | **Done** |
| **Build & Test Conversational AI / Agent Workflows** | `backend/app/agents/graph.py` | `backend/tests/test_agent_graph.py` | `docs/AGENT_GRAPH.md` | **Done** |
| **Perform Functional Testing & AI Evaluation** | `evals/eval_runner.py`, `backend/tests/` | `backend/tests/test_evaluation_runner.py` | `docs/EVALUATION.md`, `README.md` | **Done** |

---

## 4. Gaps & Intentional Non-Implementations

1. **Azure AI Services**: Marked as **Not done**. The system supports multi-cloud execution via Google Gemini 2.0 and AWS Bedrock Claude 3 Haiku, but does not provide an Azure OpenAI wrapper.
2. **Scanned PDF OCR**: Marked as **Not done**. Ingestion parses text-based PDFs, DOCX, and TXT files; OCR for handwritten/scanned images was not implemented to keep dependencies lightweight.
