# Unit-1 Business Rules

## BR-01: Service Tenant Must Be Present
For user-scoped operations, `service_tenant_id` must be present and non-empty after trimming whitespace.

- If missing/empty: reject request with HTTP 400.
- Error detail must remain generic and must not expose transport/header details.

## BR-02: Service User Must Be Present
For user-scoped operations, `service_user_id` must be present and non-empty after trimming whitespace.

- If missing/empty: reject request with HTTP 400.
- Error detail must remain generic and must not expose transport/header details.

## BR-03: Distinct Generic Error Messaging
Validation failures should emit distinct generic messages by identity dimension for better developer experience.

- Missing tenant dimension: generic tenant-context-required message.
- Missing user dimension: generic user-context-required message.
- Messages must avoid header names and internal transport mechanisms.

## BR-04: Pass-Through Success Contract
When validation succeeds, return the same resolved tenant context object unchanged.

- No mapping into alternate dict/object types for Unit-1.
- Downstream handlers continue using established context contract.

## BR-05: Top-Level Export Contract
`require_user_context` must be exported through the package's top-level public surface.

- Prevents downstream import churn.
- Avoids deep-path imports and internal coupling.

## BR-06: Immediate Transition Rule
Within this initiative scope, existing `require_user_id` usage should be replaced with `require_user_context` where user-scoped enforcement is required.

- No compatibility alias requirement for Unit-1 design.
- Implementation updates occur during code generation.

## BR-07: Composable Dependency Architecture
Identity and authorization checks should follow composable dependency chaining.

- Base identity validation can be composed with future authorization validators.
- Future examples: `require_role`, `require_scope`, resource-policy validators.

## BR-08: Unit-1 Test Contract
Shared-library tests for Unit-1 must verify:

- Happy path returns context unchanged.
- Missing tenant/user conditions return HTTP 400.
- Empty and whitespace-only values are rejected.
- Error messages match expected generic text per failure type.

No compatibility test suite for legacy dependency behavior is required for Unit-1.
