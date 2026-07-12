from ai_ops_approval.domain import Priority, RequestCategory, triage_request


def test_fraud_request_requires_human_review() -> None:
    result = triage_request(
        {
            "title": "Suspicious login and possible fraud",
            "description": "Enterprise customer reported urgent suspicious account access.",
            "customer_tier": "enterprise",
            "amount_at_risk": 2500,
        }
    )

    assert result.category == RequestCategory.FRAUD_RISK
    assert result.priority in {Priority.HIGH, Priority.CRITICAL}
    assert result.requires_human_review is True
    assert "fraud_or_security_signal" in result.risk_flags
    assert result.confidence >= 0.8


def test_general_request_stays_low_priority() -> None:
    result = triage_request(
        {
            "title": "Question about a report",
            "description": "Can you clarify how the weekly report is organized?",
        }
    )

    assert result.category == RequestCategory.GENERAL
    assert result.priority == Priority.LOW
    assert result.requires_human_review is True
