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
- GitHub Actions CI is configured to run dependency sync, lint, tests, and compilation on every push and pull request to `main`.
- Optional OpenAI Responses API triage is implemented with Structured Outputs and tested with a mocked HTTP transport.
- n8n workflow export is available at `workflows/ai_ops_approval_n8n.json`.

## Smoke Test Output

```text
compileall: ok
fraud_risk high True 0.92 high_amount_at_risk,sensitive_customer,urgency_signal,fraud_or_security_signal
needs_review fraud_risk True
approved 1 2
uv sync: ok
6 passed
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

- External LLM calls are optional.
- No Docker or n8n runtime is required to run the backend tests.
- The default AI behavior is deterministic and cost-free; OpenAI mode can be enabled through environment variables.

## Next Backend Milestone

Run one real OpenAI smoke test and import the n8n workflow in a local n8n instance.
