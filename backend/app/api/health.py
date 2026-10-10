"""Health and readiness endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()


@router.get("/health", summary="Health check")
async def health():
    """Returns 200 if the application is running."""
    return {"status": "healthy", "service": "ekia-backend"}


@router.get("/ready", summary="Readiness check")
async def ready(db: AsyncSession = Depends(get_db)):
    """Returns 200 if the application and database are ready."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    ready = db_status == "ok"
    return {
        "status": "ready" if ready else "not_ready",
        "database": db_status,
    }
