from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class RequestCategory(StrEnum):
    BILLING = "billing"
    FRAUD_RISK = "fraud_risk"
    ACCESS = "access"
    DATA_QUALITY = "data_quality"
    CUSTOMER_SUPPORT = "customer_support"
    GENERAL = "general"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestStatus(StrEnum):
    RECEIVED = "received"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


@dataclass(frozen=True)
class TriageResult:
    category: RequestCategory
    priority: Priority
    confidence: float
    requires_human_review: bool
    suggested_action: str
    rationale: str
    risk_flags: tuple[str, ...]


KEYWORDS: dict[RequestCategory, tuple[str, ...]] = {
    RequestCategory.FRAUD_RISK: (
        "fraud",
        "fraude",
        "chargeback",
        "suspicious",
        "suspeito",
        "risk",
        "risco",
        "login",
        "account takeover",
    ),
    RequestCategory.BILLING: (
        "payment",
        "pagamento",
        "invoice",
        "nota",
        "billing",
        "cobranca",
        "refund",
        "reembolso",
    ),
    RequestCategory.ACCESS: (
        "access",
        "acesso",
        "password",
        "senha",
        "login",
        "permission",
        "permissao",
    ),
    RequestCategory.DATA_QUALITY: (
        "duplicate",
        "duplicado",
        "inconsistent",
        "inconsistente",
        "missing data",
        "dados",
        "schema",
        "csv",
    ),
    RequestCategory.CUSTOMER_SUPPORT: (
        "customer",
        "cliente",
        "support",
        "suporte",
        "complaint",
        "reclamacao",
    ),
}


def _normalize_text(*parts: str | None) -> str:
    return " ".join(part or "" for part in parts).strip().lower()


def infer_category(title: str, description: str) -> RequestCategory:
    text = _normalize_text(title, description)
    scores: dict[RequestCategory, int] = {}
    for category, keywords in KEYWORDS.items():
        scores[category] = sum(1 for keyword in keywords if keyword in text)
    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score == 0:
        return RequestCategory.GENERAL
    return best_category


def triage_request(payload: dict[str, Any]) -> TriageResult:
    title = str(payload.get("title", ""))
    description = str(payload.get("description", ""))
    amount_at_risk = float(payload.get("amount_at_risk") or 0)
    customer_tier = str(payload.get("customer_tier", "standard")).lower()
    text = _normalize_text(title, description)

    category = infer_category(title, description)
    risk_flags: list[str] = []

    if amount_at_risk >= 1000:
        risk_flags.append("high_amount_at_risk")
    elif amount_at_risk >= 300:
        risk_flags.append("medium_amount_at_risk")

    if customer_tier in {"enterprise", "vip", "strategic"}:
        risk_flags.append("sensitive_customer")

    if any(term in text for term in ("urgent", "urgente", "blocked", "bloqueado")):
        risk_flags.append("urgency_signal")

    if category is RequestCategory.FRAUD_RISK:
        risk_flags.append("fraud_or_security_signal")

    if "delete" in text or "cancel" in text or "cancelar" in text:
        risk_flags.append("destructive_action_requested")

    priority = Priority.LOW
    if category in {RequestCategory.FRAUD_RISK, RequestCategory.ACCESS}:
        priority = Priority.HIGH
    elif category in {RequestCategory.BILLING, RequestCategory.DATA_QUALITY}:
        priority = Priority.MEDIUM

    if "high_amount_at_risk" in risk_flags or "fraud_or_security_signal" in risk_flags:
        priority = Priority.CRITICAL if "destructive_action_requested" in risk_flags else Priority.HIGH
    if "sensitive_customer" in risk_flags and priority == Priority.MEDIUM:
        priority = Priority.HIGH
    if "urgency_signal" in risk_flags and priority == Priority.LOW:
        priority = Priority.MEDIUM

    confidence = 0.62
    if category is not RequestCategory.GENERAL:
        confidence += 0.18
    if risk_flags:
        confidence += min(len(risk_flags) * 0.04, 0.12)
    confidence = round(min(confidence, 0.94), 2)

    requires_human_review = (
        priority in {Priority.HIGH, Priority.CRITICAL}
        or confidence < 0.75
        or "destructive_action_requested" in risk_flags
        or "sensitive_customer" in risk_flags
    )

    suggested_action = build_suggested_action(category, priority, requires_human_review)
    rationale = build_rationale(category, priority, confidence, risk_flags)

    return TriageResult(
        category=category,
        priority=priority,
        confidence=confidence,
        requires_human_review=requires_human_review,
        suggested_action=suggested_action,
        rationale=rationale,
        risk_flags=tuple(risk_flags),
    )


def build_suggested_action(
    category: RequestCategory,
    priority: Priority,
    requires_human_review: bool,
) -> str:
    if category is RequestCategory.FRAUD_RISK:
        base = "Open a fraud-risk review, collect recent activity, and notify an analyst."
    elif category is RequestCategory.BILLING:
        base = "Validate payment records and prepare a billing correction proposal."
    elif category is RequestCategory.ACCESS:
        base = "Verify identity signals and prepare an access recovery action."
    elif category is RequestCategory.DATA_QUALITY:
        base = "Run data validation checks and prepare a corrected record list."
    elif category is RequestCategory.CUSTOMER_SUPPORT:
        base = "Draft a support response and attach relevant customer context."
    else:
        base = "Route to operations queue with a concise AI-generated summary."

    if requires_human_review:
        return f"{base} Wait for human approval before executing the final action."
    if priority == Priority.LOW:
        return f"{base} Auto-suggest only; keep a log for review."
    return base


def build_rationale(
    category: RequestCategory,
    priority: Priority,
    confidence: float,
    risk_flags: list[str],
) -> str:
    flag_text = ", ".join(risk_flags) if risk_flags else "no explicit risk flags"
    return (
        f"Classified as {category.value} with {priority.value} priority "
        f"and confidence {confidence:.2f}; flags: {flag_text}."
    )

