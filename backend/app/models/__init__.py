"""Models package — import all models here so Alembic auto-detects them."""
from app.models.user import User, UserRole
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.conversation import (
    Conversation, Message, Citation, ToolExecution,
    UserFeedback, AuditEvent, MessageRole, ToolStatus
)
from app.models.evaluation import (
    EvaluationDataset, EvaluationQuestion, EvaluationRun,
    EvaluationResult, EvaluationRunStatus
)

__all__ = [
    "User", "UserRole",
    "Document", "DocumentChunk", "DocumentStatus",
    "Conversation", "Message", "Citation", "ToolExecution",
    "UserFeedback", "AuditEvent", "MessageRole", "ToolStatus",
    "EvaluationDataset", "EvaluationQuestion", "EvaluationRun",
    "EvaluationResult", "EvaluationRunStatus",
]
