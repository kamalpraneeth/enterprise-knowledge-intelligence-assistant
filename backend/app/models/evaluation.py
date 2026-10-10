"""
Evaluation dataset, run, and result models.
"""
import uuid
import enum
from datetime import datetime

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EvaluationRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    runs = relationship("EvaluationRun", back_populates="dataset")


class EvaluationQuestion(Base):
    __tablename__ = "evaluation_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str] = mapped_column(Text, nullable=True)
    expected_document_ids: Mapped[list] = mapped_column(JSON, nullable=True)
    question_type: Mapped[str] = mapped_column(String(50), nullable=True)  # answerable, unanswerable, adversarial
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_datasets.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[EvaluationRunStatus] = mapped_column(SAEnum(EvaluationRunStatus, name="eval_run_status"), default=EvaluationRunStatus.PENDING)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    completed_questions: Mapped[int] = mapped_column(Integer, default=0)
    avg_retrieval_precision: Mapped[float] = mapped_column(Float, nullable=True)
    avg_answer_correctness: Mapped[float] = mapped_column(Float, nullable=True)
    avg_citation_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    insufficient_evidence_rate: Mapped[float] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=True)
    model_used: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset = relationship("EvaluationDataset", back_populates="runs")
    results = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_questions.id", ondelete="SET NULL"), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=True)
    retrieval_precision: Mapped[float] = mapped_column(Float, nullable=True)
    answer_correctness: Mapped[float] = mapped_column(Float, nullable=True)
    citation_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    has_sufficient_evidence: Mapped[bool] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run = relationship("EvaluationRun", back_populates="results")
