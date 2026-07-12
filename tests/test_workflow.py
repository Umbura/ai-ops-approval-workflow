import json
from pathlib import Path


def test_n8n_workflow_has_valid_connections_and_security_nodes() -> None:
    workflow_path = Path(__file__).parents[1] / "workflows" / "ai_ops_approval_n8n.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    nodes = workflow["nodes"]
    node_names = {node["name"] for node in nodes}
    node_ids = [node["id"] for node in nodes]

    assert workflow["id"] == "AiOpsApprovalV1"
    assert len(node_ids) == len(set(node_ids))
    assert {
        "Validate Request Webhook",
        "Authorize Request Webhook",
        "Reject Request Webhook",
        "Validate Decision Webhook",
        "Authorize Decision Webhook",
        "Reject Decision Webhook",
    }.issubset(node_names)

    for source, outputs in workflow["connections"].items():
        assert source in node_names
        for branch in outputs["main"]:
            for connection in branch:
                assert connection["node"] in node_names

    serialized = workflow_path.read_text(encoding="utf-8")
    assert "local-development-key" not in serialized
    assert "local-webhook-secret" not in serialized
