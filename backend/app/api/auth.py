"""Authentication API: login, logout, register, me."""
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.conversation import AuditEvent
from app.models.user import User, UserRole

router = APIRouter()
logger = structlog.get_logger(__name__)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


@router.post("/login", response_model=TokenResponse, summary="Login")
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return a JWT access token."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning("Login failed", email=data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token(data={"sub": user.id, "role": user.role.value})

    # Audit log — do not log the password or token
    audit = AuditEvent(
        id=str(uuid.uuid4()),
        user_id=user.id,
        event_type="login",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    logger.info("User logged in", user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
    )


@router.post("/logout", summary="Logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    JWT logout — client should discard the token.
    Server-side token blacklisting can be added via Redis for production.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse, summary="Current user")
async def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=201, summary="Register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Self-registration for new users (employee role by default)."""
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=UserRole.EMPLOYEE,
    )
    db.add(user)
    await db.commit()

    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    logger.info("New user registered", user_id=user.id)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
    )
