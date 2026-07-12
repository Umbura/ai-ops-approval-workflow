import pytest

from ai_ops_approval.domain import Decision, triage_request
from ai_ops_approval.storage import IdempotencyConflictError, RequestStore


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
        reviewer="operations-reviewer",
        notes="Approved for controlled follow-up.",
    )

    assert decision["status"] == "approved"
    assert store.metrics()["approved"] == 1
    assert store.metrics()["review_required"] == 0
    assert len(store.audit_events()) == 2
    assert len(store.audit_events(request_id=created["id"])) == 2


def test_legacy_idempotency_fingerprint_is_backfilled(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    payload = {
        "title": "Legacy request",
        "description": "Stored before payload fingerprints were introduced.",
        "requester": "operations@example.com",
        "channel": "webhook",
        "customer_tier": "standard",
        "amount_at_risk": 0.0,
        "metadata": {"source": "migration-test"},
    }
    store = RequestStore(str(db_path))
    store.create_request(payload, triage_request(payload), idempotency_key="legacy-key")
    with store.connect() as conn:
        conn.execute(
            "UPDATE requests SET request_fingerprint = NULL WHERE idempotency_key = ?",
            ("legacy-key",),
        )

    migrated_store = RequestStore(str(db_path))
    existing = migrated_store.get_request_by_idempotency_key("legacy-key", payload)
    assert existing is not None

    with pytest.raises(IdempotencyConflictError):
        migrated_store.get_request_by_idempotency_key(
            "legacy-key",
            {**payload, "title": "Conflicting request"},
        )
