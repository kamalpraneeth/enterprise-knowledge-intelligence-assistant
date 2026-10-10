"""
Tests for authentication endpoints.
Covers: login, logout, register, me, role authorization.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """New user can register with valid credentials."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "employee"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Duplicate registration returns 409."""
    await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "full_name": "Dup", "password": "SecurePass123!"},
    )
    response = await client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "full_name": "Dup2", "password": "SecurePass123!"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Short password is rejected."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "full_name": "Weak", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user, admin_token: str):
    """Admin can log in with correct credentials."""
    assert admin_token is not None
    assert len(admin_token) > 10


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    """Wrong password returns 401."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "WrongPass!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Non-existent email returns 401."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPass123!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, admin_user, admin_token: str):
    """Authenticated user can access /me endpoint."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_upload_documents(client: AsyncClient, admin_token: str):
    """Admin has access to document upload endpoint (returns 422 for missing file, not 403)."""
    response = await client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # 422 = no file provided, which is expected — access was granted
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_employee_cannot_upload_documents(client: AsyncClient, employee_token: str):
    """Employee cannot upload documents (403 Forbidden)."""
    import io
    response = await client.post(
        "/api/documents/upload",
        headers={"Authorization": f"Bearer {employee_token}"},
        files={"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, admin_token: str):
    """Logout endpoint returns success message."""
    response = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_token(client: AsyncClient):
    """Invalid JWT token returns 401."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer this-is-not-a-valid-jwt"},
    )
    assert response.status_code == 401
