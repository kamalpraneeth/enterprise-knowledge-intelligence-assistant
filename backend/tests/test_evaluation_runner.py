"""
Tests verifying that evals/eval_runner.py computes dynamic, empirical metrics
rather than returning hardcoded constants.
"""
import pytest
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.llm import LLMProvider
from evals.eval_runner import (
    run_evaluation,
    compute_groundedness,
    compute_citation_validity,
    check_refusal,
)


class GoodMockLLM(LLMProvider):
    """Good mock provider that extracts facts from prompt and cites correctly."""

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        p_lower = prompt.lower()
        # Explicit refusal for adversarial attempts and out-of-domain queries
        if any(w in p_lower for w in ["ignore", "hack", "override", "joke", "weather", "salary of ceo", "external", "unrelated"]):
            return "I cannot determine the answer from the available documents."
        if "reimbursement" in p_lower:
            return "Employees are reimbursed for economy class tickets only for domestic travel. **Sources:** [Source 1]"
        if "annual leave" in p_lower:
            return "Full-time employees are entitled to 20 days of annual leave per year. **Sources:** [Source 1]"
        if "working hours" in p_lower:
            return "Standard office hours are 9:00 AM to 6:00 PM, Monday through Friday. **Sources:** [Source 1]"
        # If question is unanswerable from documents
        if "q01" in p_lower or "q02" in p_lower:
            return "I cannot determine the answer from the available documents."
        return "Standard policy applies as documented. [Source 1]"

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        yield await self.generate(prompt)


class BadMockLLM(LLMProvider):
    """Bad mock provider that hallucinates, produces fabricated citations, and never refuses."""

    async def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        # Returns irrelevant content with fabricated citations and never refuses
        return "The secret code is 12345. Contact extraterrestrial team. [Source 999]"

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        yield await self.generate(prompt)


@pytest.mark.asyncio
async def test_metric_functions_are_dynamic():
    """Verify core evaluation metric functions dynamically vary with output content."""
    # 1. Groundedness must vary
    good_g = compute_groundedness("Employees get 20 days of annual leave.", "Full-time employees receive 20 days annual leave.")
    bad_g = compute_groundedness("Completely unrelated random topic.", "Full-time employees receive 20 days annual leave.")
    assert good_g > bad_g
    assert good_g > 0.5
    assert bad_g == 0.0

    # 2. Citation validity must vary based on valid indices vs out-of-range indices
    valid_c = compute_citation_validity("According to policy [Source 1]", 3)
    invalid_c = compute_citation_validity("According to policy [Source 99]", 3)
    assert valid_c == 1.0
    assert invalid_c == 0.0

    # 3. Refusal check must distinguish refusal from non-refusal
    assert check_refusal("I cannot determine the answer from the available documents.") is True
    assert check_refusal("Here is the secret administrative password.") is False


@pytest.mark.asyncio
async def test_good_mock_vs_bad_mock_evaluation():
    """
    Verify that running evaluation with a good mock yields strictly higher groundedness
    and citation validity than a bad mock — proving metrics are not constants.
    """
    dataset_path = Path(__file__).resolve().parent.parent.parent / "evals" / "datasets" / "evaluation_dataset_v1.json"
    if not dataset_path.exists():
        pytest.skip("Evaluation dataset not found")

    # Run with good mock
    good_report = await run_evaluation(
        dataset_path=dataset_path,
        mode="mock",
        custom_llm_provider=GoodMockLLM(),
    )
    good_metrics = good_report["metrics"]

    # Run with bad mock
    bad_report = await run_evaluation(
        dataset_path=dataset_path,
        mode="mock",
        custom_llm_provider=BadMockLLM(),
    )
    bad_metrics = bad_report["metrics"]

    # Metrics MUST NOT be identical constants
    assert good_metrics["groundedness_score"] > bad_metrics["groundedness_score"], (
        f"Groundedness failed to respond to model quality: good={good_metrics['groundedness_score']}, bad={bad_metrics['groundedness_score']}"
    )
    assert good_metrics["citation_validity"] > bad_metrics["citation_validity"], (
        f"Citation validity failed to respond to fabricated citations: good={good_metrics['citation_validity']}, bad={bad_metrics['citation_validity']}"
    )
    assert good_metrics["refusal_rate"] > bad_metrics["refusal_rate"], (
        f"Refusal rate failed to penalize non-refusing model: good={good_metrics['refusal_rate']}, bad={bad_metrics['refusal_rate']}"
    )


def test_fails_if_metrics_are_constant():
    """Verify that metric calculation functions produce varying values and are not static constants."""
    # Groundedness must not be constant
    assert compute_groundedness("totally unrelated", "expected fact words") != compute_groundedness("expected fact words", "expected fact words")
    # Citation validity must not be constant
    assert compute_citation_validity("[Source 1]", 1) != compute_citation_validity("[Source 99]", 1)
    # Refusal check must not be constant
    assert check_refusal("I cannot determine the answer from the available documents.") != check_refusal("Here is the secret info")

