# Application Design

## Summary
This design implements identity-scope consistency for Memory Service by introducing shared user-context validation and aligning API, service, CRUD, and schema components around a single full identity tuple:
- platform_tenant_id
- service_tenant_id
- service_user_id

Design decisions from plan answers:
- Q1: A — single shared require_user_context dependency
- Q2: A — router-level dependency application for user-scoped memory routers
- Q3: B — semantic public uniqueness includes service_tenant_id
- Q4: A — immediate enforcement (no compatibility window)

## Component Design
See [components.md](components.md) for full catalog and responsibilities.

Highlights:
- Shared Identity Context Validator in soorma-service-common
- Memory API Validation Boundary for user-scoped routers
- CRUD Scope Engine aligned to full identity predicates
- Schema/Index Governance for constraint and index parity
- Isolation Test Harness for enforcement verification

## Method and Interface Design
See [component-methods.md](component-methods.md) for method signatures and behavior boundaries.

Key interface contract:
- User-scoped operations require full identity tuple at all layers
- Missing service_tenant_id or service_user_id results in immediate HTTP 400
- Upsert conflict targets must match concrete unique constraints/indexes

## Service and Orchestration Design
See [services.md](services.md).

Primary orchestration flow:
1. Route resolves TenantContext
2. require_user_context validates required dimensions
3. Route -> service -> CRUD with full tuple propagation
4. DB RLS enforces platform scope; constraints/indexes enforce service tenant + user scope

## Dependency and Data-Flow Design
See [component-dependency.md](component-dependency.md).

Key boundaries:
- RLS: platform_tenant_id only (intentional)
- App-layer predicates/constraints: service_tenant_id + service_user_id
- Admin endpoint exception: no user-context dependency

## Design Consistency Checks
- Requirement coverage: FR-1 through FR-11 mapped to components/services
- Shared dependency reusable across services (not memory-specific)
- Public semantic uniqueness updated per decision Q3=B
- Immediate validation enforcement aligns with decision Q4=A
- No infra changes introduced in application design scope

## Implementation Readiness
This application design is ready to feed Units Generation and per-unit Functional Design in Construction phase.
