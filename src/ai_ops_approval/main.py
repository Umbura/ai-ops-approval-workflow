from __future__ import annotations

from functools import lru_cache
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status

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
    version="0.1.0",
    description="Backend for AI-assisted request triage with human approval and audit logging.",
)


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


@app.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.env,
        "llm_mode": settings.llm_mode,
        "llm_model": settings.openai_model if settings.llm_mode == "openai" else "mock",
        "llm_fallback_enabled": str(settings.llm_fallback_enabled).lower(),
    }


@app.post("/requests", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(payload: RequestCreate, store: StoreDep, provider: TriageProviderDep) -> dict:
    request_payload = payload.model_dump()
    try:
        triage = provider.triage(request_payload)
    except TriageProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return store.create_request(request_payload, triage)


@app.get("/requests", response_model=list[RequestResponse])
def list_requests(
    store: StoreDep,
    status_filter: Annotated[RequestStatus | None, Query(alias="status")] = None,
) -> list[dict]:
    return store.list_requests(status_filter.value if status_filter else None)


@app.get("/requests/{request_id}", response_model=RequestResponse)
def get_request(request_id: str, store: StoreDep) -> dict:
    try:
        return store.get_request(request_id)
    except RequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Request not found") from exc


@app.post("/requests/{request_id}/decision", response_model=DecisionResponse)
def record_decision(request_id: str, payload: DecisionCreate, store: StoreDep) -> dict:
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
def metrics(store: StoreDep) -> dict:
    return store.metrics()


@app.get("/audit", response_model=list[AuditEventResponse])
def audit_events(
    store: StoreDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict]:
    return store.audit_events(limit=limit)


def run() -> None:
    uvicorn.run("ai_ops_approval.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
