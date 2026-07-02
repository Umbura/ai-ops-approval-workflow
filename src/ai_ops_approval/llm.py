from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Protocol

import httpx

from ai_ops_approval.domain import (
    Priority,
    RequestCategory,
    TriageResult,
    triage_request,
)
from ai_ops_approval.settings import Settings


class TriageProviderError(RuntimeError):
    pass


class TriageProvider(Protocol):
    def triage(self, payload: dict[str, Any]) -> TriageResult:
        pass


class MockTriageProvider:
    def triage(self, payload: dict[str, Any]) -> TriageResult:
        return triage_request(payload)


TRIAGE_JSON_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "name": "ai_ops_triage",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "category": {
                "type": "string",
                "enum": [category.value for category in RequestCategory],
            },
            "priority": {
                "type": "string",
                "enum": [priority.value for priority in Priority],
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "requires_human_review": {
                "type": "boolean",
            },
            "suggested_action": {
                "type": "string",
                "minLength": 10,
                "maxLength": 500,
            },
            "rationale": {
                "type": "string",
                "minLength": 10,
                "maxLength": 500,
            },
            "risk_flags": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 2,
                    "maxLength": 80,
                },
                "maxItems": 10,
            },
        },
        "required": [
            "category",
            "priority",
            "confidence",
            "requires_human_review",
            "suggested_action",
            "rationale",
            "risk_flags",
        ],
    },
}


SYSTEM_PROMPT = """You are an operations triage assistant.
Classify incoming operational requests for a backend workflow.
Return only the requested structured object.
Be conservative with risk: fraud, access, high-value, destructive, urgent, or enterprise/VIP cases must require human review.
Do not approve or execute final actions. Suggest the next safe operational step."""


class OpenAIResponsesTriageProvider:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
        self.model = settings.openai_model
        self.base_url = settings.openai_base_url.rstrip("/")
        self.timeout_seconds = settings.openai_timeout_seconds
        self.max_output_tokens = settings.openai_max_output_tokens
        self.transport = transport

    def triage(self, payload: dict[str, Any]) -> TriageResult:
        if not self.api_key:
            raise TriageProviderError("OPENAI_API_KEY is required when AI_OPS_LLM_MODE=openai")

        request_body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            "text": {"format": TRIAGE_JSON_FORMAT},
            "store": False,
            "max_output_tokens": self.max_output_tokens,
        }

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/responses",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TriageProviderError(f"OpenAI request failed: {exc}") from exc

        return parse_openai_triage_response(response.json(), payload)


class FallbackTriageProvider:
    def __init__(self, primary: TriageProvider, fallback: TriageProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def triage(self, payload: dict[str, Any]) -> TriageResult:
        try:
            return self.primary.triage(payload)
        except TriageProviderError:
            result = self.fallback.triage(payload)
            return replace(result, risk_flags=(*result.risk_flags, "llm_fallback_used"))


def build_triage_provider(settings: Settings) -> TriageProvider:
    if settings.llm_mode.lower() == "openai":
        openai_provider = OpenAIResponsesTriageProvider(settings)
        if settings.llm_fallback_enabled:
            return FallbackTriageProvider(openai_provider, MockTriageProvider())
        return openai_provider
    return MockTriageProvider()


def parse_openai_triage_response(response_json: dict[str, Any], payload: dict[str, Any]) -> TriageResult:
    raw_text = extract_response_text(response_json)
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise TriageProviderError("OpenAI response did not contain valid JSON") from exc
    return coerce_triage_result(data, payload)


def extract_response_text(response_json: dict[str, Any]) -> str:
    if isinstance(response_json.get("output_text"), str):
        return response_json["output_text"]

    for output_item in response_json.get("output", []):
        for content_item in output_item.get("content", []):
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise TriageProviderError("OpenAI response did not include output text")


def coerce_triage_result(data: dict[str, Any], payload: dict[str, Any]) -> TriageResult:
    try:
        category = RequestCategory(str(data["category"]))
        priority = Priority(str(data["priority"]))
    except (KeyError, ValueError) as exc:
        raise TriageProviderError("OpenAI response used an invalid category or priority") from exc

    confidence = round(max(0.0, min(float(data["confidence"]), 1.0)), 2)
    risk_flags = tuple(str(flag) for flag in data.get("risk_flags", [])[:10])
    requires_human_review = bool(data["requires_human_review"])

    if must_force_human_review(payload, priority, risk_flags):
        requires_human_review = True

    return TriageResult(
        category=category,
        priority=priority,
        confidence=confidence,
        requires_human_review=requires_human_review,
        suggested_action=str(data["suggested_action"]),
        rationale=str(data["rationale"]),
        risk_flags=risk_flags,
    )


def must_force_human_review(
    payload: dict[str, Any],
    priority: Priority,
    risk_flags: tuple[str, ...],
) -> bool:
    amount_at_risk = float(payload.get("amount_at_risk") or 0)
    customer_tier = str(payload.get("customer_tier", "")).lower()
    title = str(payload.get("title", "")).lower()
    description = str(payload.get("description", "")).lower()
    text = f"{title} {description}"
    risk_text = " ".join(risk_flags).lower()

    return (
        priority in {Priority.HIGH, Priority.CRITICAL}
        or amount_at_risk >= 1000
        or customer_tier in {"enterprise", "vip", "strategic"}
        or "fraud" in text
        or "fraude" in text
        or "chargeback" in text
        or "delete" in text
        or "cancel" in text
        or "destructive" in risk_text
    )
