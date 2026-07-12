# Reference Comparison

## Baseline

The implementation plan was based on a local study completed on 2026-07-02:

| Reference | Studied revision | Role in the study |
| --- | --- | --- |
| n8n | `ad404e6e`, n8n `2.29.0` | Webhooks, HTTP orchestration, conditional routing, waits, and human approval |
| LangGraph | `5931a5f`, LangGraph `1.2.7` | Stateful execution, checkpoints, interrupts, and idempotent resume patterns |
| CrewAI | `24901cd`, CrewAI `1.15.2a2` | Agent tasks, flows, structured output, and human feedback |
| n8n-workflows | `94007c1` | Common production workflow patterns and node usage |

The resulting design decision was to use n8n for visible orchestration and FastAPI for testable rules, persistence, safety enforcement, and audit. LangGraph and CrewAI were intentionally excluded from the V1 because the current state machine does not require a second orchestration framework.

## Implementation Matrix

| Reference criterion | Current implementation | Assessment |
| --- | --- | --- |
| Separate visual orchestration from business rules | n8n owns ingress and routing; FastAPI owns validation, triage, state transitions, and audit | Complete |
| Webhook, HTTP request, conditional branch, and controlled response | Two authenticated webhook paths, backend HTTP calls, fail-closed `IF` branches, and explicit response nodes | Complete |
| Structured LLM output with deterministic safety rules | OpenAI Responses API JSON Schema, mock provider, deterministic fallback, and forced human review | Complete |
| No sensitive final action before human approval | The system records recommendations and decisions but has no external action executor | Complete for V1 |
| Human-in-the-loop workflow | Dashboard and protected decision webhook record approve, reject, or request-changes outcomes | Complete at product level; partial against the n8n `Wait` or `sendAndWait` reference |
| Relational state and audit trail | SQLite stores requests, decisions, payload fingerprints, and append-only audit events | Partial: PostgreSQL, SQLAlchemy, and Alembic are deferred |
| Idempotent and concurrency-safe state changes | Payload-bound idempotency plus immediate SQLite transactions for final decisions | Complete |
| Reproducible local environment | Docker Compose starts the API and n8n with persistent local volumes and mock LLM mode | Complete |
| Minimum portfolio artifacts | Exported workflow, FastAPI backend, local database, audit log, README, tests, and screenshots | Complete |
| Demonstration dataset | Two committed request examples and additional fictitious runtime records | Partial: a versioned 10-20 request seed command is not yet available |
| Operational metrics | Request totals and status/category aggregates are available through the API and dashboard | Complete for operations; classification quality metrics are not implemented |
| Evaluation evidence | 34 automated tests, 88.80% branch coverage, CI, real n8n webhook validation, and one paid LLM smoke test | Partial: no labeled classification benchmark, latency distribution, or manual-time baseline |
| Cost and model provenance | Model mode is visible in health information and paid calls are controlled | Partial: token use, estimated cost, latency, and model provenance are not stored per request |
| Security baseline | API keys, fail-closed webhook secrets, strict contracts, CSP, SRI, localhost bindings, and minimized model input | Exceeds the initial portfolio baseline |

## Evidence

- [Review queue](images/review-queue.jpg): metrics, classification, confidence, rationale, and risk context.
- [Audit trail](images/audit-log.jpg): persisted request and human-decision events.
- [n8n workflow](images/n8n-workflow.jpg): independent request and decision paths from the canonical export.
- [Validation results](../RESULTS.md): automated, OpenAI, n8n, and dashboard verification.
- [Architecture](architecture.md): ownership boundaries and safety model.
- [Reuse and licensing](reuse_and_license.md): explicit reuse decisions for all studied repositories.

The n8n screenshot was produced from the canonical workflow in an isolated ephemeral instance. The canvas was auto-arranged and the non-executable sticky note was omitted only from the screenshot to improve framing. The committed workflow JSON remains unchanged.

## Conclusion

The V1 satisfies the minimum reference deliverable and demonstrates a functioning backend-first automation rather than a workflow-only mockup. It also implements the two strongest differentiators from the study: real human decisions and persistent auditability.

The remaining work is measurable rather than cosmetic. The next engineering priorities are:

1. Add a labeled request benchmark with category, priority, review-recall, latency, and fallback metrics.
2. Persist provider, model, latency, token usage, fallback status, and estimated cost for each triage result.
3. Add a reproducible fictitious seed command and a clean demonstration profile.
4. Move persistence to PostgreSQL with SQLAlchemy and Alembic when multi-instance deployment becomes a requirement.
5. Add an n8n `Wait` or `sendAndWait` notification path when email or Slack credentials are available.
