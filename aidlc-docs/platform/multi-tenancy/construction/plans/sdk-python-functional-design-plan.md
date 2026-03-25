# Functional Design Plan — U6 sdk/python
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-25  
**Unit**: U6 — sdk/python  
**Dependencies**: U4 (services/memory) ✓ COMPLETE, U5 (services/tracker) ✓ COMPLETE

---

## Unit Context

**U6 Scope** (from unit-of-work.md):
- Update `MemoryServiceClient.__init__`: accept `platform_tenant_id` parameter; default from `DEFAULT_PLATFORM_TENANT_ID` / `SOORMA_PLATFORM_TENANT_ID` env var
- Rename per-call params: `tenant_id → service_tenant_id`, `user_id → service_user_id` across all `MemoryServiceClient` methods
- Send as `X-Tenant-ID` (platform), `X-Service-Tenant-ID` (service tenant), `X-User-ID` (service user) headers
- Apply same changes to `TrackerServiceClient`
- Update PlatformContext wrappers (`context.memory`, `context.tracker`) to expose only service tenant/user dims at agent layer
- Update CLI commands (cli/commands/init.py) to use new `DEFAULT_PLATFORM_TENANT_ID` constant
- Update all SDK tests
- Update `docs/ARCHITECTURE_PATTERNS.md` Section 1 documentation

**Components Affected**:
- C6 — `sdk/python` Service Clients (MemoryServiceClient, TrackerServiceClient)
- C7 — `sdk/python` PlatformContext Wrappers (MemoryClient, TrackerClient)
- Updated documentation (ARCHITECTURE_PATTERNS.md)

**Architectural Constraints** (from soorma-core constitution):
- Strict two-layer SDK architecture: Service Clients (Layer 1) and PlatformContext Wrappers (Layer 2)
- Agent handlers MUST use `context.memory` and `context.tracker` wrappers ONLY — never import service clients directly
- Wrapper implementations MUST delegate to underlying service clients using Layer 1 HTTP communication
- All wrappers receive tenant/user context automatically from event envelope — no explicit parameters to agent handlers

---

## Functional Design Questions

**DIRECTIVE**: Below are clarifying questions about implementation approach, design boundaries, and migration strategy. All responses are required to ensure complete, unambiguous functional design artifacts.

Please answer each question by replacing `[Answer]:` with your response (A, B, C, D, or E if applicable).

---

### Q1: Service Client Parameter Binding Strategy

**Context**: `MemoryServiceClient` and `TrackerServiceClient` currently accept tenant/user as **per-call parameters**. We are refactoring to make `platform_tenant_id` an **init-time parameter** (set once at client creation) while `service_tenant_id` and `service_user_id` remain **per-call parameters**.

**Question**: When a service client is instantiated without an explicit `platform_tenant_id` parameter, how should the default value be resolved?

**Options**:
- A) Read `SOORMA_PLATFORM_TENANT_ID` env var; if absent, use `DEFAULT_PLATFORM_TENANT_ID` constant from `soorma_common.tenancy`
- B) Always use `DEFAULT_PLATFORM_TENANT_ID` constant; ignore env vars
- C) Allow both env var and constant, but require one to be explicitly set in `__init__`; raise error if both are absent
- D) Use `SOORMA_PLATFORM_TENANT_ID` env var only; raise error if absent

[Answer]:

---

### Q2: Header Injection in Service Clients

**Context**: Service clients send identity headers on every HTTP request to Memory Service and Tracker Service. Headers are currently: `X-Tenant-ID` (UUID), `X-User-ID` (UUID). After refactoring, they should be: `X-Tenant-ID` (platform tenant), `X-Service-Tenant-ID` (service tenant), `X-User-ID` (service user).

**Question**: Should the service client methods responsible for header injection be:

**Options**:
- A) Named `_inject_tenant_headers` (or similar); called in every HTTP request method before sending; builds header dict from `self.platform_tenant_id` + method parameters `service_tenant_id` + `service_user_id`
- B) Use a requests/httpx middleware or interceptor; automatically injects headers on every outgoing request without explicit per-method calls
- C) Create a separate header-builder helper class; client methods delegate to it
- D) Modify the httpx client initialization to use auth handlers or middleware directly tied to tenant metadata

[Answer]:

---

### Q3: PlatformContext Wrapper Signature Evolution

