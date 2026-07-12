import json

import httpx
import pytest

from ai_ops_approval.domain import Priority, RequestCategory
from ai_ops_approval.llm import (
    FallbackTriageProvider,
    MockTriageProvider,
    OpenAIResponsesTriageProvider,
    TriageProviderError,
    build_triage_provider,
    coerce_triage_result,
    extract_response_text,
    parse_openai_triage_response,
)
from ai_ops_approval.settings import Settings


def test_openai_provider_parses_structured_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["store"] is False
        assert body["text"]["format"]["type"] == "json_schema"
        assert request.headers["Authorization"] == "Bearer test-key"
        model_input = json.loads(body["input"][1]["content"][0]["text"])
        assert model_input["title"] == "Suspicious chargeback"
        assert "requester" not in model_input
        assert "metadata" not in model_input

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


def test_openai_provider_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AI_OPS_OPENAI_API_KEY", raising=False)
    provider = OpenAIResponsesTriageProvider(
        Settings(_env_file=None, llm_mode="openai", openai_api_key=None)
    )

    with pytest.raises(TriageProviderError, match="OPENAI_API_KEY"):
        provider.triage({"title": "Request", "description": "Request description"})


def test_provider_factory_honors_mode_and_fallback_configuration() -> None:
    mock_provider = build_triage_provider(Settings(_env_file=None, llm_mode="mock"))
    openai_provider = build_triage_provider(
        Settings(
            _env_file=None,
            llm_mode="openai",
            openai_api_key="test-key",
            llm_fallback_enabled=False,
        )
    )

    assert isinstance(mock_provider, MockTriageProvider)
    assert isinstance(openai_provider, OpenAIResponsesTriageProvider)


@pytest.mark.parametrize(
    "response_json",
    [
        {"output": "invalid"},
        {"output": []},
        {"output": [None]},
        {"output": [{"content": "invalid"}]},
    ],
)
def test_extract_response_text_rejects_invalid_structures(
    response_json: dict,
) -> None:
    with pytest.raises(TriageProviderError):
        extract_response_text(response_json)


def test_parser_rejects_non_object_output() -> None:
    with pytest.raises(TriageProviderError, match="structured object"):
        parse_openai_triage_response(
            {"output_text": "[]"},
            {"title": "Request", "description": "Request description"},
        )


def test_coercion_rejects_boolean_confidence() -> None:
    with pytest.raises(TriageProviderError, match="triage schema"):
        coerce_triage_result(
            {
                "category": "general",
                "priority": "low",
                "confidence": True,
                "requires_human_review": False,
                "suggested_action": "Route to the operations queue.",
                "rationale": "No explicit risk signal was detected.",
                "risk_flags": [],
            },
            {"title": "Request", "description": "Request description"},
        )


@pytest.mark.parametrize(
    "risk_flags",
    [
        ["valid_flag"] * 11,
        ["  "],
        ["x" * 81],
    ],
)
def test_coercion_rejects_invalid_risk_flags(risk_flags: list[str]) -> None:
    with pytest.raises(TriageProviderError, match="risk flags"):
        coerce_triage_result(
            {
                "category": "general",
                "priority": "low",
                "confidence": 0.8,
                "requires_human_review": False,
                "suggested_action": "Route to the operations queue.",
                "rationale": "No explicit risk signal was detected.",
                "risk_flags": risk_flags,
            },
            {"title": "Request", "description": "Request description"},
        )


def test_coercion_normalizes_and_deduplicates_risk_flags() -> None:
    result = coerce_triage_result(
        {
            "category": "general",
            "priority": "low",
            "confidence": 0.8,
            "requires_human_review": False,
            "suggested_action": "Route to the operations queue.",
            "rationale": "No explicit risk signal was detected.",
            "risk_flags": [" review_required ", "review_required"],
        },
        {"title": "Request", "description": "Request description"},
    )

    assert result.risk_flags == ("review_required",)
