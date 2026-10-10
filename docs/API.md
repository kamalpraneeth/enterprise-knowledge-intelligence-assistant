# EKIA REST API Documentation

The Enterprise Knowledge Intelligence Assistant exposes a typed FastAPI REST interface with interactive OpenAPI documentation available at `/docs`.

Base URL: `http://localhost:8000` (or configured reverse proxy endpoint)

All authenticated endpoints require an `Authorization: Bearer <token>` header.

---

## 1. Authentication Endpoints

### `POST /api/auth/register`
Creates a new corporate user account.
- **Request Body:**
```json
{
  "email": "analyst@company.com",
  "full_name": "Decision Scientist",
  "password": "SecurePassword123!"
}
```
- **Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1Ni...",
  "token_type": "bearer",
  "user_id": "usr-8a9d...",
  "email": "analyst@company.com",
  "full_name": "Decision Scientist",
  "role": "employee"
}
```

### `POST /api/auth/login`
Authenticates user credentials and returns JWT bearer token.
- **Request Body:**
```json
{
  "email": "admin@ekia.local",
  "password": "AdminPass123!"
}
```

### `GET /api/auth/me`
Retrieves current authenticated user's profile and RBAC role.

---

## 2. Conversational RAG Endpoints

### `POST /api/chat`
Submits a query to the conversational RAG engine.
- **Request Body:**
```json
{
  "question": "What is the daily per diem allowance for meals on domestic travel?",
  "conversation_id": "conv-123e4567-e89b-12d3-a456-426614174000"
}
```
- **Response (200 OK):**
```json
{
  "conversation_id": "conv-123e4567-e89b-12d3-a456-426614174000",
  "message": {
    "id": "msg-8f92...",
    "role": "assistant",
    "content": "According to the ACME Travel Reimbursement Policy [1], the maximum daily per diem meal allowance cap for domestic business travel is $85.00. Individual meals exceeding $25.00 require itemized receipts.",
    "citations": [
      {
        "id": "cit-1",
        "rank": 1,
        "document_name": "Travel_Reimbursement_Policy.txt",
        "page_number": 2,
        "passage": "Employees traveling on approved corporate business are eligible for meal reimbursements up to the daily per diem cap of $85.00 for domestic travel.",
        "similarity_score": 0.912
      }
    ],
    "has_sufficient_evidence": true,
    "retrieval_latency_ms": 142,
    "generation_latency_ms": 698,
    "total_latency_ms": 840,
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### `POST /api/feedback`
Submits user feedback (thumbs up / thumbs down) for an assistant response.
- **Request Body:**
```json
{
  "message_id": "msg-8f92...",
  "rating": 1,
  "comment": "Accurate per diem numbers."
}
```

---

## 3. Vector Retrieval Endpoints

### `POST /api/retrieval/search`
Direct vector similarity search endpoint without LLM synthesis.
- **Request Body:**
```json
{
  "query": "password rotation length policy",
  "top_k": 3
}
```
- **Response (200 OK):**
```json
{
  "results": [
    {
      "chunk_id": "chk-it-001",
      "document_id": "doc-3",
      "document_name": "IT_Security_Policy.txt",
      "page_number": 1,
      "content": "Passwords must be at least 14 characters in length and include uppercase, lowercase, numbers, and symbols.",
      "similarity_score": 0.942
    }
  ],
  "total": 3,
  "latency_ms": 38
}
```

---

## 4. Document Ingestion Endpoints

- `GET /api/documents`: List uploaded documents with pagination and status filters.
- `POST /api/documents/upload`: Multipart file upload (PDF, TXT, DOCX).
- `POST /api/documents/{id}/reindex`: Recomputes text chunks and vector embeddings.
- `DELETE /api/documents/{id}`: Cascading deletion of document and vector embeddings.

---

## 5. Agentic Tools Endpoints

### `GET /api/tools/available`
Returns list of allowlisted tools and parameter schemas.

### `POST /api/tools/execute`
Executes an allowlisted tool with validated parameters.
- **Request Body:**
```json
{
  "tool_name": "calculate_pto_balance",
  "arguments": {
    "months_of_service": 12,
    "employee_tier": "full_time"
  }
}
```
- **Response (200 OK):**
```json
{
  "tool_name": "calculate_pto_balance",
  "status": "success",
  "duration_ms": 14,
  "output": {
    "months_of_service": 12,
    "accrued_days": 20.0,
    "current_balance": 20.0
  }
}
```
