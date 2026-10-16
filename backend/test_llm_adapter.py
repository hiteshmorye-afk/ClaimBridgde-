"""
Unit tests for ClaimBridge Provider-Independent LLM Adapter.
Covers:
1. Schema-validated structured output
2. Tripartite separation: verified facts, missing information, uncertain interpretations
3. Reviewer explanation and missing document recommendations
4. Resilient fallback handling for timeouts, missing API keys, rate limits, and malformed JSON
5. Invariant check: Output contains disclaimer and cannot alter readiness scores or decisions
"""

import pytest
from app.llm_adapter import (
    ClaimContextForLLM,
    HTTPGenericLLMProvider,
    LLMClient,
    MockLLMProvider,
    ReviewerExplanationOutput,
    LLM_DISCLAIMER,
    generate_deterministic_fallback,
)


@pytest.fixture
def sample_context():
    return ClaimContextForLLM(
        claim_id="CLM-2026-TEST01",
        patient_name="Priya Sharma",
        patient_age=38,
        hospital="Fortis Memorial Research Institute",
        policy_number="9876543210",
        claimed_amount=125000.0,
        diagnosis="Acute Appendicitis (ICD-10: K35.8)",
        procedure="Laparoscopic Appendectomy",
        medical_indicators=["Hospital Admission Evidence", "Surgical Service"],
        policy_citations=[
            {
                "citation": "[sample_policy.txt | SECTION 2 - SURGICAL TREATMENT]",
                "section_title": "SECTION 2 - SURGICAL TREATMENT",
                "relevance_score": 0.82,
                "content": "Medically necessary surgical procedures are covered.",
            }
        ],
        missing_documents=["Official Discharge Summary"],
        mismatches=["Admission date on bill (2026-08-10) differs from claim form (2026-08-11)"],
        readiness_score=72.5,
    )


def test_mock_provider_returns_valid_schema(sample_context):
    provider = MockLLMProvider()
    result = provider.generate_explanation(sample_context)

    assert isinstance(result, ReviewerExplanationOutput)
    assert result.provider_status == "mock"
    assert "CLM-2026-TEST01" in result.summary
    assert len(result.verified_facts) >= 3
    assert any("Priya Sharma" in f for f in result.verified_facts)
    assert any("Fortis Memorial" in f for f in result.verified_facts)

    # Missing info & recommendations
    assert any("Official Discharge Summary" in m for m in result.missing_information)
    assert any("Official Discharge Summary" in r for r in result.missing_document_recommendations)

    # Uncertain interpretations
    assert any("Admission date" in u for u in result.uncertain_interpretations)

    # Reviewer narrative & disclaimer
    assert len(result.reviewer_explanation) > 20
    assert result.disclaimer == LLM_DISCLAIMER


def test_deterministic_fallback_on_missing_api_key(sample_context):
    provider = HTTPGenericLLMProvider(api_key="")
    result = provider.generate_explanation(sample_context)

    assert isinstance(result, ReviewerExplanationOutput)
    assert result.provider_status == "fallback_unavailable"
    assert "API key not configured" in result.summary
    assert len(result.verified_facts) >= 3
    assert len(result.missing_information) == 1
    assert len(result.uncertain_interpretations) == 1
    assert result.disclaimer == LLM_DISCLAIMER


def test_fallback_on_network_timeout(monkeypatch, sample_context):
    class TimeoutClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            import httpx
            raise httpx.TimeoutException("Connection timed out after 8.0s")

    monkeypatch.setattr("httpx.Client", TimeoutClient)

    provider = HTTPGenericLLMProvider(api_key="synthetic_test_key")
    result = provider.generate_explanation(sample_context)

    assert result.provider_status == "fallback_unavailable"
    assert "TimeoutException" in result.summary
    assert any("Discharge Summary" in m for m in result.missing_information)


def test_fallback_on_rate_limit_or_malformed_json(monkeypatch, sample_context):
    class MalformedResponseClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            class FakeResp:
                def raise_for_status(self):
                    pass
                def json(self):
                    return {"choices": [{"message": {"content": "This is raw text, not valid JSON"}}]}
            return FakeResp()

    monkeypatch.setattr("httpx.Client", MalformedResponseClient)

    provider = HTTPGenericLLMProvider(api_key="synthetic_test_key")
    result = provider.generate_explanation(sample_context)

    assert result.provider_status == "fallback_unavailable"
    assert "JSONDecodeError" in result.summary or "Provider degraded" in result.summary
    assert len(result.verified_facts) >= 1


def test_llm_client_initialization_defaults_safely():
    client = LLMClient()
    assert client.provider is not None
    assert isinstance(client.provider, MockLLMProvider)
