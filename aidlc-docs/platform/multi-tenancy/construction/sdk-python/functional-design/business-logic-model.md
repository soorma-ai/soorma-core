# Business Logic Model
## Unit: U6 - sdk/python
## Initiative: Multi-Tenancy Model Implementation

## Purpose
Define functional behavior for SDK multi-tenancy refactor in Layer 1 clients and Layer 2 wrappers.

## Scope
- Low-level SDK clients:
  - `soorma.memory.client.MemoryClient` -> renamed to `MemoryServiceClient`
  - `soorma.tracker.client.TrackerServiceClient` (existing name retained)
- Layer 2 wrappers:
  - `context.memory`
  - `context.tracker`
- CLI init behavior, docs updates, and test scope.

## Requirement Traceability
- FR-3.10: Memory SDK client headers update
- FR-7.1: platform_tenant_id at client init
- FR-7.2: Memory client per-call params renamed
- FR-7.3: Tracker client per-call params renamed
- FR-7.4: PlatformContext wrapper behavior aligned
- FR-7.5: CLI init uses existing platform tenant env/default model
- FR-7.6: SDK tests updated
- FR-8.1/8.2/8.3: ARCHITECTURE_PATTERNS.md Section 1 updated
- NFR-2.3: breaking-change-friendly refactor accepted pre-release

## Logical Components
1. Platform Tenant Binding
- Platform identity is fixed at low-level client construction time.
- Source order: explicit constructor value, else env/default constant behavior already implemented in soorma-common.

2. Service Identity Binding
- Service tenant and service user are per-operation values.
- Inputs may come from:
  - explicit method arguments
  - bound event metadata defaults (wrapper path)

3. Header Projection
- Every outgoing Memory/Tracker HTTP request projects identity into:
  - `X-Tenant-ID` = platform tenant
  - `X-Service-Tenant-ID` = service tenant
  - `X-User-ID` = service user

4. Wrapper Precedence
- Wrapper methods resolve identity using precedence:
  - explicit args from caller
  - otherwise event-bound metadata defaults
- Explicit caller-provided values always win.

## Runtime Flows

### Flow A: Low-level Client Initialization
1. Caller creates low-level client.
2. Client stores platform tenant identity for all future requests.
3. Client exposes methods requiring service_tenant_id and service_user_id per call.

### Flow B: Low-level Client Request Execution
1. Caller invokes Memory/Tracker method with service identity.
2. Client validates required service identity fields.
3. Client builds headers via internal helper.
4. Client performs HTTP request with explicit headers.

### Flow C: Wrapper Invocation with Implicit Defaults
1. Agent handler receives an event and context.
2. Context binds event metadata for downstream wrapper defaults.
3. Wrapper method called without explicit service identity.
4. Wrapper resolves identity from bound metadata.
5. Wrapper delegates to low-level client.

### Flow D: Wrapper Invocation with Explicit Overrides
1. Agent or test driver passes service_tenant_id/service_user_id explicitly.
2. Wrapper resolves identity and preserves explicit values.
3. Wrapper delegates with explicit values (metadata ignored for those fields).

### Flow E: Migration/Refactor Flow
1. Rename low-level memory client class to `MemoryServiceClient`.
2. Update SDK imports/callers to new class name.
3. Rename method parameter names from tenant_id/user_id to service_tenant_id/service_user_id.
4. Update all low-level-client example and test-driver call paths.
5. Update SDK tests and architecture docs.

## Failure Modes and Handling
- Missing service_tenant_id or service_user_id at call time -> fail fast with ValueError.
- Missing platform tenant at init -> rely on env/default fallback (pre-release behavior).
- Inconsistent identity between explicit args and metadata -> explicit args take precedence.

## Out of Scope
- Production auth redesign (Identity Service/JWT/API key) beyond documentation updates.
- Changes to backend service auth contracts in this unit.
