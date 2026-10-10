"""
Database seeder for demo accounts and legacy account role corrections.
Ensures pre-configured credentials match documentation and repairs permissions.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.user import User, UserRole
from app.core.security import hash_password

logger = structlog.get_logger(__name__)

DEMO_ACCOUNTS = [
    {
        "email": "admin@ekia.local",
        "full_name": "System Administrator",
        "password": "AdminPass123!",
        "role": UserRole.ADMIN,
    },
    {
        "email": "km@ekia.local",
        "full_name": "Knowledge Manager",
        "password": "KMPass123!",
        "role": UserRole.KNOWLEDGE_MANAGER,
    },
    {
        "email": "employee@ekia.local",
        "full_name": "Standard Employee",
        "password": "EmployeePass123!",
        "role": UserRole.EMPLOYEE,
    },
]


async def seed_demo_accounts(session: AsyncSession) -> None:
    """
    Seed initial README demo accounts and repair any incorrect legacy roles.
    """
    for item in DEMO_ACCOUNTS:
        stmt = select(User).where(User.email == item["email"])
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email=item["email"],
                full_name=item["full_name"],
                hashed_password=hash_password(item["password"]),
                role=item["role"],
                is_active=True,
            )
            session.add(user)
            logger.info("Seeded demo account", email=item["email"], role=item["role"].value)
        else:
            if user.role != item["role"]:
                user.role = item["role"]
                logger.info("Updated demo account role", email=item["email"], role=item["role"].value)

    # Fix HIGH-01: Correct legacy admin@company.com role bug if present
    stmt_comp = select(User).where(User.email == "admin@company.com")
    res_comp = await session.execute(stmt_comp)
    user_comp = res_comp.scalar_one_or_none()
    if user_comp:
        if user_comp.role != UserRole.ADMIN:
            user_comp.role = UserRole.ADMIN
            logger.info("Fixed admin@company.com role bug -> set to ADMIN")
    else:
        # Also seed admin@company.com as an admin so legacy configurations work smoothly
        user_comp = User(
            email="admin@company.com",
            full_name="Company Administrator",
            hashed_password=hash_password("AdminPass123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user_comp)
        logger.info("Seeded legacy admin@company.com with ADMIN role")

    await session.commit()
