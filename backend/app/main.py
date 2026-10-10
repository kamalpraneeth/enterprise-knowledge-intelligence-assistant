"""
EKIA Backend - Enterprise Knowledge Intelligence Assistant
FastAPI application entry point.
"""
import logging
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.api import auth, documents, chat, retrieval, evaluations, tools, health, users

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("EKIA starting up", environment=settings.APP_ENV)
    await init_db()
    yield
    logger.info("EKIA shutting down")


app = FastAPI(
    title="EKIA - Enterprise Knowledge Intelligence Assistant",
    description=(
        "A production-grade RAG system for enterprise knowledge management. "
        "Demonstrates Generative AI, vector search, agentic tool calling, "
        "and secure document retrieval."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a unique request ID to every request for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Return safe error messages without leaking internal details."""
    logger.error(
        "Unhandled exception",
        request_id=getattr(request.state, "request_id", "unknown"),
        path=request.url.path,
        exc_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# --- Routers ---
app.include_router(health.router, tags=["System"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api", tags=["Assistant"])
app.include_router(retrieval.router, prefix="/api/retrieval", tags=["Retrieval"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["Evaluation"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])
