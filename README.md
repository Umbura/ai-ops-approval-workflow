# AI Ops Approval Workflow

[![CI](https://github.com/Umbura/ai-ops-approval-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Umbura/ai-ops-approval-workflow/actions/workflows/ci.yml)

Backend for AI-assisted operational request triage with human approval and audit logging.

The application receives operational requests, classifies risk, stores request state, requires human review for sensitive cases, and exposes approval and audit endpoints. It supports deterministic local triage by default and optional OpenAI Responses API triage with Structured Outputs.

## Overview

The system separates request intake, triage, persistence, human decisioning, and auditability. The FastAPI backend owns business rules and state transitions. n8n is used as an orchestration layer through an importable workflow export.

The default configuration does not require paid API calls. OpenAI mode can be enabled through environment variables without changing the API contract.

## Implemented Scope

- FastAPI service with request, decision, metrics, audit, and health endpoints.
- SQLite persistence for requests, decisions, and audit events.
- Deterministic mock triage provider.
- Optional OpenAI Responses API triage provider.
- Structured Outputs JSON Schema for LLM responses.
- Fallback from OpenAI triage to deterministic triage.
- Forced human review for high-risk cases.
- Importable n8n workflow JSON.
- Unit and integration tests.
- GitHub Actions CI.

## Execution Flow

```text
request payload
  -> FastAPI POST /requests
  -> triage provider
      -> mock mode: deterministic classifier
      -> openai mode: Responses API + Structured Outputs
      -> fallback: deterministic classifier when enabled
  -> safety boundary
      -> force human review for high-risk cases
  -> SQLite state and audit log
  -> response with category, priority, confidence, and suggested action
  -> optional human decision via POST /requests/{id}/decision
```

## Safety Model

The backend does not execute final operational actions automatically. It classifies the request, suggests the next step, and records a human decision.

Human review is required for:

- high or critical priority;
- fraud or security signals;
- high amount at risk;
- VIP, enterprise, or strategic customers;
- destructive action requests;
- low-confidence deterministic classification.

When OpenAI mode is enabled, the backend still applies deterministic safety checks after parsing the model output.

## API

Start the local API:

```bash
uv sync
uv run uvicorn ai_ops_approval.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Endpoints:

- `GET /health`
- `POST /requests`
- `GET /requests`
- `GET /requests/{request_id}`
- `POST /requests/{request_id}/decision`
- `GET /metrics`
- `GET /audit`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/requests \
  -H "Content-Type: application/json" \
  -d @examples/high_priority_request.json
```

## LLM Configuration

Default no-cost mode:

```env
AI_OPS_LLM_MODE=mock
```

OpenAI mode:

```env
AI_OPS_LLM_MODE=openai
OPENAI_API_KEY=your_key_here
AI_OPS_OPENAI_MODEL=gpt-5.4-mini
AI_OPS_LLM_FALLBACK_ENABLED=true
```

The `.env` file is ignored by Git.

## n8n Workflow

Workflow export:

```text
workflows/ai_ops_approval_n8n.json
```

Webhook paths:

- `POST /webhook/ai-ops-request`
- `POST /webhook/ai-ops-decision`

Backend URL for n8n on the host machine:

```text
AI_OPS_API_BASE_URL=http://127.0.0.1:8000
```

Backend URL for n8n in Docker:

```text
AI_OPS_API_BASE_URL=http://host.docker.internal:8000
```

The workflow export contains no credentials.

## Local Commands

Install dependencies:

```bash
uv sync --dev
```

Run tests and lint:

```bash
uv run pytest -q
uv run ruff check .
```

Compile Python modules:

```bash
uv run python -m compileall -q src tests
```

Validate the n8n workflow JSON:

```bash
python -m json.tool workflows/ai_ops_approval_n8n.json
```

## Validation Results

Latest validation:

| Check | Result |
| --- | ---: |
| Unit and integration tests | 6 passed |
| Lint | passed |
| Python compilation | passed |
| n8n workflow JSON validation | passed |
| GitHub Actions CI | passed |

OpenAI behavior is tested with a mocked HTTP transport. No real OpenAI request is required for the automated test suite.

## Repository Layout

```text
docs/                   architecture, demo, publishing, and workflow notes
examples/               sample request payloads
src/ai_ops_approval/    FastAPI backend, triage providers, storage, schemas
tests/                  unit and integration tests
workflows/              importable n8n workflow export
```

## Roadmap

### Phase 1: Backend MVP

Status: implemented.

- Request intake API.
- Deterministic triage.
- SQLite persistence.
- Human decision endpoint.
- Audit events.
- Metrics endpoint.
- Tests and CI.

### Phase 2: LLM And Workflow Integration

Status: implemented.

- OpenAI Responses API provider.
- Structured Outputs schema.
- Fallback behavior.
- Importable n8n workflow.

### Phase 3: Runtime Validation

- Run one real OpenAI smoke test.
- Import and execute the n8n workflow in a local n8n instance.
- Document request and decision webhook outputs with screenshots.

### Phase 4: Deployment And UI

- Deploy the backend.
- Add a minimal approval dashboard.
- Replace SQLite with PostgreSQL for deployed environments.
- Add API-key authentication for exposed endpoints.

## References

- OpenAI Responses API: https://developers.openai.com/api/reference/resources/responses/methods/create/
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs

License and reuse notes are documented in `docs/reuse_and_license.md`.
