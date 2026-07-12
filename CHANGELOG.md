# Changelog

All notable changes are documented in this file.

## Unreleased

### Added

- Evidence-based comparison against the repositories and architecture studied before implementation.
- Curated screenshots of the review queue, audit trail, and canonical n8n workflow.

## 1.0.1 - 2026-07-12

### Added

- Strict static type checking with mypy.
- Branch coverage gate and expanded regression suite.
- Payload fingerprints for idempotency validation.
- Defensive HTTP headers and Subresource Integrity.
- Database indexes and atomic decision transactions.
- Fail-closed webhook authentication and explicit decision validation.

### Changed

- External model input is limited to fields required for triage.
- Runtime configuration fails fast on invalid LLM modes and bounds.
- API contracts reject unknown fields and whitespace-only values.
- Metrics use SQL aggregation instead of loading a capped request list.
- Docker ports bind to localhost and the Python base image is version-pinned.
- Request webhook transport fields are removed before backend forwarding.

### Fixed

- Conflicting payloads can no longer reuse an idempotency key silently.
- Concurrent decision attempts can no longer pass a non-atomic final-state check.
- Invalid model response fields are rejected before domain conversion.
- Legacy idempotency fingerprints are backfilled during schema initialization.
- Swagger UI assets are permitted by the documentation-specific CSP.
- Selected dashboard details refresh with newly loaded request state.
- Missing decision fields can no longer default to approval in n8n.

## 1.0.0 - 2026-07-11

- Initial complete local release with FastAPI, SQLite, OpenAI triage, n8n orchestration, human approval dashboard, Docker Compose, tests, and CI.
