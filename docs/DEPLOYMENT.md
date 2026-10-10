# Enterprise Knowledge Intelligence Assistant (EKIA) — Deployment Guide

This guide details deployment options for EKIA, focusing on cost efficiency, enterprise cloud security, and IAM role governance.

---

## 1. Cloud Architecture & Cost Guardrails

> [!WARNING]
> **TERRAFORM STACK COST WARNING**:  
> The multi-AZ production Terraform configuration in `infra/terraform/` (AWS ECS Fargate + Multi-AZ RDS PostgreSQL + Application Load Balancer + Dual NAT Gateways) is an enterprise production blueprint. It is **NOT intended for AWS Free Tier or personal demo credits**. Idle NAT Gateways alone cost ~$65+/month before database or compute charges.  
>  
> For portfolios, staging, and evaluations, deploy using the **Single Small EC2 Instance (Docker Compose + IAM Instance Profile)** detailed below.

### Monthly Cost Estimation Comparison

| Resource / Pattern | Hourly Cost | Monthly Cost (24/7) | Free Tier / Credit Safe? |
| :--- | :--- | :--- | :--- |
| **Recommended: Single EC2 (`t3.medium`, 2 vCPU, 4GB RAM)** | ~$0.0416 | ~$30.00 | **Yes** (or ~$15/mo on `t3.small`) |
| **Root EBS Volume (20GB gp3)** | - | ~$1.60 | **Yes** (within 30GB free tier) |
| **Amazon Bedrock (Claude 3 Haiku)** | Pay-per-token | ~$0.50 - $2.00 / 10k queries | **Yes** (No idle costs) |
| *Enterprise Terraform Stack (NAT Gateways + RDS + ECS)* | ~$0.16+ | ~$115.00+ | **NO (Exceeds free tier)** |

---

## 2. Low-Cost Deployment: Single EC2 Instance + IAM Role

This production pattern runs the full containerized stack (PostgreSQL + pgvector, FastAPI, Next.js) on a single EC2 instance, using **IAM Instance Profile** credentials for Amazon Bedrock.

### Key Security Feature: Zero Stored Credentials
No AWS access keys (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) are stored in `.env`, Docker containers, or configuration files. The backend uses `boto3`'s default credential chain, which automatically retrieves rotating temporary credentials from the EC2 Instance Metadata Service (IMDSv2).

### Step 1: Create the IAM Role for EC2
1. Open the **AWS IAM Console** -> **Roles** -> **Create Role**.
2. Select **AWS service** -> **EC2**.
3. Attach the managed policy:
   - `AmazonBedrockFullAccess` (or create a custom least-privilege policy allowing `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`).
4. Name the role: `ekia-ec2-bedrock-role`.

### Step 2: Launch EC2 Instance
1. AMI: **Ubuntu Server 24.04 LTS** (or Amazon Linux 2023).
2. Instance Type: **t3.medium** (recommended: 4GB RAM is required for compiling Next.js and hosting pgvector) or **t3.small** with swap.
3. Storage: 20 GiB gp3 EBS.
4. Advanced Details -> **IAM instance profile**: Attach `ekia-ec2-bedrock-role`.
5. Security Group Inbound Rules:
   - `SSH (22)`: Source = `My IP` (do NOT leave open to 0.0.0.0/0).
   - `HTTP (80)` or `3000`: Inbound web access.
   - `8000`: FastAPI backend (or reverse-proxy via Nginx/Caddy).

### Step 3: Server Provisioning Commands
Connect via SSH to your EC2 instance and execute:

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install Docker & Docker Compose Plugin
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# 3. Clone Repository
git clone https://github.com/kamalpraneeth/enterprise-knowledge-intelligence-assistant.git
cd enterprise-knowledge-intelligence-assistant

# 4. Configure Production Environment
cp .env.example .env
```

### Step 4: Configure `.env` for Bedrock or Gemini
Edit `.env`:

```env
# Database Settings
DATABASE_URL=postgresql+asyncpg://ekia_user:securepassword@db:5432/ekia_db
POSTGRES_USER=ekia_user
POSTGRES_PASSWORD=securepassword
POSTGRES_DB=ekia_db

# Security & Secrets
SECRET_KEY=generate-a-strong-random-hex-key-here
APP_ENV=production

# Provider Selection (Bedrock or Gemini)
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# If using Google Gemini instead:
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=AIzaSy...
# LLM_MODEL=gemini-2.0-flash
# EMBEDDING_MODEL=models/gemini-embedding-001
# EMBEDDING_DIMENSION=768
```

### Step 5: Launch Stack
```bash
docker compose up --build -d
docker compose ps
```

---

## 3. Teardown Checklist (Stop Cloud Spending)

When you are done testing or demonstrating the application, follow this teardown checklist immediately to avoid unexpected AWS charges:

- [ ] **1. Terminate or Stop the EC2 Instance**:
  - Open AWS EC2 Console -> Select instance -> **Instance State** -> **Terminate Instance**.
  - (If only stopping for later demo: select **Stop Instance**; EBS storage fee is ~$1.60/month).
- [ ] **2. Release Elastic IP (if assigned)**:
  - EC2 Console -> **Elastic IPs** -> Select IP -> Actions -> **Release Elastic IP addresses**. (Unattached Elastic IPs incur charges!).
- [ ] **3. Delete Custom Security Groups**:
  - EC2 Console -> Security Groups -> Delete `ekia-sg`.
- [ ] **4. Delete IAM Instance Profile & Role**:
  - IAM Console -> Roles -> Delete `ekia-ec2-bedrock-role`.
- [ ] **5. Delete EBS Snapshots & Volumes**:
  - EC2 Console -> Volumes -> Check for orphaned detached volumes -> Delete.
- [ ] **6. Verify CloudWatch Alarms & Log Groups**:
  - CloudWatch Console -> Log groups -> Delete `/aws/bedrock` or custom app log groups.

---

## 4. Local Quick Start (Docker Compose)

For offline testing without cloud infrastructure:

```bash
docker compose up --build -d
```

The system initializes with SQLite/PostgreSQL in-memory mocks and deterministic evaluation runner modes when cloud keys are omitted.
