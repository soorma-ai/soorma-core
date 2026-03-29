# Unit-1 NFR Design Patterns

## Scope
This document maps approved Unit-1 NFR requirements into implementable design patterns for the shared `require_user_context` dependency in `soorma-service-common`.

## Answer Traceability
- Q1: B (aggregate validation failures into one combined HTTP 400)
- Q2: A (structured warning logging with fixed fields + platform_tenant_id only)
- Q3: A (centralized immutable default error messages)
- Q4: A (two explicit logical components)
- Q5: A (deferred architecture decision documented with issue-ready content)

## Pattern 1: Aggregated Fail-Closed Validation
### Intent
Fail closed for invalid identity context while returning one deterministic validation response.

### Design
- Validate all required dimensions (`service_tenant_id`, `service_user_id`) in one pass.
- Collect missing/invalid dimensions internally.
- Return one `HTTP 400` failure after validation pass if any dimension is invalid.
- No downstream handler execution when validation fails.

### Why
- Consistent client behavior with one response per request.
- Avoids partial-validation leakage.
- Preserves fail-safe default behavior (deny on invalid context).

## Pattern 2: Structured Security-Safe Warning Logging
### Intent
Enable tenant-level operational filtering without exposing service-level identity details.

### Required log fields
- `event_name`: fixed value (e.g., `identity_validation_failed`)
- `severity`: warning
- `platform_tenant_id`: included when available
- `failure_reason`: enum or fixed code list
- `correlation_id` / request identifier if available

### Forbidden fields
- `service_tenant_id`
- `service_user_id`
- tokens, credentials, raw payloads, PII

### Why
- Supports multi-tenant troubleshooting at platform boundary.
- Maintains privacy minimization and least-exposure logging.

## Pattern 3: Centralized Immutable Message Catalog
### Intent
Ensure message consistency across service adopters.

### Design
- Define default message constants in shared library.
- Dependency uses constants directly for validation failures.
- No per-service overrides in Unit-1 scope.

### Why
- Eliminates wording drift.
- Stabilizes behavior and tests.
- Simplifies future migration to alternate auth transport.

## Pattern 4: Minimal Component Boundary Pattern
### Intent
Keep Unit-1 design explicit but not over-engineered.

### Components
1. Identity Validation Dependency (primary behavior)
2. Logging Adapter Interface Seam (structured event emission boundary)

### Why
- Matches initiative scope.
- Preserves extension point for future observability evolution.

## Deferred Architecture Decision (Issue-Ready)
### Deferred topic
Platform-wide tenant-scoped troubleshooting and observability exposure model across Soorma Core services.

### Trigger to revisit
- When platform tenants require self-service support and diagnostics across multiple services.
- When cross-service observability standardization work begins as a dedicated later initiative.

### GitHub issue draft content
Title:
- Design platform-wide tenant-scoped troubleshooting capability (later initiative)

Body:
- Problem:
  - Current Unit-1 logs establish a safe pattern for identity-validation events, but Soorma Core lacks a unified tenant-scoped troubleshooting capability across services.
- Goals:
  - Define authorized tenant-scoped access model for troubleshooting data across Memory, Tracker, Event, Registry, and shared platform telemetry.
  - Define redaction policy and field-level exposure contract.
  - Define query/API and UI boundary options for tenant-visible diagnostics.
  - Define audit, retention, and compliance requirements for tenant-visible diagnostics.
  - Evaluate whether to create a reusable structured logging capability/library for cross-service adoption (including field schema governance and migration strategy).
- Non-goals:
  - No change to Unit-1 dependency behavior in this initiative.
  - No immediate cross-service rollout in this initiative.
  - No implementation of a new shared structured logging library in this initiative.
- Acceptance criteria:
  - Architecture proposal reviewed by platform + security stakeholders.
  - Candidate tenant-scoped diagnostics model documented with authz controls.
  - Data classification, retention, and operational ownership documented.
  - Decision recorded on shared structured logging capability approach (build shared library vs standard contract-only approach).
  - Follow-up execution plan created as a separate initiative.
