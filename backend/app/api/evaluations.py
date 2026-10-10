"""
Evaluation API: manage datasets, run evaluations, view results.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_knowledge_manager
from app.db.session import get_db
from app.models.evaluation import (
    EvaluationDataset, EvaluationQuestion, EvaluationRun,
    EvaluationResult, EvaluationRunStatus
)
from app.models.user import User
from app.rag.pipeline import run_rag_pipeline

router = APIRouter()
logger = structlog.get_logger(__name__)


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    question_count: int
    created_at: datetime


class RunResponse(BaseModel):
    id: str
    dataset_id: Optional[str]
    status: str
    total_questions: int
    completed_questions: int
    avg_retrieval_precision: Optional[float]
    avg_answer_correctness: Optional[float]
    avg_citation_accuracy: Optional[float]
    insufficient_evidence_rate: Optional[float]
    avg_latency_ms: Optional[float]
    prompt_version: Optional[str]
    model_used: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class RunEvaluationRequest(BaseModel):
    dataset_id: str


@router.post("/run", response_model=RunResponse, summary="Run evaluation")
async def run_evaluation(
    request: RunEvaluationRequest,
    current_user: User = Depends(require_knowledge_manager()),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an evaluation run on a dataset."""
    result = await db.execute(
        select(EvaluationDataset).where(EvaluationDataset.id == request.dataset_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Create run record
    run = EvaluationRun(
        id=str(uuid.uuid4()),
        dataset_id=dataset.id,
        status=EvaluationRunStatus.PENDING,
        total_questions=dataset.question_count,
    )
    db.add(run)
    await db.commit()

    # Run evaluation asynchronously
    asyncio.create_task(_execute_evaluation_run(run.id, dataset.id))

    return RunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status.value,
        total_questions=run.total_questions,
        completed_questions=run.completed_questions,
        avg_retrieval_precision=run.avg_retrieval_precision,
        avg_answer_correctness=run.avg_answer_correctness,
        avg_citation_accuracy=run.avg_citation_accuracy,
        insufficient_evidence_rate=run.insufficient_evidence_rate,
        avg_latency_ms=run.avg_latency_ms,
        prompt_version=run.prompt_version,
        model_used=run.model_used,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


async def _execute_evaluation_run(run_id: str, dataset_id: str):
    """Execute evaluation questions and compute metrics."""
    from app.db.session import AsyncSessionLocal
    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        # Load run
        result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return

        run.status = EvaluationRunStatus.RUNNING
        await db.commit()

        # Load questions
        q_result = await db.execute(
            select(EvaluationQuestion).where(EvaluationQuestion.dataset_id == dataset_id)
        )
        questions = q_result.scalars().all()

        results = []
        try:
            for q in questions:
                try:
                    import time
                    start = time.time()
                    rag_resp = await run_rag_pipeline(
                        question=q.question,
                        db=db,
                        conversation_id=f"eval-{run_id}",
                    )
                    latency_ms = (time.time() - start) * 1000

                    # Simple correctness check
                    correctness = None
                    if q.reference_answer:
                        # Token overlap heuristic (not LLM-graded for unit tests)
                        ref_tokens = set(q.reference_answer.lower().split())
                        ans_tokens = set(rag_resp.answer.lower().split())
                        overlap = len(ref_tokens & ans_tokens)
                        correctness = min(1.0, overlap / max(len(ref_tokens), 1))

                    citation_correct = len(rag_resp.citations) > 0 if rag_resp.has_sufficient_evidence else True

                    res = EvaluationResult(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        question_id=q.id,
                        question_text=q.question,
                        generated_answer=rag_resp.answer,
                        answer_correctness=correctness,
                        citation_correct=citation_correct,
                        has_sufficient_evidence=rag_resp.has_sufficient_evidence,
                        latency_ms=latency_ms,
                    )
                    db.add(res)
                    results.append(res)
                    run.completed_questions += 1
                    await db.commit()
                except Exception as e:
                    logger.error("Eval question failed", question_id=q.id, error=str(e))

            # Compute aggregate metrics
            if results:
                correctness_scores = [r.answer_correctness for r in results if r.answer_correctness is not None]
                latencies = [r.latency_ms for r in results if r.latency_ms is not None]
                sufficient = [r.has_sufficient_evidence for r in results if r.has_sufficient_evidence is not None]
                citations_ok = [r.citation_correct for r in results if r.citation_correct is not None]

                run.avg_answer_correctness = sum(correctness_scores) / len(correctness_scores) if correctness_scores else None
                run.avg_latency_ms = sum(latencies) / len(latencies) if latencies else None
                run.insufficient_evidence_rate = (
                    len([s for s in sufficient if not s]) / len(sufficient)
                    if sufficient else None
                )
                run.avg_citation_accuracy = (
                    sum(1 for c in citations_ok if c) / len(citations_ok)
                    if citations_ok else None
                )
                run.prompt_version = "v1.2"
                run.model_used = settings.LLM_MODEL

            run.status = EvaluationRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Evaluation run completed", run_id=run_id)

        except Exception as e:
            logger.error("Evaluation run failed", run_id=run_id, error=str(e))
            run.status = EvaluationRunStatus.FAILED
            run.error_message = str(e)[:500]
            await db.commit()


@router.get("/", summary="List evaluation runs")
async def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(EvaluationRun)
    count = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count.scalar() or 0
    result = await db.execute(
        query.order_by(EvaluationRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    runs = result.scalars().all()
    return {
        "items": [
            RunResponse(
                id=r.id,
                dataset_id=r.dataset_id,
                status=r.status.value,
                total_questions=r.total_questions,
                completed_questions=r.completed_questions,
                avg_retrieval_precision=r.avg_retrieval_precision,
                avg_answer_correctness=r.avg_answer_correctness,
                avg_citation_accuracy=r.avg_citation_accuracy,
                insufficient_evidence_rate=r.insufficient_evidence_rate,
                avg_latency_ms=r.avg_latency_ms,
                prompt_version=r.prompt_version,
                model_used=r.model_used,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
            for r in runs
        ],
        "total": total,
    }


@router.get("/datasets", summary="List evaluation datasets")
async def list_datasets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EvaluationDataset).order_by(EvaluationDataset.created_at.desc()))
    datasets = result.scalars().all()
    return {"items": [DatasetResponse(id=d.id, name=d.name, description=d.description, question_count=d.question_count, created_at=d.created_at) for d in datasets]}


@router.get("/{run_id}", response_model=RunResponse, summary="Get evaluation run")
async def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return RunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        status=run.status.value,
        total_questions=run.total_questions,
        completed_questions=run.completed_questions,
        avg_retrieval_precision=run.avg_retrieval_precision,
        avg_answer_correctness=run.avg_answer_correctness,
        avg_citation_accuracy=run.avg_citation_accuracy,
        insufficient_evidence_rate=run.insufficient_evidence_rate,
        avg_latency_ms=run.avg_latency_ms,
        prompt_version=run.prompt_version,
        model_used=run.model_used,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )
