"""
Tests for tool validation and security.
Covers argument validation, allowlist, SQL injection prevention.
"""
import pytest
from pydantic import ValidationError

from app.tools.tools import (
    SearchKBInput,
    GetDocumentMetadataInput,
    LookupPolicyRecordInput,
    CreateSupportRequestInput,
    TOOL_REGISTRY,
)


def test_tool_registry_contains_expected_tools():
    """All expected tools are registered."""
    assert "search_knowledge_base" in TOOL_REGISTRY
    assert "get_document_metadata" in TOOL_REGISTRY
    assert "lookup_policy_record" in TOOL_REGISTRY
    assert "create_support_request" in TOOL_REGISTRY


def test_search_kb_validates_empty_query():
    """Empty query is rejected by schema validation."""
    with pytest.raises(ValidationError):
        SearchKBInput(query="")


def test_search_kb_validates_max_length():
    """Query longer than 1000 chars is rejected."""
    with pytest.raises(ValidationError):
        SearchKBInput(query="x" * 1001)


def test_search_kb_top_k_bounds():
    """top_k must be between 1 and 20."""
    with pytest.raises(ValidationError):
        SearchKBInput(query="test", top_k=0)
    with pytest.raises(ValidationError):
        SearchKBInput(query="test", top_k=21)


def test_lookup_policy_record_rejects_sql_injection():
    """Policy ID with SQL injection characters is rejected by regex."""
    with pytest.raises(ValidationError):
        LookupPolicyRecordInput(policy_id="1; DROP TABLE documents; --")


def test_lookup_policy_record_rejects_path_traversal():
    """Path traversal attempt is rejected."""
    with pytest.raises(ValidationError):
        LookupPolicyRecordInput(policy_id="../../../etc/passwd")


def test_lookup_policy_record_valid_id():
    """Alphanumeric policy IDs are accepted."""
    args = LookupPolicyRecordInput(policy_id="POLICY-001")
    assert args.policy_id == "POLICY-001"


def test_create_support_request_requires_confirmation():
    """Support request without confirmation raises ValidationError."""
    with pytest.raises(ValidationError):
        CreateSupportRequestInput(
            title="My Issue",
            description="This is a detailed description of the issue.",
            confirmed=None,  # type: ignore
        )


def test_create_support_request_short_title():
    """Title shorter than 5 chars is rejected."""
    with pytest.raises(ValidationError):
        CreateSupportRequestInput(title="Hi", description="A" * 10, confirmed=True)


def test_create_support_request_short_description():
    """Description shorter than 10 chars is rejected."""
    with pytest.raises(ValidationError):
        CreateSupportRequestInput(title="Valid Title", description="short", confirmed=True)


def test_document_metadata_input_valid():
    """Valid UUID-like document ID passes validation."""
    args = GetDocumentMetadataInput(document_id="abc123-def-456")
    assert args.document_id == "abc123-def-456"


def test_max_tool_calls_constant_defined():
    """MAX_TOOL_CALLS_PER_REQUEST is a reasonable positive integer."""
    from app.tools.tools import MAX_TOOL_CALLS_PER_REQUEST
    assert MAX_TOOL_CALLS_PER_REQUEST > 0
    assert MAX_TOOL_CALLS_PER_REQUEST <= 20  # Sanity upper bound
