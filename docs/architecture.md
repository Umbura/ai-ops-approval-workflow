# Architecture

## Runtime Components

```mermaid
flowchart LR
    UI["Approval dashboard"] -->|X-API-Key| API["FastAPI"]
    CLIENT["External client"] -->|X-Webhook-Secret| N8N["n8n"]
    N8N -->|X-API-Key| API
    API --> MODE{"LLM mode"}
    MODE --> MOCK["Deterministic triage"]
    MODE --> OPENAI["OpenAI Responses API"]
    OPENAI -. provider failure .-> MOCK
    MOCK --> SAFE["Deterministic safety boundary"]
    OPENAI --> SAFE
    SAFE --> DB["SQLite"]
    DB --> UI
    UI --> DECISION["Human decision"]
    N8N --> DECISION
    DECISION --> DB
```

## Ownership

FastAPI owns:

- request validation;
- authentication;
- idempotency;
- triage-provider selection;
- deterministic safety enforcement;
- state transitions;
- persistence and audit events;
- dashboard assets.

n8n owns:

- external webhook ingress;
- webhook-secret validation;
- API orchestration;
- response shaping;
- decision-webhook routing.

The dashboard is an operational client. It does not contain business rules or direct database access.

## Persistence

SQLite stores requests, decisions, and audit events. Initialization applies additive schema migration for the idempotency key, enables foreign keys, configures a busy timeout, and uses WAL mode.

SQLite is appropriate for the local V1. A multi-instance production deployment should use PostgreSQL and managed migrations.

## Safety Boundary

Model output cannot bypass deterministic review rules. High or critical priority, fraud signals, high-value requests, sensitive customer tiers, and destructive actions always require human review.

The system records decisions but does not execute a sensitive final operational action.

## Runtime Packaging

Docker Compose starts:

- the FastAPI image built from `Dockerfile`;
- n8n `2.29.10`;
- persistent API and n8n volumes.

The n8n entrypoint imports and publishes the canonical workflow at every start. The workflow JSON remains the source of truth.
