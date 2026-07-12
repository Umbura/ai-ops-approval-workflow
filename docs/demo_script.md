# Demonstration Script

## 1. Start The Environment

```powershell
$env:AI_OPS_LLM_MODE = "mock"
docker compose up --build -d
```

Open the dashboard:

```text
http://127.0.0.1:8000
```

Use the local development API key:

```text
local-development-key
```

## 2. Submit A High-Risk Request

```powershell
$body = Get-Content -Raw examples\high_priority_request.json
$headers = @{
  "X-Webhook-Secret" = "local-webhook-secret"
  "X-Idempotency-Key" = "portfolio-demo-001"
}
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5678/webhook/ai-ops-request `
  -Headers $headers `
  -ContentType application/json `
  -Body $body
```

Expected result:

```text
category: fraud_risk
priority: high
status: needs_review
requires_human_review: true
```

## 3. Review The Request

In the dashboard:

1. Select the new request.
2. Inspect the risk flags, rationale, confidence, and suggested action.
3. Select `Record decision`.
4. Record an approval, rejection, or change request.

The queue, metrics, status, and audit log update after the decision.

## 4. Show The Workflow

Open:

```text
http://127.0.0.1:5678
```

The workflow contains separate request and decision paths, fail-closed webhook authorization, sanitized payload forwarding, idempotency propagation, explicit decision validation, backend API authentication, and shaped responses.

## 5. Explain The Engineering Decisions

- FastAPI owns testable business rules.
- n8n owns orchestration.
- model output is constrained by Structured Outputs.
- deterministic rules can override unsafe model output.
- SQLite provides a reproducible local state store.
- API and webhook secrets protect the two trust boundaries.
- payload-bound idempotency prevents duplicates and rejects key reuse with different content.
- every request and decision generates an audit event.

Use mock mode for the routine demonstration. The real OpenAI integration has already been validated and recorded in `RESULTS.md`.
