"""
User management API — admin-only user administration.
"""
import uuid
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole

router = APIRouter()
logger = structlog.get_logger(__name__)


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="employee")


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/", summary="List users (admin)")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count.scalar() or 0

    result = await db.execute(
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()
    return {
        "items": [UserOut(id=u.id, email=u.email, full_name=u.full_name, role=u.role.value, is_active=u.is_active, created_at=u.created_at) for u in users],
        "total": total,
    }


@router.post("/", response_model=UserOut, status_code=201, summary="Create user (admin)")
async def create_user(
    data: CreateUserRequest,
    _: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    try:
        role = UserRole(data.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid role: {data.role}")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    await db.commit()
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value, is_active=user.is_active, created_at=user.created_at)


@router.patch("/{user_id}", response_model=UserOut, summary="Update user (admin)")
async def update_user(
    user_id: str,
    data: UpdateUserRequest,
    _: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        try:
            user.role = UserRole(data.role)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid role: {data.role}")
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value, is_active=user.is_active, created_at=user.created_at)
