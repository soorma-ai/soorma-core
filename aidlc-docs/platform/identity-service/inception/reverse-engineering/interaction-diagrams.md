# Interaction Diagrams (Text)

## Transaction 1: Developer Registers Agent (Tier 1)
1. SDK/agent runtime calls Registry API with `X-Tenant-ID` (developer tenant).
2. Registry service resolves tenant context and persists agent metadata.
3. Query and discovery APIs return agents within the same developer tenant scope.

## Transaction 2: Worker Stores Task Context (Tier 2)
1. Worker handler receives event envelope with `tenant_id` and `user_id`.
2. `PlatformContext` wrapper resolves identity and delegates to MemoryServiceClient.
3. Memory service validates user context and sets DB session RLS dimensions.
4. Task context data is persisted and isolated by platform/service tenant + user dimensions.

## Transaction 3: Planner-Worker Event Choreography
1. Planner publishes task event to event service.
2. Worker consumes event and executes delegated action.
3. Worker responds using explicit `response_event` + correlation id.
4. Planner receives result and advances workflow state.

## Transaction 4: Plan/Task Observability Query
1. Client queries tracker endpoints with tenant/user context.
2. Tracker service applies tenant context and returns scoped progress/actions.
3. Results are visible only within authorized tenant boundaries.

## Identity-Service-Relevant Interaction Requirements
- Identity service must preserve tier boundaries:
  - Tier 1: developer-tenant admin identity operations.
  - Tier 2: end-user and machine-token issuance for downstream platform APIs.
- Token claims must carry enough data to map to current header model (platform tenant + service tenant + user) during transition period.