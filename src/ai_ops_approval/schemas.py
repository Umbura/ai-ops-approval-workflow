from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ai_ops_approval.domain import Decision, Priority, RequestCategory, RequestStatus


class RequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    requester: str = Field(default="unknown", max_length=120)
    channel: str = Field(default="webhook", max_length=80)
    customer_tier: str = Field(default="standard", max_length=80)
    amount_at_risk: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TriageResponse(BaseModel):
    category: RequestCategory
    priority: Priority
    confidence: float
    requires_human_review: bool
    suggested_action: str
    rationale: str
    risk_flags: list[str]


class RequestResponse(BaseModel):
    id: str
    status: RequestStatus
    title: str
    description: str
    requester: str
    channel: str
    customer_tier: str
    amount_at_risk: float
    triage: TriageResponse
    created_at: datetime
    updated_at: datetime


class DecisionCreate(BaseModel):
    decision: Decision
    reviewer: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=2000)


class DecisionResponse(BaseModel):
    request_id: str
    status: RequestStatus
    decision: Decision
    reviewer: str
    notes: str
    decided_at: datetime


class MetricsResponse(BaseModel):
    total_requests: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    review_required: int
    approved: int
    rejected: int


class AuditEventResponse(BaseModel):
    id: int
    request_id: str
    event_type: str
    payload: dict[str, Any]
    created_at: datetime

