"""
Unit tests for Knowledge Base Validation (scripts/validate_kb.py).
Tests:
- Clean demo documents directory passes validation.
- Tiny / low word count / missing header documents fail validation.
- Near-duplicate documents trigger TF-IDF cosine similarity rejection.
- Duplicate normalized identifiers trigger collision rejection.
- Ingestion pipeline blocks and sets DocumentStatus.FAILED on invalid files.
"""
import subprocess
import sys
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from scripts.validate_kb import (
    validate_knowledge_base,
    validate_single_document,
    check_metadata,
)
from app.models.document import Document, DocumentStatus
from app.services.ingestion import ingest_document


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "bad_kb"
DEMO_DOCS_DIR = Path(__file__).resolve().parent.parent / "demo_documents"


def test_clean_demo_documents_pass_validation():
    """Verify that all production demo documents satisfy enterprise KB constraints."""
    assert DEMO_DOCS_DIR.exists(), f"Demo docs directory missing: {DEMO_DOCS_DIR}"
    is_valid, errors = validate_knowledge_base(DEMO_DOCS_DIR)
    assert is_valid is True
    assert len(errors) == 0


def test_tiny_bad_fixture_fails_validation():
    """Verify that tiny file (< 50 bytes, < 10 words) fails validation checks."""
    tiny_path = FIXTURES_DIR / "bad_tiny.txt"
    assert tiny_path.exists()
    content = tiny_path.read_text(encoding="utf-8")
    size_bytes = tiny_path.stat().st_size

    is_valid, errors = validate_single_document(content, tiny_path.name, size_bytes)
    assert is_valid is False
    assert any("too small" in err for err in errors)
    assert any("Word count too low" in err for err in errors)
    assert any("Missing required metadata" in err for err in errors)


def test_near_duplicate_fixtures_trigger_tfidf_rejection(tmp_path):
    """Verify that near-duplicate files with >85% identical content are rejected by TF-IDF."""
    file_a = FIXTURES_DIR / "bad_duplicate_a.txt"
    file_b = FIXTURES_DIR / "bad_duplicate_b.txt"
    assert file_a.exists() and file_b.exists()

    # Copy only the two duplicate files to an isolated temp directory
    test_dir = tmp_path / "dup_kb"
    test_dir.mkdir()
    (test_dir / "policy_v1.txt").write_text(file_a.read_text(encoding="utf-8"))
    (test_dir / "policy_v2.txt").write_text(file_b.read_text(encoding="utf-8"))

    is_valid, errors = validate_knowledge_base(test_dir, similarity_threshold=0.85)
    assert is_valid is False
    assert any("Near-duplicate content detected" in err for err in errors)
    assert any("TF-IDF similarity" in err for err in errors)


def test_duplicate_stem_identifiers_rejected(tmp_path):
    """Verify that identical or normalized stem filenames collide and fail."""
    test_dir = tmp_path / "id_dup_kb"
    test_dir.mkdir()
    sample_content = "# Enterprise Security\n" + ("This is valid text for enterprise guidelines. " * 10)
    (test_dir / "travel_policy.txt").write_text(sample_content)
    (test_dir / "travel-policy.txt").write_text(sample_content)

    is_valid, errors = validate_knowledge_base(test_dir)
    assert is_valid is False
    assert any("Duplicate document identifier" in err for err in errors)


def test_cli_exit_code_on_bad_directory():
    """Verify that running validate_kb.py CLI exits with code 1 on bad fixtures."""
    cmd = [sys.executable, "scripts/validate_kb.py", str(FIXTURES_DIR)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "[FAILED]" in res.stdout
    assert "Ingestion blocked until errors are resolved." in res.stdout


@pytest.mark.asyncio
async def test_ingest_document_blocks_on_validation_failure(tmp_path, monkeypatch):
    """Verify that ingest_document stops and marks document as FAILED when validation fails."""
    # Point uploads directory to temp path
    upload_file = tmp_path / "bad_test.txt"
    upload_file.write_text("tiny bad")
    
    # Mock Document object
    fake_doc = MagicMock()
    fake_doc.id = "doc-123"
    fake_doc.filename = "bad_test.txt"
    fake_doc.file_type = "txt"
    fake_doc.status = DocumentStatus.PENDING

    mock_db = AsyncMock()
    # Mock synchronous result object returned by await db.execute(...)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_doc
    mock_db.execute.return_value = mock_result

    with patch("app.services.ingestion.UPLOAD_DIR", tmp_path):
        await ingest_document("doc-123", mock_db)

    # Document status should have been set to FAILED and rollback occurred
    assert fake_doc.status == DocumentStatus.FAILED
    assert "Knowledge validation" in (fake_doc.error_message or "")
