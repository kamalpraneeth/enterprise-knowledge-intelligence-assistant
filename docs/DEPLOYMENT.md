# EKIA Deployment & Operations Guide

## 1. Quick Start with Docker Compose

The easiest way to run the full application (PostgreSQL + pgvector, FastAPI Backend, and Next.js Frontend) is using `docker-compose.yml`:

```bash
# 1. Clone or navigate to the repository
cd enterprise-knowledge-intelligence-assistant

# 2. Configure environment variables
cp .env.example .env
# Edit .env and enter your GEMINI_API_KEY and SECRET_KEY

# 3. Build and launch all services
docker compose up --build -d

# 4. Access the web interface
# Frontend: http://localhost:3000
# Backend API Docs: http://localhost:8000/docs
```

---

## 2. Local Manual Development Setup

### Backend (FastAPI + Python 3.12)
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (Next.js 16)
```bash
cd frontend
npm install
npm run dev
# Accessible at http://localhost:3000
```

---

## 3. Production AWS Deployment via Terraform

The `infra/terraform/` directory contains production Infrastructure-as-Code for AWS:
- **VPC & Subnets**: Multi-AZ public and private subnets with NAT gateways.
- **Amazon RDS**: PostgreSQL 16 with `pgvector` extension enabled.
- **AWS ECS Fargate**: Serverless container orchestration for Backend and Frontend.
- **Application Load Balancer**: SSL termination with path-based routing (`/api/*` to FastAPI, `/*` to Next.js).
- **Amazon S3**: SSE-KMS encrypted storage for raw corporate documents.

### Provisioning Steps
```bash
cd infra/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

---

## 4. Environment Variables Reference

| Variable | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql+asyncpg://...` |
| `GEMINI_API_KEY` | Google Gemini API Key | Yes | - |
| `SECRET_KEY` | JWT signing secret key | Yes | - |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration duration in minutes | No | `60` |
| `NEXT_PUBLIC_API_URL` | Base API URL for frontend client | No | `http://localhost:8000` |
| `CORS_ORIGINS` | Allowed origins for API requests | No | `["http://localhost:3000"]` |
