# Business Rules
## Unit: U6 - sdk/python

## Naming and Layer Rules

### BR-1: Low-level memory client naming
- Rename low-level memory service client class to `MemoryServiceClient` to avoid confusion with `PlatformContext` wrapper `MemoryClient`.
- Update all affected imports and call sites in this unit.

### BR-2: Two-layer separation
- Agent code must continue to use wrapper APIs (`context.memory`, `context.tracker`).
- Wrappers must delegate to low-level service clients.
- Agent handlers must not import low-level clients directly.

## Identity Resolution Rules

### BR-3: Platform identity lifetime
- `platform_tenant_id` is init-time client state for low-level Memory/Tracker clients.
- It is never a per-call method argument.

### BR-4: Service identity per-call requirements
- `service_tenant_id` and `service_user_id` are required for operations that call Memory/Tracker APIs.
- Missing required values must fail in SDK before request dispatch.

### BR-5: Wrapper precedence model
- Wrappers apply fallback defaults from bound event metadata only when explicit args are omitted.
- Explicitly provided args always take precedence over metadata defaults.

### BR-6: Header projection
- Every Memory/Tracker request must include all three identity headers:
  - `X-Tenant-ID`
  - `X-Service-Tenant-ID`
  - `X-User-ID`

## Migration and Compatibility Rules

### BR-7: Pre-release compatibility strategy
- This unit adopts a breaking-change path for renamed low-level method parameters:
  - `tenant_id` -> `service_tenant_id`
  - `user_id` -> `service_user_id`
- No backward-compatibility shim is required for this initiative phase.

### BR-8: Low-level caller migration completeness
- All low-level-client examples and test-driver clients must be updated to renamed parameter names and class renames.
- No stale low-level call path may remain on old identity parameter names.

## CLI and Documentation Rules

### BR-9: CLI platform tenant configuration
- CLI does not add a new platform-tenant flag in this unit.
- CLI behavior relies on existing env/default resolution model.

### BR-10: Architecture docs update scope
- Update `docs/ARCHITECTURE_PATTERNS.md` Section 1 in place.
- Include:
  - three-header mapping
  - init-time vs per-call parameter split
  - Event Service platform_tenant_id injection trust boundary note

## Test Gating Rules

### BR-11: Completion gate for U6 code generation
- Required test execution scope: full workspace tests (`C` decision).
- Minimum expected for this unit:
  - full sdk/python tests
  - affected example/test-driver checks
  - workspace-level regression pass per selected gate

## Security Baseline Alignment

### Applicable
- SECURITY-11 (Secure Design Principles): compliant
  - clear separation of concerns between wrappers and low-level clients
  - defense-in-depth through SDK validation + backend validation
- SECURITY-15 (Exception Handling and Fail-Safe Defaults): compliant
  - fail-fast behavior for missing identity values

### Not Applicable to this stage artifact set (N/A)
- SECURITY-01, SECURITY-02, SECURITY-04, SECURITY-06, SECURITY-07, SECURITY-09, SECURITY-10, SECURITY-12, SECURITY-13, SECURITY-14
  - rationale: these concern infrastructure/deployment/runtime controls outside U6 functional design artifact scope

### Conditionally Applicable in code generation phase
- SECURITY-03, SECURITY-05, SECURITY-08
  - to be validated against implemented code paths during U6 code generation and tests
