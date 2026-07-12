import asyncio

import httpx

from ai_ops_approval.domain import triage_request
from ai_ops_approval.llm import TriageProviderError
from ai_ops_approval.main import app, get_store, get_triage_provider
from ai_ops_approval.settings import get_settings
from ai_ops_approval.storage import RequestStore

REQUEST_PAYLOAD = {
    "title": "Suspicious account activity",
    "description": "A VIP customer reported an urgent chargeback after a suspicious login.",
    "requester": "security@example.com",
    "customer_tier": "vip",
    "amount_at_risk": 1800,
}


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def triage(self, payload: dict):
        self.calls += 1
        return triage_request(payload)


class FailingProvider:
    def triage(self, _payload: dict):
        raise TriageProviderError("sensitive upstream detail")


def test_dashboard_is_public_and_api_key_protects_operations(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AI_OPS_API_KEY", "test-api-key")
    store = RequestStore(str(tmp_path / "auth.db"))
    app.dependency_overrides[get_store] = lambda: store
    get_settings.cache_clear()

    async def run_flow() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            dashboard = await client.get("/")
            assert dashboard.status_code == 200
            assert "AI Ops Console" in dashboard.text

            config = await client.get("/config")
            assert config.status_code == 200
            assert config.json()["auth_required"] is True

            missing = await client.get("/requests")
            assert missing.status_code == 401

            incorrect = await client.get("/requests", headers={"X-API-Key": "wrong"})
            assert incorrect.status_code == 401

            authorized = await client.get(
                "/requests",
                headers={"X-API-Key": "test-api-key"},
            )
            assert authorized.status_code == 200

    try:
        asyncio.run(run_flow())
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_idempotency_key_reuses_request_without_second_triage(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AI_OPS_API_KEY", raising=False)
    store = RequestStore(str(tmp_path / "idempotency.db"))
    provider = CountingProvider()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_triage_provider] = lambda: provider
    get_settings.cache_clear()

    async def run_flow() -> None:
        transport = httpx.ASGITransport(app=app)
        headers = {"Idempotency-Key": "same-operation"}
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/requests", headers=headers, json=REQUEST_PAYLOAD)
            second = await client.post("/requests", headers=headers, json=REQUEST_PAYLOAD)

            assert first.status_code == 201
            assert second.status_code == 201
            assert first.json()["id"] == second.json()["id"]
            assert provider.calls == 1
            assert len(store.list_requests()) == 1

    try:
        asyncio.run(run_flow())
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_provider_failure_does_not_expose_internal_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AI_OPS_API_KEY", raising=False)
    store = RequestStore(str(tmp_path / "provider-error.db"))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_triage_provider] = lambda: FailingProvider()
    get_settings.cache_clear()

    async def run_flow() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/requests", json=REQUEST_PAYLOAD)
            assert response.status_code == 503
            assert response.json() == {"detail": "Triage service unavailable"}
            assert "sensitive" not in response.text

    try:
        asyncio.run(run_flow())
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_metadata_size_limit_is_enforced(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AI_OPS_API_KEY", raising=False)
    store = RequestStore(str(tmp_path / "metadata.db"))
    provider = CountingProvider()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_triage_provider] = lambda: provider
    get_settings.cache_clear()

    async def run_flow() -> None:
        transport = httpx.ASGITransport(app=app)
        payload = {**REQUEST_PAYLOAD, "metadata": {"content": "x" * 17_000}}
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/requests", json=payload)
            assert response.status_code == 422
            assert provider.calls == 0

    try:
        asyncio.run(run_flow())
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