**Context**: PlatformContext wrappers (`MemoryClient`, `TrackerClient`) currently expose method signatures like:  
```python
async def store_task_context(self, task_id: str, tenant_id: str, user_id: str, ...) -> TaskContext
```

After refactoring, the unit spec says wrappers should NO LONGER expose `platform_tenant_id` as a parameter. Agent handlers should never set it. However, internally the wrapper MUST pass it to the underlying service client.

**Question**: How should wrappers extract event context (service tenant/user IDs) and pass them to underlying service clients?

**Options**:
- A) Wrappers receive `context: PlatformContext` instance as a method parameter; extract tenant/user from `context.event_envelope`; pass to client
- B) Wrappers store a reference to the current event envelope at initialization; extract tenant/user from stored enum on every method call
- C) Wrappers modify method signatures to accept an optional `event_context: EventContext` dataclass; agent handlers must pass it explicitly
- D) Agent handlers bind tenant/user into wrapper at dispatch time (via dynamic assignment or method binding); wrappers simply use them without explicit parameters

[Answer]:

---

### Q4: CLI Command Initialization Refactoring

**Context**: `cli/commands/init.py` currently initializes SDK clients (MemoryServiceClient, RegistryClient, etc.). The file reads tenant/user from command-line args and env vars. After refactoring, `MemoryServiceClient.__init__` will accept `platform_tenant_id`, which should default to `DEFAULT_PLATFORM_TENANT_ID` if not supplied.

**Question**: How should `cli/commands/init.py` be updated to pass `platform_tenant_id` to the client?

**Options**:
- A) Add a new optional CLI flag `--platform-tenant-id` (or `--developer-tenant-id`); if provided, pass it to `MemoryServiceClient.__init__`; if absent, let client use its internal default
- B) Read from env var `SOORMA_PLATFORM_TENANT_ID` before creating the client; pass it explicitly to `__init__`
- C) Remove all platform_tenant_id sourcing from CLI and let clients self-initialize from env/constant; CLI only manages service tenant/user
- D) Create a separate CLI command `init-developer-tenant` to configure platform tenant once; regular `init` command reuses stored value

[Answer]:

---

### Q5: Test Refactoring Scope

**Context**: SDK has unit tests in `sdk/python/tests/` covering MemoryServiceClient, TrackerServiceClient, PlatformContext wrappers, and agent handler integration. After refactoring, **all** test invocations of service clients and wrappers must use the new parameter signatures.

**Question**: For the test refactoring, should we:

**Options**:
- A) Update all existing test fixtures and mocks to use new `platform_tenant_id` init parameter + `service_tenant_id`/`service_user_id` per-call params; run full test suite with new signatures
- B) Create parallel test files (e.g., `test_memory_client_v2.py`) for new signatures; deprecate old tests; migrate gradually
- C) Use pytest parametrize to run the same tests with both old and new signatures; mark old-signature tests as deprecated
- D) Only test the changed code paths; skip legacy signature tests

[Answer]:

---

### Q6: Documentation Updates — ARCHITECTURE_PATTERNS.md

**Context**: `docs/ARCHITECTURE_PATTERNS.md` Section 1 currently documents headers as `X-Tenant-ID` (client tenant UUID) and `X-User-ID` (user UUID). After refactoring, we have **three** distinct headers: `X-Tenant-ID` (platform tenant), `X-Service-Tenant-ID` (service tenant), `X-User-ID` (service user).

**Question**: How should Section 1 be restructured to explain the new two-tier tenancy model and header mapping?

**Options**:
- A) Expand Section 1 with a new "Two-Tier Tenancy Model" subsection explaining Tier 1 (Developer/Platform Tenant) vs. Tier 2 (Client Tenant + User); include updated header table; keep current examples but annotate with new header names
- B) Reorganize entirely: move current Table (service → tenancy tier mapping) to top; add detailed explanation of each tier's purpose and scope; show header examples for Memory/Tracker vs. Registry services
- C) Create a new Section 1b "SDK Multi-Tenancy Implementation" covering only the SDK perspective (init params + per-call params); defer detailed service-side explanation to service sections (2.1, 2.2, etc.)
- D) Keep Section 1 mostly unchanged; add a callout box at the top referencing a new "Multi-Tenancy Implementation Guide" document

[Answer]:

---

### Q7: Error Handling & Validation

