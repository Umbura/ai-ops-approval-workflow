from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_ops_approval.domain import Decision, Priority, RequestCategory, RequestStatus


class APIModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class RequestCreate(APIModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    requester: str = Field(default="unknown", min_length=1, max_length=120)
    channel: str = Field(default="webhook", min_length=1, max_length=80)
    customer_tier: str = Field(default="standard", min_length=1, max_length=80)
    amount_at_risk: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 50:
            raise ValueError("metadata cannot contain more than 50 top-level fields")
        try:
            encoded = json.dumps(value, ensure_ascii=True, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON serializable") from exc
        if len(encoded) > 16_384:
            raise ValueError("metadata cannot exceed 16384 bytes")
        return value


class TriageResponse(APIModel):
    category: RequestCategory
    priority: Priority
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool
    suggested_action: str = Field(min_length=10, max_length=500)
    rationale: str = Field(min_length=10, max_length=500)
    risk_flags: list[str] = Field(max_length=10)


class RequestResponse(APIModel):
    id: str
    status: RequestStatus
    title: str
    description: str
    requester: str
    channel: str
    customer_tier: str
    amount_at_risk: float
    metadata: dict[str, Any]
    triage: TriageResponse
    created_at: datetime
    updated_at: datetime


class DecisionCreate(APIModel):
    decision: Decision
    reviewer: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=2000)


class DecisionResponse(APIModel):
    request_id: str
    status: RequestStatus
    decision: Decision
    reviewer: str
    notes: str
    decided_at: datetime


class MetricsResponse(APIModel):
    total_requests: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    review_required: int
    approved: int
    rejected: int


class AuditEventResponse(APIModel):
    id: int
    request_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
