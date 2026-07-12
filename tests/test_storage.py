from ai_ops_approval.domain import Decision, triage_request
from ai_ops_approval.storage import RequestStore


def test_request_lifecycle(tmp_path) -> None:
    store = RequestStore(str(tmp_path / "test.db"))
    payload = {
        "title": "Payment chargeback risk",
        "description": "Customer says payment is suspicious and asks for urgent review.",
        "requester": "ops@example.com",
        "channel": "test",
        "customer_tier": "vip",
        "amount_at_risk": 700,
        "metadata": {"source": "pytest"},
    }
    created = store.create_request(payload, triage_request(payload))

    assert created["id"]
    assert created["triage"]["requires_human_review"] is True

    decision = store.record_decision(
        created["id"],
        Decision.APPROVE,
        reviewer="Iago",
        notes="Approved for controlled follow-up.",
    )

    assert decision["status"] == "approved"
    assert store.metrics()["approved"] == 1
    assert store.metrics()["review_required"] == 0
    assert len(store.audit_events()) == 2
    assert len(store.audit_events(request_id=created["id"])) == 2
