import json
from pathlib import Path
from typing import Any

WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "workflows" / "ai_ops_approval_n8n.json"


def load_workflow() -> dict[str, Any]:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def load_nodes() -> dict[str, dict[str, Any]]:
    workflow = load_workflow()
    return {node["name"]: node for node in workflow["nodes"]}


def test_workflow_has_valid_connections_and_no_embedded_credentials() -> None:
    workflow = load_workflow()
    nodes = workflow["nodes"]
    node_names = {node["name"] for node in nodes}
    node_ids = [node["id"] for node in nodes]

    assert workflow["id"] == "AiOpsApprovalV1"
    assert len(node_ids) == len(set(node_ids))
    for source, outputs in workflow["connections"].items():
        assert source in node_names
        for branch in outputs["main"]:
            for connection in branch:
                assert connection["node"] in node_names

    serialized = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "local-development-key" not in serialized
    assert "local-webhook-secret" not in serialized


def test_webhook_authentication_fails_closed() -> None:
    nodes = load_nodes()

    for node_name in ("Validate Request Webhook", "Validate Decision Webhook"):
        code = nodes[node_name]["parameters"]["jsCode"]
        assert "expected.length > 0" in code
        assert "!expected" not in code


def test_decision_webhook_requires_explicit_valid_decision() -> None:
    nodes = load_nodes()
    validation_code = nodes["Validate Decision Webhook"]["parameters"]["jsCode"]
    conditions = nodes["Authorize Decision Webhook"]["parameters"]["conditions"]["conditions"]
    request_body = nodes["Record Backend Decision"]["parameters"]["jsonBody"]

    assert "decision_payload_valid" in validation_code
    assert "uuidPattern.test(requestId)" in validation_code
    assert any(
        condition["leftValue"] == "={{ $json.decision_payload_valid }}" for condition in conditions
    )
    assert "|| 'approve'" not in request_body
    assert "|| 'n8n-reviewer'" not in request_body


def test_request_webhook_sanitizes_transport_fields() -> None:
    nodes = load_nodes()
    validation_code = nodes["Validate Request Webhook"]["parameters"]["jsCode"]
    request_body = nodes["Create Backend Request"]["parameters"]["jsonBody"]

    assert "delete body.idempotency_key" in validation_code
    assert request_body == "={{ JSON.stringify($json.request_payload) }}"
