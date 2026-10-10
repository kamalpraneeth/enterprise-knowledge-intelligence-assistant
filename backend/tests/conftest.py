"""
pytest configuration and shared fixtures.
Uses in-memory SQLite for unit tests with fake LLM/embedding providers.
Integration tests use a real PostgreSQL instance (configurable via TEST_DATABASE_URL).
"""
import asyncio
import os
import pytest
import pytest_asyncio

# Force test environment before any app imports
os.environ["APP_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-do-not-use-in-prod"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GOOGLE_API_KEY"] = ""

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole


from sqlalchemy.pool import StaticPool

# Use SQLite for unit tests (no PostgreSQL required)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function")
async def db():
    """Create fresh tables for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession):
    """Test HTTP client with DB override."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """Create an admin user for tests."""
    user = User(
        id="test-admin-id",
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def employee_user(db: AsyncSession) -> User:
    """Create an employee user for tests."""
    user = User(
        id="test-employee-id",
        email="employee@test.com",
        full_name="Test Employee",
        hashed_password=hash_password("EmployeePass123!"),
        role=UserRole.EMPLOYEE,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """Get JWT token for admin user."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def employee_token(client: AsyncClient, employee_user: User) -> str:
    """Get JWT token for employee user."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "employee@test.com", "password": "EmployeePass123!"},
    )
    return response.json()["access_token"]
