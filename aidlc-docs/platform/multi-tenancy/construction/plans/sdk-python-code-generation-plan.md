# Code Generation Plan — U6: sdk/python
## Initiative: Multi-Tenancy Model Implementation
**Date**: 2026-03-27
**Unit**: U6 — sdk/python (Wave 4)
**Depends On**: U4 (services/memory) complete, U5 (services/tracker) complete
**Change Type**: Moderate

---

## Architecture Alignment (docs/ARCHITECTURE_PATTERNS.md)

This plan aligns with:
- Section 1: Authentication model and header contracts
- Section 2: Two-layer SDK architecture (wrappers over service clients)
- Section 3: Event choreography trust boundary behavior
- Section 6: Fail-closed validation behavior
- Section 7: Unit + integration test expectations

---

## Unit Context

U6 aligns SDK client and wrapper identity semantics with the multi-tenancy model.

Primary scope for U6:
- Rename low-level memory client class to MemoryServiceClient to remove wrapper ambiguity
- Keep RegistryClient and EventClient names unchanged for this initiative
- Introduce platform tenant init-time behavior for low-level Memory/Tracker clients
- Rename per-call parameters tenant_id/user_id -> service_tenant_id/service_user_id for Memory/Tracker clients and wrappers
- Send three headers for Memory/Tracker requests: X-Tenant-ID, X-Service-Tenant-ID, X-User-ID
- Ensure EventClient publish includes X-Tenant-ID and does not set platform_tenant_id in payload
- Update CLI default handling and SDK docs in ARCHITECTURE_PATTERNS Section 1

Functional design rules in force: BR-1, BR-1a, BR-2, BR-3, BR-4, BR-4a, BR-5, BR-6, BR-6a, BR-6b, BR-7, BR-8, BR-9, BR-10, BR-11.

---

## Part 1 — Planning Status

- [x] Step 1 — Analyze U6 artifacts and approved business rules
- [x] Step 2 — Identify concrete SDK/documentation files for brownfield modification
- [x] Step 3 — Define executable sequence with FR/BR/TC traceability
- [x] Step 4 — Create this code-generation plan document
- [x] Step 5 — Summarize implementation approach for user review
- [x] Step 6 — Log code-generation plan approval prompt in audit.md
- [ ] Step 7 — Wait for explicit user approval to execute Part 2
- [ ] Step 8 — Record user approval in audit.md
- [ ] Step 9 — Update aidlc-state.md for execution start

---

## Planned Execution Steps (Part 2 — after approval)

### Group 1: SDK Service Client Refactor

- [ ] Step 10 — Refactor memory low-level client class and exports
  - Rename class to MemoryServiceClient
  - Update constructor to support platform_tenant_id init-time defaulting
  - Keep API shape consistent with two-layer architecture
- [ ] Step 11 — Update Memory client method signatures
  - Rename per-call args to service_tenant_id and service_user_id
  - Add fail-closed non-empty validation
  - Ensure header projection: X-Tenant-ID, X-Service-Tenant-ID, X-User-ID
- [ ] Step 12 — Update TrackerServiceClient signatures and header projection
  - Rename per-call args to service_tenant_id and service_user_id
  - Add fail-closed non-empty validation
  - Ensure same three-header behavior as Memory
- [ ] Step 13 — Update EventClient publish request path
  - Ensure X-Tenant-ID is always sent on publish
  - Preserve trust boundary by not writing platform_tenant_id into outbound payload

### Group 2: PlatformContext Wrapper Alignment

- [ ] Step 14 — Update context.memory wrapper methods
  - Rename wrapper parameters to service_tenant_id/service_user_id
  - Apply metadata defaults only when explicit args are omitted
  - Ensure explicit args take precedence over defaults
- [ ] Step 15 — Update context.tracker wrapper methods
  - Rename wrapper parameters to service_tenant_id/service_user_id
  - Apply same precedence model as memory wrapper
- [ ] Step 16 — Verify wrapper completeness
  - Confirm all modified service-client methods have wrapper coverage
  - Confirm agent-facing paths use wrappers and do not import service clients directly

### Group 3: SDK Call-Site and CLI Updates

- [ ] Step 17 — Update SDK call sites and examples using low-level clients
  - Replace old tenant_id/user_id argument names
  - Update imports for MemoryServiceClient rename where needed
- [ ] Step 18 — Update CLI initialization behavior
  - Align init path with DEFAULT_PLATFORM_TENANT_ID and env-first resolution
  - Keep no new CLI platform-tenant flag per approved design decision

### Group 4: Tests

- [ ] Step 19 — Update unit tests for Memory and Tracker low-level clients
  - Validate argument naming migration
  - Validate three-header outbound projection
  - Validate fail-closed behavior for missing service identity
- [ ] Step 20 — Update wrapper tests
  - Validate wrapper defaulting and explicit-override precedence
  - Validate delegation to low-level clients with renamed args
- [ ] Step 21 — Add/update EventClient publish tests
  - Validate X-Tenant-ID presence on publish calls
  - Validate platform_tenant_id not set by SDK payload path
- [ ] Step 22 — Execute test gate (decision C)
  - Run full sdk/python tests
  - Run affected integration checks for memory/tracker compatibility
  - Run full workspace regression pass

### Group 5: Documentation and Progress Artifacts

- [ ] Step 23 — Update docs/ARCHITECTURE_PATTERNS.md Section 1
  - Add three-header mapping table
  - Clarify init-time vs per-call identity split
  - Document Event Service platform_tenant_id injection trust boundary
- [ ] Step 24 — Create/update U6 code summary artifact
  - Path: aidlc-docs/platform/multi-tenancy/construction/sdk-python/code/code-summary.md
  - Include modified/created file inventory and test results
- [ ] Step 25 — Update relevant changelog/docs touched by U6 code changes

### Group 6: Workflow Tracking

- [ ] Step 26 — Mark completed execution checkboxes in this plan as work is performed
- [ ] Step 27 — Update aidlc-state.md for U6 code generation progress and completion
- [ ] Step 28 — Prepare U6 for construction stage completion review

---

## Requirement and Test Traceability

- FR-7.1, FR-7.2, FR-7.3 -> Steps 10-16
- FR-7.4, FR-7.5 -> Steps 13, 21
- FR-7.6 -> Steps 19-22
- FR-8.1, FR-8.2 -> Step 23
- TC-SP-001..TC-SP-011 -> Steps 19-23
- BR-11 full workspace test gate -> Step 22

---

## Brownfield File Touch Scope (Expected)

Expected modified areas include:
- sdk/python/soorma/memory/*
- sdk/python/soorma/tracker/*
- sdk/python/soorma/context.py
- sdk/python/soorma/events.py
- sdk/python/soorma/cli/commands/init.py
- sdk/python/tests/**
- docs/ARCHITECTURE_PATTERNS.md
- aidlc-docs/platform/multi-tenancy/construction/sdk-python/code/code-summary.md
