# Architecture

## MVP Architecture

```mermaid
flowchart LR
    A["n8n Webhook"] --> B["FastAPI POST /requests"]
    B --> C["Mock AI triage"]
    C --> D["SQLite audit store"]
    B --> E{"Human review required?"}
    E -->|Yes| F["n8n approval step"]
    E -->|No| G["Auto-suggest only"]
    F --> H["FastAPI POST /requests/{id}/decision"]
    G --> D
    H --> D
```

## Why FastAPI Owns Business Logic

n8n is excellent for orchestration and visibility, but business rules need tests, version control and clear APIs. This backend keeps triage, status transitions and audit logging in Python.

## Why Mock AI First

The MVP must work without API keys or credit spend. The current triage engine is deterministic and easy to test. A later version can swap it for a real LLM while keeping the same response schema.

## Human Approval Rule

The system never executes a sensitive final action directly. It only suggests an action and records a human decision.

