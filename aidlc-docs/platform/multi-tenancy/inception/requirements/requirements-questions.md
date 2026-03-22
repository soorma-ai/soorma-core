# Requirements Clarification Questions

**Initiative**: Multi-Tenancy Model — soorma-core  
**INITIATIVE_ROOT**: `aidlc-docs/platform/multi-tenancy/`

Please answer the following questions to help finalize the requirements before workflow planning begins.

---

## Question 1
**Platform Tenant ID Format**

The request specifies the hardcoded platform tenant ID as `spt_00000000-0000-0000-0000-000000000000`. Does this suggest a `spt_` prefix convention for all platform tenant IDs, and should the ID validation in services enforce this prefix pattern, or is it just an opaque string up to 64 characters with no prefix enforcement?

A) `spt_` prefix is a convention hint only — validate as opaque string up to 64 chars, no prefix check

B) `spt_` prefix must be enforced — validate that platform tenant IDs always start with `spt_`

C) Apply a broader prefix pattern (e.g., `spt_` for system tenants, `pt_` for regular platform tenants) — I will define the full pattern

D) The default value is informational only — implement as opaque string, let the future Identity Service decide validation rules

E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 2
**Memory Service: Platform Tenant ID in DB Schema**

The memory service currently has a `tenants` reference table and uses `tenant_id UUID FK → tenants.id`. Under the new model, memory tables need to track both `platform_tenant_id` (who owns the agentic system) and `service_tenant_id` (the platform tenant's customer). What is the preferred approach?

A) Add `platform_tenant_id VARCHAR(64)` column to all memory tables; rename current `tenant_id` to `service_tenant_id`; remove the `tenants` reference table (no FK to a tenants table — platform tenants are trusted via header, not DB-joined)

B) Add `platform_tenant_id VARCHAR(64)` column to memory tables; keep `tenant_id` alongside it but change type to VARCHAR(64); keep the `tenants` table but change its PK to VARCHAR(64) and update the default to `spt_00000000-0000-0000-0000-000000000000`

C) Restructure: replace `tenants` / `users` reference tables entirely; use only `platform_tenant_id VARCHAR(64)` + `service_tenant_id VARCHAR(64)` + `service_user_id VARCHAR(64)` as plain columns with no FK to reference tables

D) Other (please describe after [Answer]: tag below)

[Answer]: Use Option C schema (three plain VARCHAR(64) columns, no reference tables), plus add a PlatformTenantDataDeletion service method that explicitly deletes all rows for a given (platform_tenant_id) or (platform_tenant_id, service_tenant_id) across all tables in a transaction, callable by a future GDPR compliance API.

---

## Question 3
**User Table and User Identity**

The memory service currently has a `users` reference table (UUID PK) that some memory tables FK to. Under the new model, service user IDs are managed by platform tenants (no Soorma-managed user registry in scope). Should the `users` table be removed?

A) Yes — remove the `users` table entirely; store `service_user_id` as a plain VARCHAR(64) column in memory tables with no FK constraint

B) Keep a `users` concept but restructure: `(platform_tenant_id, service_user_id)` composite key — no UUID, no FK to a reference table; user existence is trusted

C) Rename and repurpose: make (platform_tenant_id, service_user_id) the unique key; keep the table for auditing/tracking known user IDs seen by memory service

D) Other (please describe after [Answer]: tag below)

[Answer]: A, with similar to Q2 application managed delete for specific user's data using PlatformTenantDataDeletion service method

---

## Question 4
**Registry Service: Tenant ID Type Change**

The registry service `AgentTable` and `EventTable` currently have `tenant_id: UUID` (native PostgreSQL UUID type). Changing to `VARCHAR(64)` requires a DB migration and a code change. Should the registry service migration create a new column, backfill, and drop the old one, or use `ALTER TABLE ... ALTER COLUMN ... TYPE VARCHAR(64) USING tenant_id::text`?

A) Use `ALTER COLUMN TYPE` with a `USING` cast — simplest migration approach (requires no data to exist or all existing UUIDs become strings)

B) Create new `VARCHAR(64)` column, backfill from old UUID column, rename — safest for production data preservation

C) Drop and recreate tables — acceptable since this is a pre-production system with no persistent production data

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
**EventEnvelope Changes**

The `EventEnvelope` in `soorma_common/events.py` currently has `tenant_id: Optional[str]` and `user_id: Optional[str]`. Under the new model, the envelope may need to carry both `platform_tenant_id` and `service_tenant_id`. What change should be made to EventEnvelope?

A) Add `platform_tenant_id: Optional[str]` field; rename existing `tenant_id` to `service_tenant_id`; keep `user_id` but rename to `service_user_id` — full rename for clarity

B) Add `platform_tenant_id: Optional[str]` alongside the existing `tenant_id` and `user_id` fields — additive change, no renaming (backward compatible)