**Context**: Service clients will now receive `platform_tenant_id` at init time. It's possible to pass an empty string, None, or invalid value.

**Question**: Should service client `__init__` methods validate `platform_tenant_id`?

**Options**:
- A) No validation in `__init__`; accept any string (including empty), pass as-is to backend; let backend reject invalid values
- B) Validate non-empty string; raise `ValueError` if empty or None at init time
- C) Validate format (e.g., must match `spt_` prefix if it's a test/default tenant); raise `ValueError` for non-matching patterns
- D) Warn if default is used (log at init time: "Using default platform tenant ID `{DEFAULT_PLATFORM_TENANT_ID}`"); no validation

[Answer]:

---

### Q8: Migration Path for Existing SDK Callers (Non-Agent Code)

**Context**: Some existing code outside of agent handlers may directly instantiate `MemoryServiceClient` and `TrackerServiceClient` with old signatures (e.g., `client = MemoryServiceClient()` then `await client.store_task_context(tenant_id="...", user_id="...")`). After refactoring, the signature becomes `client = MemoryServiceClient(platform_tenant_id="...")` then `await client.store_task_context(service_tenant_id="...", service_user_id="...")`.

**Question**: How should we handle backward compatibility for non-agent callers?

**Options**:
- A) **Breaking change**: Remove old signatures entirely; update all callers in `examples/` and tests
- B) **Deprecation path**: Add new signatures; mark old ones with `@deprecated` warnings; keep both working for one release; plan removal in next version
- C) **Alias methods**: Add new parameter-named methods (e.g., `store_task_context_v2`) alongside old ones; keep both indefinitely
- D) **Factory pattern**: Create helper factory functions that wrap the client to accept old signatures and translate to new ones internally

[Answer]:

---

### Q9: PlatformContext Wrapper Implementation — Tenant/User Extraction Mechanism

**Context**: Currently, agent handler functions receive a `context: PlatformContext` instance that should have access to the current event envelope (containing tenant/user context). Wrappers like `context.memory` need to extract service tenant/user from this envelope and pass to the underlying service client.

**Question**: How is the current event envelope made available to PlatformContext at handler dispatch time?

**Options**:
- A) Event envelope is passed as a method parameter to every handler; PlatformContext stores it at initialization; wrappers read from stored reference
- B) Event envelope is bound to a thread-local or context var; PlatformContext queries it at runtime via `contextvars.get_context()` or similar
- C) PlatformContext is instantiated fresh for every event; envelope is injected into `__init__` at dispatch time
- D) Handlers bind event envelope to PlatformContext explicitly before calling wrapper methods (e.g., `context.set_event_envelope(envelope)`)

[Answer]:

---

### Q10: Service Client Constructor Flexibility

**Context**: Both `MemoryServiceClient` and `TrackerServiceClient` need similar refactoring: platform_tenant_id at init, service tenant/user per-call. But they may have slightly different initialization needs (different base URLs, timeouts, etc.).

**Question**: Should we:

**Options**:
- A) Apply identical patterns to both; any differences in init parameters are client-specific (documented in their own docstrings)
- B) Create a base class `TenantedServiceClient` with common init logic; both inherit and extend as needed
- C) Create a shared initialization helper function; both clients call it to ensure consistent behavior
- D) Keep them entirely independent; document expected patterns and do manual review for consistency

[Answer]:

---

## Plan Execution Steps

Once all questions are answered, Functional Design will execute these steps:

- [ ] Step 1: Analyze all Q1–Q10 answers for consistency and completeness
- [ ] Step 2: Create `construction/sdk-python/functional-design/business-logic-model.md` — service client architecture, parameter binding strategy, header injection mechanism
- [ ] Step 3: Create `construction/sdk-python/functional-design/domain-entities.md` — tenant/user parameter entities, header structures, default constant definitions
- [ ] Step 4: Create `construction/sdk-python/functional-design/business-rules.md` — validation rules, error handling, tenant context extraction logic for wrappers
- [ ] Step 5: Update `construction/plans/sdk-python-functional-design-plan.md` with all steps marked [x]
- [ ] Step 6: Notify user that Functional Design is ready for review

---

## Next Step

**Please answer all 10 questions above by replacing `[Answer]:` with your choice (A, B, C, D, or E).** Once all answers are provided, Functional Design artifacts will be generated.
