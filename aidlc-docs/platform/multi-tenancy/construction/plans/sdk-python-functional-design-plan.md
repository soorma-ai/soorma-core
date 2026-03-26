# Functional Design Plan - U6 sdk/python
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-26
**Unit**: U6 - sdk/python
**Dependencies**: U4 (services/memory) complete, U5 (services/tracker) complete

---

## Quality Review Outcome

This plan has been regenerated to remove trivial or invalid questions and to align terminology with current code.

### Issues found in prior draft
- Low-level memory client was referenced as MemoryServiceClient, but current class is `soorma.memory.client.MemoryClient`.
- Some questions asked to decide behavior that is already implemented (for example platform tenant default resolution).
- Some questions mixed layer responsibilities (PlatformContext wrapper behavior vs low-level client init behavior).

### Scope reminder for U6
- Refactor low-level SDK clients to send three headers:
  - X-Tenant-ID (platform tenant, init-time)
  - X-Service-Tenant-ID (service tenant, per-call)
  - X-User-ID (service user, per-call)
- Rename per-call parameters from tenant_id/user_id to service_tenant_id/service_user_id in Memory and Tracker clients.
- Update all example/test-driver code paths that use low-level service clients to the renamed parameters and any class renames from this unit.
- Update PlatformContext wrappers (context.memory, context.tracker) to align with two-tier tenancy model.
- Update CLI and tests.
- Update architecture documentation.

---

## Resolved Decisions (No Further Input Required)

### D1: Platform tenant default resolution
- **Locked Decision**: Use env-first fallback.
- **Behavior**: Read SOORMA_PLATFORM_TENANT_ID; if absent, use DEFAULT_PLATFORM_TENANT_ID.
- **Note**: This is already implemented in soorma-common tenancy constant resolution.

### D2: Header injection style in low-level clients
- **Locked Decision**: Use a client-level internal helper to build headers and pass headers explicitly per request.
- **Reason**: Matches existing SDK client style and keeps request identity explicit.

---

## Open Functional Design Questions

Please answer each question by filling the [Answer]: tag.

## Question 1
How should low-level memory client naming be handled to avoid confusion with the PlatformContext MemoryClient wrapper?

A) Rename low-level class to MemoryServiceClient now, and update all SDK imports/call sites in this unit

B) Keep low-level class name as MemoryClient and only clarify in docs/comments

C) Keep class name but add alias export MemoryServiceClient for clarity, migrate internal usage gradually

D) Other (please describe after [Answer]: tag below)

[Answer]: A - prefer immediate rename for readability and developer experience, accepting near-term refactoring cost.

## Question 2
How should context.memory/context.tracker obtain service_tenant_id and service_user_id by default in handler execution paths?

A) Add contextvars binding (similar to BusClient metadata binding) for memory/tracker wrappers and apply implicit defaults when args omitted

B) Keep explicit parameters required on wrapper methods; no implicit binding

C) Add a shared identity accessor on PlatformContext and have wrappers read from it

D) Other (please describe after [Answer]: tag below)

[Answer]: A - sufficient, with explicit-override semantics: wrappers apply metadata defaults only when args are omitted; agent-provided service_tenant_id/service_user_id must always take precedence.

## Question 3
For backward compatibility, how should renamed low-level method parameters be handled (tenant_id/user_id -> service_tenant_id/service_user_id)?

A) Breaking change now: remove old names and update all internal callers/tests immediately

B) One-release compatibility: accept both old and new names with deprecation warning, then remove old names next release

C) Keep old names permanently as aliases to new names

D) Other (please describe after [Answer]: tag below)

[Answer]: A is sufficient. we are pre-release and do not have to be backward compatible.

## Question 4
What SDK-side validation should apply for identity parameters before making HTTP calls?

A) Validate non-empty service_tenant_id and service_user_id in wrappers/clients; raise ValueError before request

B) No SDK validation; pass through and let backend return validation errors

C) Hybrid: enforce only non-empty user_id, allow service_tenant_id optional for specific endpoints

D) Other (please describe after [Answer]: tag below)

[Answer]: A. we are aligning on always having a service tenant id and user id be provided by the platform tenant's agent implementations. this should also be captured in architecture docs, if not already done.

## Question 5
How should CLI initialization expose platform tenant configuration for SDK usage?

A) Add optional --platform-tenant-id flag and pass to client init when supplied

B) Do not add new flag; rely on SOORMA_PLATFORM_TENANT_ID/env default resolution only

C) Add flag plus persisted local profile/config for reuse

D) Other (please describe after [Answer]: tag below)

[Answer]: B. this is just temporary and will anyway get replaced with future authentication scheme implementation with platform identity service before final releasing.

## Question 6
How should docs/ARCHITECTURE_PATTERNS.md be updated for SDK multi-tenancy changes?

A) Expand Section 1 in-place with updated header mapping and SDK init/per-call parameter split

B) Keep Section 1 concise and add a dedicated subsection specifically for SDK client header behavior

C) Add a separate SDK multi-tenancy document and only cross-reference from Section 1

D) Other (please describe after [Answer]: tag below)

[Answer]: A. keep updates in Section 1 for now; this area will be replaced/reimplemented with proper service authentication in a future release.

## Question 7
What test execution scope should gate completion of U6 code generation?

A) Full sdk/python test suite plus targeted integration tests touching Memory and Tracker client calls

B) Only targeted unit tests in changed files

C) Full workspace tests (all packages/services)

D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Plan Execution Steps

- [x] Step 1: Validate all answers for completeness and ambiguity
- [x] Step 2: Generate functional design artifacts in aidlc-docs/platform/multi-tenancy/construction/sdk-python/functional-design/
- [x] Step 3: Update this plan with resolved decisions and mark completion checkboxes
- [x] Step 4: Present Functional Design completion message for user approval

---

## Next Step

Functional Design artifacts have been generated at:
- aidlc-docs/platform/multi-tenancy/construction/sdk-python/functional-design/business-logic-model.md
- aidlc-docs/platform/multi-tenancy/construction/sdk-python/functional-design/domain-entities.md
- aidlc-docs/platform/multi-tenancy/construction/sdk-python/functional-design/business-rules.md

Awaiting user review/approval.
