# MVP Results

Verification date: 2026-07-02

This repository currently ships a backend-only MVP for an AI-assisted operations approval workflow.

## What Was Verified

- Python modules compile successfully with `python -m compileall -q src tests`.
- The triage engine identifies a fraud/security request as high priority and sends it to human review.
- The SQLite request store can create a request, record an approval decision, update status, and persist audit events.
- Project dependencies install successfully with `uv sync --dev`.
- Unit tests pass with `uv run pytest -q`.
- Lint passes with `uv run ruff check .`.
- The FastAPI app imports successfully.
- API integration is tested with direct ASGI transport, without requiring a running server.
- The local API starts successfully with Uvicorn.
- `POST /requests` creates and classifies a high-risk request.

## Smoke Test Output

```text
compileall: ok
fraud_risk high True 0.92 high_amount_at_risk,sensitive_customer,urgency_signal,fraud_or_security_signal
needs_review fraud_risk True
approved 1 2
uv sync: ok
4 passed in 0.71s
All checks passed!
AI Ops Approval Workflow
server: ok http://127.0.0.1:8000
health: ok mock
status: needs_review
category: fraud_risk
priority: high
review: True
```

## Current Scope

- No external LLM calls are required.
- No Docker or n8n runtime is required for this version.
- The AI behavior is intentionally mocked with deterministic rules so the backend can be demonstrated, tested, and evolved without API cost.

## Next Backend Milestone

Replace the deterministic triage strategy with a provider interface that can support OpenAI, local models, or a hybrid rules-plus-LLM approach while keeping the current approval and audit flow unchanged.
