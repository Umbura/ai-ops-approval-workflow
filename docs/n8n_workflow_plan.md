# n8n Workflow Plan

This backend is ready to be connected to n8n. The workflow should be created manually first, then exported as JSON into `workflows/`.

## Nodes

1. Webhook
   - Method: POST
   - Path: `ai-ops-request`
   - Response mode: using Respond to Webhook node

2. HTTP Request
   - POST `http://host.docker.internal:8000/requests`
   - Body: incoming webhook JSON

3. IF / Switch
   - Check `triage.requires_human_review`

4. Approval notification
   - Email, Slack, Telegram, or mock HTTP node
   - Include request id, summary, suggested action and risk flags

5. Wait
   - Resume by form or webhook
   - Capture approve/reject/request_changes

6. HTTP Request
   - POST `/requests/{id}/decision`

7. Respond to Webhook
   - Return request id, status and suggested action

## Export Rule

Do not export credentials. Use placeholders only.

