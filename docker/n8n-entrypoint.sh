set -eu

workflow_id="${AI_OPS_N8N_WORKFLOW_ID:-AiOpsApprovalV1}"
workflow_file="${AI_OPS_N8N_WORKFLOW_FILE:-/opt/ai-ops/workflow.json}"

n8n import:workflow --input="$workflow_file"
n8n publish:workflow --id="$workflow_id"
exec n8n start
