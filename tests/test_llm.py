import json

import httpx

from ai_ops_approval.domain import Priority, RequestCategory
from ai_ops_approval.llm import (
    FallbackTriageProvider,
    MockTriageProvider,
    OpenAIResponsesTriageProvider,
)
from ai_ops_approval.settings import Settings


def test_openai_provider_parses_structured_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["store"] is False
        assert body["text"]["format"]["type"] == "json_schema"
        assert request.headers["Authorization"] == "Bearer test-key"

        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "category": "fraud_risk",
                                        "priority": "medium",
                                        "confidence": 0.88,
                                        "requires_human_review": False,
                                        "suggested_action": "Open a fraud-risk review queue item.",
                                        "rationale": "The request mentions chargeback and suspicious payment.",
                                        "risk_flags": ["fraud_or_security_signal"],
                                    }
                                ),
                            }
                        ],
                    }
                ]
            },
        )

    provider = OpenAIResponsesTriageProvider(
        Settings(
            llm_mode="openai",
            openai_api_key="test-key",
            openai_model="test-model",
        ),
        transport=httpx.MockTransport(handler),
    )

    result = provider.triage(
        {
            "title": "Suspicious chargeback",
            "description": "VIP customer reported a suspicious payment.",
            "customer_tier": "vip",
            "amount_at_risk": 1500,
        }
    )

    assert result.category == RequestCategory.FRAUD_RISK
    assert result.priority == Priority.MEDIUM
    assert result.requires_human_review is True
    assert result.confidence == 0.88


def test_fallback_provider_uses_mock_when_openai_fails() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "temporary failure"}})

    primary = OpenAIResponsesTriageProvider(
        Settings(
            llm_mode="openai",
            openai_api_key="test-key",
            openai_model="test-model",
        ),
        transport=httpx.MockTransport(handler),
    )
    provider = FallbackTriageProvider(primary, MockTriageProvider())

    result = provider.triage(
        {
            "title": "Suspicious login",
            "description": "Enterprise customer is blocked after suspicious login.",
            "customer_tier": "enterprise",
        }
    )

    assert result.category == RequestCategory.FRAUD_RISK
    assert result.requires_human_review is True
    assert "llm_fallback_used" in result.risk_flags


def test_fallback_provider_uses_mock_for_malformed_model_output() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "not-json"})

    primary = OpenAIResponsesTriageProvider(
        Settings(
            llm_mode="openai",
            openai_api_key="test-key",
            openai_model="test-model",
        ),
        transport=httpx.MockTransport(handler),
    )
    provider = FallbackTriageProvider(primary, MockTriageProvider())

    result = provider.triage(
        {
            "title": "Suspicious login",
            "description": "Enterprise customer reported a suspicious login.",
            "customer_tier": "enterprise",
        }
    )

    assert result.category == RequestCategory.FRAUD_RISK
    assert result.requires_human_review is True
    assert "llm_fallback_used" in result.risk_flags
