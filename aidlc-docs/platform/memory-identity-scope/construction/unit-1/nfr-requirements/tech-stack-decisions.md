# Unit-1 Tech Stack Decisions

## Context
Unit-1 is implemented in existing stack boundaries:
- Python + FastAPI dependency pattern
- Shared package: `libs/soorma-service-common`
- Service consumers: memory service first

## Decision 1: Keep Existing Dependency Mechanism
Decision:
- Continue with FastAPI `Depends`-compatible dependency model.

Rationale:
- Already established in current service architecture.
- Minimal integration friction for Unit-2 adoption.

## Decision 2: Centralize Validation Message Defaults in Shared Library
Decision:
- Define and own default failure messages in `soorma-service-common`.

Rationale:
- Enforces consistent API behavior across services.
- Avoids message drift and duplicated wording logic.

## Decision 3: Logging Field Policy for Validation Failures
Decision:
- Permit `platform_tenant_id` as operational log filter field.
- Prohibit service tenant/user identifiers in validation warning logs.

Rationale:
- Balances multi-tenant operability with privacy minimization.
- Aligns with security baseline goals for least exposure.

## Decision 4: Verification Scope for Unit-1
Decision:
- Shared-library unit test suite is the required bar for Unit-1 NFR signoff.

Rationale:
- Unit-1 changes are isolated to shared dependency behavior.
- Cross-service integration behavior is validated in downstream units.

## Decision 5: Rollout Sequence
Decision:
- Adopt in memory service first during Unit-2; document wider reuse for later.

Rationale:
- Initiative scope is memory-identity-scope.
- Reduces risk and keeps delivery focused.

## Explicit Non-Decisions (Deferred)
- No tenant-facing observability product design in this initiative.
- No additional logging platform or SIEM architecture changes in Unit-1.
- No tracker-service adoption requirement in this initiative.
