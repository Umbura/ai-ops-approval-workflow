# Demo Script

Use this script to present the MVP in a portfolio review or interview.

## 1. Start The API

```powershell
uv sync
uv run uvicorn ai_ops_approval.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 2. Explain The Problem

Operational teams receive requests that can involve fraud, billing, access, support, or data quality. Some requests can be auto-summarized, but risky actions need human approval and auditability.

## 3. Submit A High-Risk Request

Use `examples/high_priority_request.json` in `POST /requests`.

Expected result:

- Category: `fraud_risk`
- Priority: `high`
- Status: `needs_review`
- Human review: `true`

## 4. Record A Human Decision

Use `POST /requests/{request_id}/decision`.

Example:

```json
{
  "decision": "approve",
  "reviewer": "Iago",
  "notes": "Approved after checking customer context."
}
```

Expected result:

- Status changes to `approved`.
- A decision is stored.
- An audit event is generated.

## 5. Show Metrics And Audit

Open:

```text
GET /metrics
GET /audit
```

Use this to highlight that the project is not just a chatbot. It has persistence, state transitions, risk routing, approval, and observability.
