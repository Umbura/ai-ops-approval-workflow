import asyncio

import httpx

from ai_ops_approval.llm import MockTriageProvider
from ai_ops_approval.main import app, get_store, get_triage_provider
from ai_ops_approval.storage import RequestStore


def test_api_request_decision_and_metrics(tmp_path) -> None:
    store = RequestStore(str(tmp_path / "api.db"))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_triage_provider] = lambda: MockTriageProvider()

    async def run_flow() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/requests",
                json={
                    "title": "Urgent suspicious payment",
                    "description": "VIP customer reported a suspicious chargeback and blocked login.",
                    "requester": "ops@example.com",
                    "customer_tier": "vip",
                    "amount_at_risk": 1200,
                },
            )
            assert created.status_code == 201
            request_payload = created.json()
            assert request_payload["status"] == "needs_review"
            assert request_payload["triage"]["category"] == "fraud_risk"
            assert request_payload["triage"]["requires_human_review"] is True

            decision = await client.post(
                f"/requests/{request_payload['id']}/decision",
                json={
                    "decision": "approve",
                    "reviewer": "operations-reviewer",
                    "notes": "Approved after checking customer context.",
                },
            )
            assert decision.status_code == 200
            assert decision.json()["status"] == "approved"

            repeated_decision = await client.post(
                f"/requests/{request_payload['id']}/decision",
                json={
                    "decision": "reject",
                    "reviewer": "operations-reviewer",
                    "notes": "A finalized request cannot be changed.",
                },
            )
            assert repeated_decision.status_code == 409

            metrics = await client.get("/metrics")
            assert metrics.status_code == 200
            assert metrics.json()["approved"] == 1

            audit = await client.get("/audit")
            assert audit.status_code == 200
            assert len(audit.json()) == 2

    try:
        asyncio.run(run_flow())
    finally:
        app.dependency_overrides.clear()
