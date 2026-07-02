# n8n Workflow

This backend includes an importable n8n workflow at:

```text
workflows/ai_ops_approval_n8n.json
```

The export stores no credentials.

## Nodes

1. Submit Request Webhook
   - Method: POST
   - Path: `ai-ops-request`
   - Response mode: using Respond to Webhook node

2. Create Backend Request
   - POST `{{$env.AI_OPS_API_BASE_URL}}/requests`
   - Fallback base URL: `http://host.docker.internal:8000`
   - Body: incoming webhook JSON

3. Prepare Request Response
   - Returns request id, status, category, priority, suggested action, and decision webhook instructions

4. Decision Webhook
   - Method: POST
   - Path: `ai-ops-decision`
   - Body: `request_id`, `decision`, `reviewer`, `notes`

5. Record Backend Decision
   - POST `{{$env.AI_OPS_API_BASE_URL}}/requests/{request_id}/decision`

## Local Import

1. Start the backend:

```powershell
uv run uvicorn ai_ops_approval.main:app --reload
```

2. In n8n, set the environment variable:

```text
AI_OPS_API_BASE_URL=http://host.docker.internal:8000
```

For n8n running directly on the host machine, use:

```text
AI_OPS_API_BASE_URL=http://127.0.0.1:8000
```

3. Import `workflows/ai_ops_approval_n8n.json`.

4. Test the submit webhook with a payload like `examples/high_priority_request.json`.

## Export Rule

Do not export credentials. Use placeholders only.
