"""
Unit tests for AWS Bedrock LLM Provider (backend/app/services/llm.py).
Tests use mocked boto3 client — no AWS account, cloud resources, or API keys needed.
Verifies that:
1. boto3 is invoked using only the default credential chain (no access keys).
2. Claude payload formatting and text extraction work properly.
3. Amazon Titan payload formatting and outputText extraction work properly.
4. Response streaming handles chunks correctly.
5. get_llm_provider() respects LLM_PROVIDER=bedrock.
"""
import io
import json
import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.llm import BedrockLLMProvider, get_llm_provider


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 bedrock-runtime client."""
    with patch("boto3.client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        yield mock_client, mock_client_factory


@pytest.mark.asyncio
async def test_bedrock_provider_uses_default_credential_chain(mock_boto3_client):
    """Verify that Bedrock provider initializes with no hardcoded access keys."""
    mock_client, mock_client_factory = mock_boto3_client
    
    provider = BedrockLLMProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0", region_name="us-east-1")
    
    # Assert boto3.client called with service name and region only, NO credentials kwargs
    mock_client_factory.assert_called_once_with("bedrock-runtime", region_name="us-east-1")
    call_kwargs = mock_client_factory.call_args[1]
    assert "aws_access_key_id" not in call_kwargs
    assert "aws_secret_access_key" not in call_kwargs
    assert "aws_session_token" not in call_kwargs


@pytest.mark.asyncio
async def test_bedrock_claude_generate(mock_boto3_client):
    """Verify that generate properly parses Anthropic Claude Messages API format."""
    mock_client, _ = mock_boto3_client
    
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({
        "content": [{"text": "Based on the policy, standard travel reimbursement is $75."}]
    }).encode("utf-8")
    mock_client.invoke_model.return_value = {"body": mock_body}

    provider = BedrockLLMProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    result = await provider.generate("What is the meal allowance?")

    assert "reimbursement is $75" in result
    mock_client.invoke_model.assert_called_once()
    call_kwargs = mock_client.invoke_model.call_args[1]
    assert call_kwargs["modelId"] == "anthropic.claude-3-haiku-20240307-v1:0"
    sent_payload = json.loads(call_kwargs["body"])
    assert sent_payload["anthropic_version"] == "bedrock-2023-05-31"
    assert sent_payload["messages"][0]["content"] == "What is the meal allowance?"


@pytest.mark.asyncio
async def test_bedrock_titan_generate(mock_boto3_client):
    """Verify that generate properly formats and parses Amazon Titan payload."""
    mock_client, _ = mock_boto3_client
    
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({
        "results": [{"outputText": "Titan response: Policy requirement verified."}]
    }).encode("utf-8")
    mock_client.invoke_model.return_value = {"body": mock_body}

    provider = BedrockLLMProvider(model_id="amazon.titan-text-express-v1")
    result = await provider.generate("Verify policy.")

    assert "Policy requirement verified" in result
    call_kwargs = mock_client.invoke_model.call_args[1]
    assert call_kwargs["modelId"] == "amazon.titan-text-express-v1"
    sent_payload = json.loads(call_kwargs["body"])
    assert sent_payload["inputText"] == "Verify policy."


@pytest.mark.asyncio
async def test_bedrock_generate_stream(mock_boto3_client):
    """Verify streaming response parses event stream chunks."""
    mock_client, _ = mock_boto3_client
    
    chunk_1 = {"chunk": {"bytes": json.dumps({"delta": {"text": "Hello "}}).encode("utf-8")}}
    chunk_2 = {"chunk": {"bytes": json.dumps({"delta": {"text": "World"}}).encode("utf-8")}}
    mock_client.invoke_model_with_response_stream.return_value = {
        "body": [chunk_1, chunk_2]
    }

    provider = BedrockLLMProvider(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    chunks = []
    async for chunk in provider.generate_stream("Hello"):
        chunks.append(chunk)

    assert "".join(chunks) == "Hello World"


def test_get_llm_provider_selects_bedrock_when_configured():
    """Verify factory returns BedrockLLMProvider when LLM_PROVIDER=bedrock in production mode."""
    with patch.object(settings, "APP_ENV", "production"):
        with patch.object(settings, "LLM_PROVIDER", "bedrock"):
            with patch("boto3.client") as mock_client:
                provider = get_llm_provider()
                assert isinstance(provider, BedrockLLMProvider)
