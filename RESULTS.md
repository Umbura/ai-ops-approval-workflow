# Validation Results

Verification date: 2026-07-12

Version `1.0.1` was validated as a local end-to-end portfolio application.

## Automated Validation

```text
pytest: 34 passed
branch coverage: 88.80%
ruff: passed
ruff format: passed
mypy --strict: passed
compileall: passed
JavaScript syntax: passed
n8n JSON syntax and connection integrity: passed
Docker Compose configuration: passed
API container build: passed
```

GitHub Actions runs the same checks on pushes and pull requests to `main`.

## Hardening Validation

The final review added and validated:

- fail-fast LLM mode and runtime bounds;
- whitespace stripping and rejection of unknown request fields;
- model-input minimization that excludes requester identifiers and metadata;
- payload fingerprints for idempotency conflicts;
- atomic decision transitions using an immediate SQLite transaction;
- SQL aggregate metrics without an application-level row cap;
- rollback on persistence errors;
- CSP, SRI, defensive HTTP headers, and localhost-only port bindings;
- fail-closed webhooks with explicit decision-payload validation;
- transport-field sanitization before forwarding requests from n8n;
- exact Python base-image version;
- static type, formatting, and branch-coverage gates.

## OpenAI Runtime Validation

A single direct request was sent through `OpenAIResponsesTriageProvider` with fallback bypassed.

```text
model: gpt-5.4-mini
category: fraud_risk
priority: critical
confidence: 0.98
requires_human_review: true
```

The response matched the strict output schema. The deterministic safety boundary preserved human review for the high-value VIP fraud case.

No further paid calls were made. Automated provider tests use `httpx.MockTransport`.

## n8n Runtime Validation

n8n `2.29.10` was executed in Docker. The canonical workflow was imported, published, and exercised through both production webhooks.

Verified behavior:

- a request without `X-Webhook-Secret` returned HTTP `401`;
- an authenticated request reached the protected FastAPI service;
- repeated `X-Idempotency-Key` values returned one stored request;
- high-risk triage returned `needs_review`;
- the decision webhook recorded an approval;
- the final request status changed to `approved`;
- the decision and request creation produced audit events.

## Dashboard Validation

The dashboard was exercised against the Dockerized API.

Verified behavior:

- API-key connection dialog;
- metrics and review queue;
- request detail and risk context;
- decision modal;
- audit log navigation;
- no browser console errors;
- no document-level horizontal overflow at 1280 x 720 or 390 x 844.

## Scope

The validated scope is a complete local V1. Production infrastructure, PostgreSQL, role-based access control, and centralized observability remain deployment concerns rather than V1 requirements.
