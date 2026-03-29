# Unit-1 NFR Requirements

## Scope
Unit-1 covers a shared dependency (`require_user_context`) in `soorma-service-common` that enforces required identity context for user-scoped endpoints.

## Inputs
- Functional Design artifacts from `construction/unit-1/functional-design/`
- Answers from `construction/plans/unit-1-nfr-requirements-plan.md`

## NFR Decisions (from answered questions)
- Q1: A - No hard numeric latency SLO for this initiative; best-effort low overhead.
- Q2: A - Failure message defaults are centrally defined in `soorma-service-common`.
- Q3: B - Validation warnings may include `platform_tenant_id` only; never service tenant/user IDs.
- Q4: A - Unit-1 test bar is shared-library unit tests only.
- Q5: A - Adoption is memory-service first in Unit-2; broader reuse documented for later.

## Non-Functional Requirements

### NFR-U1-01 Performance Efficiency
`require_user_context` must remain lightweight and synchronous, performing only field presence/emptiness checks.

Acceptance:
- No network I/O in dependency logic.
- No database I/O in dependency logic.
- Constant-time checks over already-resolved context values.

### NFR-U1-02 Message Consistency Contract
Error messages for missing identity context must be centrally owned by the shared library to ensure cross-service consistency.

Acceptance:
- Default messages are defined in shared dependency layer.
- Services do not define ad-hoc message variants for the same validation failures in this initiative.

### NFR-U1-03 Logging Privacy and Tenant Operability
When validation fails, logging policy should preserve privacy while enabling operational filtering.

Acceptance:
- Allowed: `platform_tenant_id` as filterable log field.
- Forbidden: `service_tenant_id`, `service_user_id`, tokens, and PII in validation warning logs.
- Validation errors returned to callers remain transport-agnostic.

Deferred strategy note:
- Tenant-facing troubleshooting exposure (self-service log views, scoped query APIs, redaction tiers) is out of scope for Unit-1 and should be designed as a future cross-service observability initiative.

### NFR-U1-04 Maintainability and Verification Bar
Shared dependency behavior must be verified by focused unit tests in `soorma-service-common` before code generation signoff.

Acceptance:
- Unit tests cover success, missing tenant, missing user, and empty/whitespace inputs.
- Unit tests assert expected generic failure messages.
- No cross-service compatibility matrix required in Unit-1.

### NFR-U1-05 Incremental Adoption Safety
Rollout should minimize blast radius by adopting memory service first.

Acceptance:
- Unit-2 applies dependency to memory user-scoped routes.
- Reuse guidance is documented for future services.
- Tracker or other services are not required in this initiative.

## Traceability
- FR-2, FR-3, NFR-1, NFR-5
- Supports downstream Unit-2 runtime enforcement decisions.
