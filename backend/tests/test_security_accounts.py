"""
Tests for security, RBAC audit logging, demo account seeding, and rate limiting (HIGH-01 through HIGH-04).
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User, UserRole
from app.models.conversation import AuditEvent
from app.db.seed import seed_demo_accounts
from app.core.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_demo_accounts_match_readme(db: AsyncSession):
    """Verify demo accounts match README credentials and roles after seeding."""
    await seed_demo_accounts(db)

    # 1. Admin account
    res = await db.execute(select(User).where(User.email == "admin@ekia.local"))
    admin = res.scalar_one_or_none()
    assert admin is not None
    assert admin.role == UserRole.ADMIN

    # 2. Knowledge Manager account
    res = await db.execute(select(User).where(User.email == "km@ekia.local"))
    km = res.scalar_one_or_none()
    assert km is not None
    assert km.role == UserRole.KNOWLEDGE_MANAGER

    # 3. Employee account
    res = await db.execute(select(User).where(User.email == "employee@ekia.local"))
    emp = res.scalar_one_or_none()
    assert emp is not None
    assert emp.role == UserRole.EMPLOYEE


@pytest.mark.asyncio
async def test_admin_company_role_bug_fixed(db: AsyncSession):
    """
    Verify that if admin@company.com was incorrectly configured with EMPLOYEE role,
    the seeder repairs the role to ADMIN.
    """
    # Create or update admin@company.com with buggy EMPLOYEE role
    res = await db.execute(select(User).where(User.email == "admin@company.com"))
    existing = res.scalar_one_or_none()
    if existing:
        existing.role = UserRole.EMPLOYEE
    else:
        buggy_user = User(
            id=str(uuid.uuid4()),
            email="admin@company.com",
            full_name="Buggy Admin",
            hashed_password=hash_password("Pass123!"),
            role=UserRole.EMPLOYEE,
            is_active=True,
        )
        db.add(buggy_user)
    await db.commit()

    # Re-run seeder
    await seed_demo_accounts(db)

    # Verify role was fixed to ADMIN
    res = await db.execute(select(User).where(User.email == "admin@company.com"))
    fixed_user = res.scalar_one_or_none()
    assert fixed_user is not None
    assert fixed_user.role == UserRole.ADMIN, f"Expected role ADMIN, got {fixed_user.role}"


@pytest.mark.asyncio
async def test_audit_log_tool_execution(client: AsyncClient, db: AsyncSession, admin_user: User):
    """Verify tool execution logs an AuditEvent with sanitized parameters and no tokens."""
    token = create_access_token({"sub": admin_user.id, "role": admin_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/tools/execute",
        headers=headers,
        json={
            "tool_name": "lookup_policy_record",
            "arguments": {"policy_id": "POL-101", "api_token_secret": "my-secret-token"},
        },
    )
    assert response.status_code == 200

    # Verify AuditEvent in DB
    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.event_type == "tool_execution")
        .order_by(AuditEvent.created_at.desc())
    )
    audit = res.scalar_one_or_none()
    assert audit is not None
    assert audit.user_id == admin_user.id
    assert audit.resource_id == "lookup_policy_record"
    # Ensure sensitive token argument was redacted to ***
    assert audit.details["arguments"].get("api_token_secret") == "***"


@pytest.mark.asyncio
async def test_audit_log_denied_rbac_attempt(client: AsyncClient, db: AsyncSession, employee_user: User):
    """Verify denied RBAC attempt logs an AuditEvent and returns 403."""
    token = create_access_token({"sub": employee_user.id, "role": employee_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to upload a document (requires Admin or Knowledge Manager)
    response = await client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert response.status_code == 403

    # Verify AuditEvent for denied RBAC in DB
    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.event_type == "rbac_denied")
        .order_by(AuditEvent.created_at.desc())
    )
    audit = res.scalar_one_or_none()
    assert audit is not None
    assert audit.user_id == employee_user.id
    assert audit.details["attempted_role"] == "employee"
    assert "admin" in audit.details["required_roles"]


@pytest.mark.asyncio
async def test_audit_log_document_query(client: AsyncClient, db: AsyncSession, employee_user: User):
    """Verify document search logs an AuditEvent with search metadata and no raw tokens."""
    token = create_access_token({"sub": employee_user.id, "role": employee_user.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/api/retrieval/search",
        headers=headers,
        json={"query": "What is the annual leave policy?", "top_k": 3},
    )
    assert response.status_code == 200

    # Verify AuditEvent in DB
    res = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.event_type == "document_query")
        .order_by(AuditEvent.created_at.desc())
    )
    audit = res.scalar_one_or_none()
    assert audit is not None
    assert audit.user_id == employee_user.id
    assert audit.details["top_k"] == 3
    assert "query_length" in audit.details


@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    """
    Verify slowapi rate limiter rejects requests with HTTP 429 when threshold is exceeded.
    """
    from app.core.rate_limit import limiter
    from fastapi import FastAPI, Request
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler

    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Route with very strict rate limit (2/minute)
    @test_app.get("/rate-limited-test")
    @limiter.limit("2/minute")
    async def limited_endpoint(request: Request):
        return {"status": "ok"}

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        r1 = await test_client.get("/rate-limited-test")
        r2 = await test_client.get("/rate-limited-test")
        r3 = await test_client.get("/rate-limited-test")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
        assert "429" in str(r3.status_code)
