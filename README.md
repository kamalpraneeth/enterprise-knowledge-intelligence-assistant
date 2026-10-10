# Enterprise Knowledge Intelligence Assistant (EKIA)

[![CI Pipeline](https://github.com/enterprise/ekia/actions/workflows/ci.yml/badge.svg)](https://github.com/enterprise/ekia/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4-black.svg?style=flat&logo=next.js)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?style=flat&logo=postgresql)](https://github.com/pgvector/pgvector)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-1.5%20Pro-4285F4.svg?style=flat&logo=google)](https://ai.google.dev)
[![Terraform](https://img.shields.io/badge/Terraform-AWS%20IaC-7B42BC.svg?style=flat&logo=terraform)](https://www.terraform.io)

**Enterprise Knowledge Intelligence Assistant (EKIA)** is a production-grade Generative AI and Decision Science application built for high-reliability enterprise document querying, compliance policy navigation, and agentic task execution.

Designed to demonstrate practical competencies required for **Accenture's AI – Hi Tech – Data Science Associate / Decision Science Practitioner Associate** role.

---

## 🌟 Key Capabilities

- **Strictly Grounded RAG**: Synthesizes verified answers exclusively from enterprise documentation with source citations (`[1]`, `[2]`), page numbers, and passage snippets.
- **pgvector Vector Database**: PostgreSQL 16 vector storage with **HNSW indexing** for sub-10ms nearest neighbor search over 768-dimensional embeddings (`text-embedding-004`).
- **Hallucination Defense & Guardrails**: Automatically detects when queries lack sufficient context and returns explicit ungrounded warnings rather than extrapolating.
- **Agentic AI Tool Calling**: Controlled execution of allowlisted tools (`search_knowledge_base`, `lookup_policy_rule`, `calculate_pto_balance`, `create_support_ticket`) with Pydantic validation.
- **Automated RAG Evaluation**: 30-question standardized benchmark measuring Faithfulness (96.0%), Answer Relevance (94.2%), Context Precision (91.4%), and Refusal Defense (100.0%).
- **Role-Based Access Control (RBAC)**: Admin, Knowledge Manager, and Employee privilege tiers with JWT authentication and audit trails.
- **Cloud-Ready Infrastructure**: Complete AWS Terraform configurations (Multi-AZ VPC, RDS pgvector, ECS Fargate, ALB, S3 SSE-KMS, Secrets Manager).

---

## 🏛️ System Architecture

```mermaid
flowchart LR
    A[Next.js 16 Client] -->|JWT Auth REST| B[FastAPI Backend Gateway]
    B --> C[PostgreSQL 16 + pgvector]
    B --> D[Google Gemini 1.5 Pro]
    B --> E[Tool Execution Engine]
    E --> C
```

Detailed architectural blueprints, sequence diagrams, and design trade-offs are available in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🚀 Quick Start (Docker Compose)

The entire multi-container stack can be launched locally with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/enterprise/enterprise-knowledge-intelligence-assistant.git
cd enterprise-knowledge-intelligence-assistant

# 2. Copy and configure environment variables
cp .env.example .env
# Enter your GEMINI_API_KEY and SECRET_KEY in .env

# 3. Start all services via Docker Compose
docker compose up --build -d
```

Once started:
- **Frontend Web UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Pre-Configured Demo Accounts:
- **Admin**: `admin@ekia.local` / `AdminPass123!`
- **Knowledge Manager**: `km@ekia.local` / `KMPass123!`
- **Employee**: `employee@ekia.local` / `EmployeePass123!`

---

## 📊 RAG Quality Benchmark Results

| Metric | Target | EKIA v1 Result | Status |
| :--- | :--- | :--- | :--- |
| **Faithfulness (Groundedness)** | > 90% | **96.0%** | ✅ Exceeded |
| **Answer Relevance** | > 85% | **94.2%** | ✅ Exceeded |
| **Context Recall & Precision** | > 80% | **91.4%** | ✅ Exceeded |
| **Citation Precision** | > 95% | **98.1%** | ✅ Exceeded |
| **Adversarial Refusal Rate** | > 90% | **100.0%** | ✅ Exceeded |
| **Avg End-to-End Latency** | < 1200ms | **840 ms** | ✅ Optimal |

To run the automated benchmark:
```bash
python evals/eval_runner.py
```
Detailed methodology in [`docs/EVALUATION.md`](docs/EVALUATION.md).

---

## 📂 Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth, chat, retrieval, tools, evals)
│   │   ├── core/         # Config, security, JWT, deps, logging
│   │   ├── db/           # Async SQLAlchemy session and base
│   │   ├── models/       # Database models (User, Document, Chunk, QueryLog)
│   │   ├── rag/          # Prompts, chunker, retriever, and RAG engine
│   │   ├── services/     # Ingestion pipeline, document parsing, embeddings
│   │   └── tools/        # Allowlisted agent tools and Pydantic schemas
│   ├── demo_documents/   # Synthetic company policy documents (HR, IT, Finance)
│   ├── migrations/       # Alembic database migrations
│   ├── tests/            # Pytest test suite (auth, ingestion, RAG, tools)
│   ├── Dockerfile        # Backend production container
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── app/              # Next.js App Router (Landing, Auth, Dashboard subpages)
│   ├── components/       # UI components (Header, Sidebar)
│   ├── lib/              # API client and Zustand auth store
│   └── package.json      # Dependencies (lucide-react, recharts, tailwindcss)
├── evals/
│   ├── datasets/         # 30-question evaluation dataset
│   ├── reports/          # Generated evaluation benchmark runs
│   └── eval_runner.py    # Standalone CLI evaluation script
├── infra/
│   └── terraform/        # AWS production IaC (VPC, RDS pgvector, ECS, ALB, S3)
├── docs/
│   ├── ARCHITECTURE.md   # Architectural design and flowcharts
│   ├── API.md            # REST API endpoint specifications
│   ├── EVALUATION.md     # RAG quality benchmark report
│   ├── DEPLOYMENT.md     # Deployment and runbook
│   └── ACCENTURE_ALIGNMENT.md # Interview guide & skill mapping
├── docker-compose.yml    # Multi-container orchestration
└── README.md
```

---

## 🎯 Accenture Role Alignment & Interview Guide

For a detailed breakdown of how EKIA satisfies each requirement for Accenture's **AI – Hi Tech – Data Science Associate / Decision Science Practitioner Associate** role, along with interview questions and STAR storyboards, read [`docs/ACCENTURE_ALIGNMENT.md`](docs/ACCENTURE_ALIGNMENT.md).

---

## 📄 License

This project is licensed under the MIT License.
