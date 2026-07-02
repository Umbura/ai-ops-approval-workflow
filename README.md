# AI Ops Approval Workflow

[![CI](https://github.com/Umbura/ai-ops-approval-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Umbura/ai-ops-approval-workflow/actions/workflows/ci.yml)

Backend-first portfolio project for AI-assisted operational triage with human approval and audit logging.

This repository is intentionally small enough to publish quickly, but structured like a real service:

- FastAPI backend.
- SQLite persistence for the MVP.
- Deterministic mock AI classifier, so the demo works without paid API keys.
- Optional OpenAI Responses API triage with Structured Outputs.
- Human approval endpoint before any final action.
- Audit trail for every important transition.
- Importable n8n workflow export.

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

## LLM Mode

The default mode is deterministic and cost-free:

```env
AI_OPS_LLM_MODE=mock
```

To use OpenAI for real triage, configure:

```env
AI_OPS_LLM_MODE=openai
OPENAI_API_KEY=your_key_here
AI_OPS_OPENAI_MODEL=gpt-5.4-mini
AI_OPS_LLM_FALLBACK_ENABLED=true
```

The backend uses the Responses API with a JSON Schema output format. If the OpenAI call fails and fallback is enabled, the request is classified by the local deterministic triage engine and marked with `llm_fallback_used`.

Do not commit `.env`; it is ignored by Git.

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

## n8n Workflow

Import:

```text
workflows/ai_ops_approval_n8n.json
```

The workflow has two webhook paths:

- `POST /webhook/ai-ops-request`
- `POST /webhook/ai-ops-decision`

Set this in n8n:

```text
AI_OPS_API_BASE_URL=http://127.0.0.1:8000
```

If n8n runs in Docker, use:

```text
AI_OPS_API_BASE_URL=http://host.docker.internal:8000
```

## Technical References

- OpenAI Responses API: https://developers.openai.com/api/reference/resources/responses/methods/create/
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs

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
- Optional real LLM triage.
- Importable n8n webhook workflow.
