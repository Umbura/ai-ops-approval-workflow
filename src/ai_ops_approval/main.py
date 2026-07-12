from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from ai_ops_approval import __version__
from ai_ops_approval.domain import Decision, RequestStatus
from ai_ops_approval.llm import TriageProvider, TriageProviderError, build_triage_provider
from ai_ops_approval.schemas import (
    AuditEventResponse,
    DecisionCreate,
    DecisionResponse,
    MetricsResponse,
    RequestCreate,
    RequestResponse,
)
from ai_ops_approval.settings import Settings, get_settings
from ai_ops_approval.storage import RequestNotFoundError, RequestStore

app = FastAPI(
    title="AI Ops Approval Workflow",
    version=__version__,
    description="Backend for AI-assisted request triage with human approval and audit logging.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@lru_cache
def get_store() -> RequestStore:
    settings = get_settings()
    return RequestStore(settings.db_path)


@lru_cache
def get_triage_provider() -> TriageProvider:
    return build_triage_provider(get_settings())


StoreDep = Annotated[RequestStore, Depends(get_store)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
TriageProviderDep = Annotated[TriageProvider, Depends(get_triage_provider)]


def require_api_key(
    settings: SettingsDep,
    provided_api_key: Annotated[str | None, Depends(api_key_header)],
) -> None:
    expected = settings.api_key.get_secret_value() if settings.api_key else ""
    if not expected:
        return
    if not provided_api_key or not secrets.compare_digest(provided_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


AuthDep = Annotated[None, Depends(require_api_key)]


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config", include_in_schema=False)
def public_config(settings: SettingsDep) -> dict[str, str | bool]:
    return {
        "app_name": settings.app_name,
        "auth_required": bool(settings.api_key and settings.api_key.get_secret_value()),
        "environment": settings.env,
    }


@app.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.env,
        "llm_mode": settings.llm_mode,
        "llm_model": settings.openai_model if settings.llm_mode == "openai" else "mock",
        "llm_fallback_enabled": str(settings.llm_fallback_enabled).lower(),
        "auth_required": str(bool(settings.api_key and settings.api_key.get_secret_value())).lower(),
    }


@app.post("/requests", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,
    store: StoreDep,
    provider: TriageProviderDep,
    _auth: AuthDep,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=128),
    ] = None,
) -> dict:
    if idempotency_key:
        existing = store.get_request_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

    request_payload = payload.model_dump()
    try:
        triage = provider.triage(request_payload)
    except TriageProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Triage service unavailable",
        ) from exc
    return store.create_request(request_payload, triage, idempotency_key=idempotency_key)


@app.get("/requests", response_model=list[RequestResponse])
def list_requests(
    store: StoreDep,
    _auth: AuthDep,
    status_filter: Annotated[RequestStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict]:
    return store.list_requests(status_filter.value if status_filter else None, limit=limit)


@app.get("/requests/{request_id}", response_model=RequestResponse)
def get_request(request_id: str, store: StoreDep, _auth: AuthDep) -> dict:
    try:
        return store.get_request(request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Request not found") from exc


@app.post("/requests/{request_id}/decision", response_model=DecisionResponse)
def record_decision(
    request_id: str,
    payload: DecisionCreate,
    store: StoreDep,
    _auth: AuthDep,
) -> dict:
    try:
        return store.record_decision(
            request_id=request_id,
            decision=Decision(payload.decision),
            reviewer=payload.reviewer,
            notes=payload.notes,
        )
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Request not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/metrics", response_model=MetricsResponse)
def metrics(store: StoreDep, _auth: AuthDep) -> dict:
    return store.metrics()


@app.get("/audit", response_model=list[AuditEventResponse])
def audit_events(
    store: StoreDep,
    _auth: AuthDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    request_id: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> list[dict]:
    return store.audit_events(limit=limit, request_id=request_id)


app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


def run() -> None:
    uvicorn.run("ai_ops_approval.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
