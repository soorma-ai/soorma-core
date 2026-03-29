# Unit-1 Business Logic Model

## Purpose
Define reusable identity-context validation logic in `soorma-service-common` for all user-scoped service endpoints.

## Scope
- In scope: shared dependency behavior and composition model
- Out of scope: memory-service CRUD/query behavior (handled in Unit-2)

## Chosen Design Decisions
- Q1: Return existing context object unchanged on success
- Q2: Use distinct generic error messages by missing identity dimension
- Q3: Export from current top-level public module
- Q4: Replace existing `require_user_id` usage in this initiative scope
- Q5: Use composable dependency chain model for extensibility
- Q6: Shared-library tests cover happy path + empty/whitespace and message assertions (no compatibility harness)

## Functional Flow
1. Request enters service endpoint.
2. Existing tenant context dependency resolves request-scoped context.
3. `require_user_context` validates `service_tenant_id`.
4. `require_user_context` validates `service_user_id`.
5. If either is missing or empty/whitespace, raise `HTTP 400` with generic message.
6. If both are valid, return the same context object for downstream handler use.

## Validation Pipeline (Composable)
- `require_identity`: base identity validation seam for service context
- `require_user_context`: user-scope validation layer used for current initiative
- Future layers (not implemented in Unit-1): `require_role`, `require_scope`, etc.

The pipeline remains additive: each dependency validates a single concern and passes through canonical context.

## Input and Output Contract
### Input
- Request-scoped tenant context object (already parsed by shared context dependency)

### Output
- Same tenant context object instance, unchanged

### Failure Contract
- Raise `HTTPException(status_code=400, detail=<generic-message>)`

## Export/Reuse Model
- Dependency is exported from the existing top-level package surface used by services today.
- Downstream services import from stable top-level path, avoiding deep-path coupling.

## Operational Notes
- This design intentionally avoids transport-specific wording in errors.
- The dependency remains service-agnostic and can be reused by memory, tracker, and future services.
