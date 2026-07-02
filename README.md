# AI Ops Approval Workflow

Backend-first portfolio project for AI-assisted operational triage with human approval and audit logging.

This repository is intentionally small enough to publish quickly, but structured like a real service:

- FastAPI backend.
- SQLite persistence for the MVP.
- Deterministic mock AI classifier, so the demo works without paid API keys.
- Human approval endpoint before any final action.
- Audit trail for every important transition.
- n8n integration plan documented for the next step.

## Why This Project Exists

The target jobs ask for practical AI automation: Python, APIs, n8n, SQL, LLMs, workflow orchestration, human review, and logs. This project demonstrates those skills without depending on a fragile chatbot demo.

## Reuse And License Position

I studied n8n, LangGraph, CrewAI, and public n8n workflow examples. This project does not copy their source code.

What is reused:

- Project structure ideas: `pyproject.toml`, typed modules, tests, docs.
- Architecture patterns: webhook input, backend decisioning, human approval, audit logging.
- Workflow concepts: n8n as visual orchestrator and FastAPI as testable business backend.

What is not reused:

- No copied source files from n8n, LangGraph, CrewAI, or n8n-workflows.
- No workflow JSON copied from public collections.
- No vendor credentials or templates.

## Quick Start

```powershell
uv sync
uv run uvicorn ai_ops_approval.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

If you do not want to install dependencies yet, you can still inspect the code and run pure-Python checks over the domain layer.

## Example Request

```bash
curl -X POST http://127.0.0.1:8000/requests ^
  -H "Content-Type: application/json" ^
  -d @examples/high_priority_request.json
```

## API Shape

- `GET /health`
- `POST /requests`
- `GET /requests`
- `GET /requests/{request_id}`
- `POST /requests/{request_id}/decision`
- `GET /metrics`
- `GET /audit`

## MVP Result

The backend already produces:

- Request classification.
- Priority.
- Confidence score.
- Suggested action.
- Human review requirement.
- Persisted request state.
- Audit events.
- Metrics.

## Next Step

Build the n8n workflow:

Webhook -> HTTP Request to backend -> IF/Switch -> Send approval -> Wait -> Decision endpoint -> Respond to Webhook.

