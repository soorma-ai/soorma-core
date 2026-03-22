# Functional Design Plan — soorma-common (U1)
## Initiative: Multi-Tenancy Model Implementation
**Unit**: U1 — `libs/soorma-common`
**Wave**: 1 (unblocks all other units)
**Change Type**: Minor
**Date**: 2026-03-22

---

## Unit Context

**Requirements assigned to U1**:
- FR-1.1: `DEFAULT_PLATFORM_TENANT_ID` constant
- FR-1.2: `SOORMA_PLATFORM_TENANT_ID` env var override
- FR-1.3: Deprecation warning on constant (code comment, not runtime warning)
- FR-1.4: No format validation on tenant/user ID strings
- FR-6.1: `EventEnvelope.tenant_id` field retained (now = service tenant, update docstring)
- FR-6.2: `EventEnvelope.user_id` field retained (now = service user, update docstring)
- FR-6.3: Add `EventEnvelope.platform_tenant_id` field; Event Service injects it, SDK MUST NOT set it
- FR-6.4: Update all `EventEnvelope` field docstrings for new semantics
- NFR-3.2: No UUID format validation
- NFR-3.3: Constant must carry a clear code comment warning

**Construction stages for U1**:
- [x] Functional Design (this stage)
- [ ] NFR Requirements — SKIP (no NFR scope for U1)
- [ ] NFR Design — SKIP
- [ ] Infrastructure Design — SKIP
- [ ] Code Generation

---

## Questions Requiring User Input

> **Assessment**: All design decisions for U1 were resolved during the Inception phase (Requirements Analysis + Application Design). The component method signatures, constant value, env var name, field names, and docstring intent are all fully specified in `components.md` and `component-methods.md`.
>
> **No blocking questions** — proceeding directly to artifact generation.

---

## Functional Design Steps

- [x] Step 1: Analyze unit context — U1 scope from unit-of-work.md + component-methods.md reviewed
- [x] Step 2: Determine questions — none required (all design resolved in inception)
- [x] Step 3: Generate business-logic-model.md
- [x] Step 4: Generate business-rules.md
- [x] Step 5: Generate domain-entities.md
- [x] Step 6: Security compliance review (SECURITY baseline rules)
- [ ] Step 7: Await user approval and proceed to Code Generation

---

## Security Extension Compliance Summary

| Rule | Status | Rationale |
|------|--------|-----------|
| SECURITY-01 (Encryption at Rest/Transit) | N/A | U1 is a shared library with no data stores, databases, or network communication |
| SECURITY-02 (Access Logging on Network Intermediaries) | N/A | U1 has no network-facing components (library only) |
| SECURITY-03 (Application-Level Logging) | N/A | U1 is a pure Python library; no application runtime |
| SECURITY-04+ | N/A | No auth, no secrets, no external integrations in this library unit |

**Non-blocking**: All SECURITY rules are N/A for U1. No blocking security findings.

---

## Artifact Locations

```
aidlc-docs/platform/multi-tenancy/construction/soorma-common/functional-design/
  business-logic-model.md
  business-rules.md
  domain-entities.md
```
