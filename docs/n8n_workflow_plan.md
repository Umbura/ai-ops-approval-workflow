# n8n Workflow

Canonical export:

```text
workflows/ai_ops_approval_n8n.json
```

Validated runtime: n8n `2.29.10`.

## Request Path

1. `POST /webhook/ai-ops-request` receives a request.
2. `Validate Request Webhook` compares `X-Webhook-Secret` with `AI_OPS_WEBHOOK_SECRET`.
3. `Authorize Request Webhook` returns HTTP `401` when validation fails.
4. An idempotency key is retained from the request or generated from the n8n execution.
5. `Create Backend Request` calls `POST /requests` with `X-API-Key` and `Idempotency-Key`.
6. `Prepare Request Response` returns triage and decision instructions.

## Decision Path

1. `POST /webhook/ai-ops-decision` receives `request_id`, `decision`, `reviewer`, and `notes`.
2. `Validate Decision Webhook` checks the webhook secret.
3. `Authorize Decision Webhook` returns HTTP `401` when validation fails.
4. `Record Backend Decision` calls `POST /requests/{request_id}/decision` with `X-API-Key`.
5. The backend response is returned to the caller.

## Required Environment Variables

```text
AI_OPS_API_BASE_URL=http://api:8000
AI_OPS_API_KEY=<backend-api-key>
AI_OPS_WEBHOOK_SECRET=<webhook-secret>
WEBHOOK_URL=http://localhost:5678/
```

## Docker Compose

`docker/n8n-entrypoint.sh` imports and publishes the workflow when the n8n container starts. Changes to the canonical JSON replace the stored workflow on restart.

## Export Rule

Credentials and fixed secrets must not be stored in the workflow JSON. Runtime values are supplied through environment variables.