C) Keep EventEnvelope as-is; `tenant_id` = service tenant ID; platform tenant ID flows only via HTTP headers, not via event envelope — no change to EventEnvelope

D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 6
**SDK: Default Tenant ID Constant**

The SDK currently initializes with hardcoded or environment-variable tenant IDs. Should the SDK define a constant `DEFAULT_PLATFORM_TENANT_ID = "spt_00000000-0000-0000-0000-000000000000"` for the single hardcoded platform tenant?

A) Yes — define the constant in SDK/common and use it as the default in all clients and init scripts

B) Yes — define it in soorma_common (shared library) so all SDK and service code can reference it

C) No — keep it as an environment variable only (`SOORMA_PLATFORM_TENANT_ID`); no hardcoded constant in code

D) Other (please describe after [Answer]: tag below)

[Answer]: B. should be overridable with environment variable option C. MUST NOT be used when actual platform tenant authentication is implemented with future identity service.

---

## Question 7
**Tracker Service: Already uses String(255)**

The tracker service already uses `String(255)` for `tenant_id` and `user_id` in its DB model. Does it need any changes beyond:
- Ensuring max length is 64 chars (change to `String(64)`)
- Adding `platform_tenant_id VARCHAR(64)` alongside the existing `tenant_id` (service tenant)

A) Yes — add `platform_tenant_id` column and enforce max 64 chars on all ID columns

B) The tracker service is platform-scoped (like registry), not service-tenant-scoped — no `platform_tenant_id` needed; just enforce max 64 chars

C) The tracker service needs further analysis — I'll clarify the tenancy tier for tracker

D) No changes needed to tracker service at this time — leave as-is

E) Other (please describe after [Answer]: tag below)

[Answer]: A — apply the same three-tier identity model as the Memory Service.

**Rationale**: Plans and action-progress state machines in the Tracker represent the execution of a specific service user's goal within a specific service tenant's context (e.g., Acme Corp's customer Alice's research plan). This is service-tenant-scoped data, not platform-scoped. Therefore the Tracker needs the same column structure as Memory:

- Rename `tenant_id String(255)` → `service_tenant_id VARCHAR(64)` (the platform tenant's customer tenant)
- Rename `user_id String(255)` → `service_user_id VARCHAR(64)` (the service tenant's end user)
- Add `platform_tenant_id VARCHAR(64)` (injected server-side from the authenticated request context — never from the payload)

Migration note: since Tracker's columns are already `String(255)` (not UUID), no type cast is needed — migration is column renames + length tightening + adding the new `platform_tenant_id` column.

GDPR deletion: the `PlatformTenantDataDeletion` service method defined for Memory must also cover Tracker tables — delete `plan_progress` and `action_progress` rows scoped to `(platform_tenant_id)` or `(platform_tenant_id, service_tenant_id)` or `(platform_tenant_id, service_tenant_id, service_user_id)` in a single transaction.

---

## Question 8
**Backward Compatibility and Migration Strategy**

Since this is a pre-production system, is this a breaking change with a clean migration, or do we need to maintain any backward compatibility?

A) Breaking change — clean migration; no production data to worry about; existing dev/test data can be dropped and recreated

B) Semi-breaking — generate migration scripts that handle existing UUID data gracefully (cast UUID strings to VARCHAR)

C) Additive only — all new columns must be nullable (or have defaults) so existing data continues to work; no column renames or type changes

D) Other (please describe after [Answer]: tag below)

[Answer]: we don;t have to worry about data migration etc in favor of simplicity, ok to have breaking change.

---

## Extension Questions

---

## Question 9
**Team Collaboration Review Gates (PR Checkpoint Extension)**

Is this initiative a solo effort (one developer working end-to-end) or a team-based project requiring PR review checkpoints?

A) Enable team review gates — working with a team; use PRs as collaboration checkpoints at end of Inception and after each unit's design

B) Solo effort — no PR checkpoints needed; skip this extension

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 10
**JIRA Tickets Extension**

Should JIRA ticket content be generated at the end of the Inception phase (one Epic + one Story per unit of work)?

A) Yes — generate JIRA tickets at end of Inception

B) No — skip JIRA ticket generation

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 11
**QA Test Cases Extension**

Should structured test case specifications be generated from units of work and functional requirements?

A) Yes — generate QA test case specs (comprehensive: happy path, negative, edge cases, boundary conditions)

B) Yes — generate QA test case specs (happy path + basic negative only)

C) No — skip QA test case generation

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 12
**Security Baseline Extension**

Should security extension rules be enforced as blocking constraints during this initiative (recommended for production-grade infrastructure services)?

A) Yes — enforce all SECURITY rules as blocking constraints

B) No — skip SECURITY rules (this is pre-production / development)

C) Other (please describe after [Answer]: tag below)

[Answer]: A
