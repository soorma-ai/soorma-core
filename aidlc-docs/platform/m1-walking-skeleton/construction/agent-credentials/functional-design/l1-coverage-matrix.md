# L1 Coverage Matrix: U6 `agent-credentials`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`,
  the main source for this unit
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Verification targets**: `TC-AC-001` to `022` are the inception specs
(`inception/test-cases/agent-credentials/`). *QA enrichment* marks a verification the QA
construction enrichment adds as a test case before the Construction Design PR gate; it replaces
each marker with a test-case ID.

**Result**: 34 applicable rows, all `Covered`. Three rest on the inherited work-arounds: L1-27 and
L1-29 on **GAP-INT-008** (Open, soorma-prd#27), L1-28 on **GAP-INT-009** (Open, soorma-prd#28).
**0 `Missing`.**

**Updated at NFR Design (2026-11-12)**: implementation targets made concrete, no row's status
changed. L1-01, L1-13, L1-17: `packages/credentials/src/agent-token.ts` (NP-AC-09). L1-02:
`PROPAGATION_BOUND_MS`, `AGENT_CREDENTIAL_LIFETIME_MS`, `LINEAGE_MAX_AGE_MS`, code constants
(NP-AC-01) and `agent_credentials`' `expires_at <= lineage_ends_at` (NP-AC-03). L1-04, L1-05,
L1-06: `packages/agent-identity` over the seam's agent half (NP-AC-08). L1-07, L1-22:
`agent_credentials` and its renew statement, the binding in its `WHERE` (NP-AC-03). L1-08 to
L1-10, L1-14: `credential_revocations`, `agent_revocations` with foreign keys, `SELECT` only
(NP-AC-04, 06). L1-11, L1-24: the per-credential cache in `revocation.ts` (NP-AC-05). L1-15:
`attempt_slots` and `failed_bootstrap_attempts` in E's store, P8's `SlotBound` (NP-AC-07). L1-23:
the agent key ring on U4's loader (NP-AC-09). L1-27: `0004`'s CHECK (NP-AC-02). L1-33: S3's
manifest walk and the image check (NP-AC-10).

---

## Applicable to U6

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | PF §7a *Agent Credential*, §3: asserts **logical agent X, environment Y, instance Z** | D-AC-13; BR-CR-AC-01; domain-entities *Token* | P5 mint and verify; S3 | TC-AC-001; TC-AC-016 | Covered |
| L1-02 | PF §7a: **short-lived and renewable** | BR-CR-AC-04; D-AC-02 (L, M) | P5; S3 renewal | TC-AC-001; TC-AC-003; *QA enrichment*: renewal near the lineage end is capped, and at the end is `credential_expired` | Covered |
| L1-03 | PF FR-009, §7a, §11: **the instance identifier is asserted, recorded, not verified** | D-AC-07, 23; BR-BQ-01 | S3 schema; P5 record and token | TC-AC-002; *QA enrichment*: two live credentials of A asserting the same identifier both work | Covered |
| L1-04 | PF FR-009: material **bound to a registered, non-retired, non-revoked logical agent in a named environment**; a short-lived credential issued | BR-BS-03 to 06; D-AC-09 | P6 agent half; S3; P5 | TC-AC-001; TC-AC-014; *QA enrichment*: a revoked agent (seeded) cannot bootstrap | Covered |
| L1-05 | PF FR-009, §8b, FR-026; M1-FR-13: **the accepted material types are the identity-resolution seam**; core accepts a locally verified registration secret | D-AC-04, 08, 20; BR-BS-01 | `seams/identity-resolution` (agent half); `packages/agent-identity` | TC-AC-022; *QA enrichment*: the seam's agent half returns identity only (no state or revocation decided in it) | Covered |
| L1-06 | PF §7a *Registration Secret*: verified at exchange; **lifecycle independent of any credential's** (FR-008) | D-AC-15, 19; BR-RN-06 | P6 agent half; S3 renewal reads no secret | TC-AC-007; *QA enrichment*: renewal succeeds without consulting the secret (a store probe shows no secret read) | Covered |
| L1-07 | PF FR-010: renewal of a **currently valid, unrevoked** credential yields a replacement; **never widens**; **never outlives revocation**; **not weaker than issuance**; a lapsed instance re-bootstraps | D-AC-14, 15; BR-RN-01 to 09 | S3 renewal; P1 `checkAgentRequest`; P5 | TC-AC-003; TC-AC-009; TC-AC-011; TC-AC-016 | Covered |
| L1-08 | PF §7a *Revocation State*, FR-011: **two granularities**, credential and logical agent | D-AC-16; BR-RV-01 | P5 revocation state; the test fixture | TC-AC-009; *QA enrichment*: an agent-granularity revocation refuses renewal and bootstrap | Covered |
| L1-09 | PF §7a: revocation state **environment-scoped, readable by no principal** | BR-RV-03, 04; BR-BS-07 | P5; no edge operation | TC-AC-018 | Covered |
| L1-10 | PF FR-011: revocation is **terminal**; reinstatement is a new issuance | BR-RV-02; D-AC-14 | P5; the cache keeps `revoked` | *QA enrichment*: after a `cid` is revoked, a new bootstrap gives a new `cid` that works, and the old lineage stays refused | Covered |
| L1-11 | PF FR-012, O3: read **on every request**; cached **at most one published bound**, then **deny**; the bound finite, published, platform-set, not tenant-configurable; **one value** (M1-NFR-01; NFR-AE-10) | D-AC-01, 18; BR-RC-01 to 05 | P5 cache (S4 wiring: U7); S3 direct reads; **`PROPAGATION_BOUND_MS`, a code constant** (NFR Design NP-AC-01; not configuration, so not tenant-configurable) | TC-AC-010; TC-AC-015 (adjusted at enrichment: P5 clock and outage tests, §5 of the business logic model) | Covered |
| L1-12 | PF §8a *Exchange bootstrap material*: data face, Gateway; **n/a to delegation** | D-AC-24; business-rules §12 | S3; `contract/data-gateway.openapi.yaml` | TC-AC-021 | Covered |
| L1-13 | PF §8a *Renew credential*: a currently valid, unrevoked credential **for the same logical agent** | BR-RN-02, 08 | S3 renewal | TC-AC-016 | Covered |
| L1-14 | PF §8a *Read revocation state*: **no principal; internal** | BR-RV-04; D-AC-16 | P5 only; no route | TC-AC-018 | Covered |
| L1-15 | PF FR-027: failed attempts **recorded against the registration**; attempt volume **per registration bounded** | D-AC-06, 22; BR-AB-AC; BR-FA | P8; the writer | TC-AC-007; TC-AC-008; TC-AC-022 | Covered |
| L1-16 | PF FR-027: bootstrap is **unauthenticated** (no credential yet) | BR-PR-AC-02; D-AC-24 | S3; P1 | *QA enrichment*: any `Authorization` or `Soorma-Delegation` header on bootstrap is `malformed_request` naming it | Covered |
| L1-17 | PF §8b **O1, O2, O4** at renewal; O4 compared field by field | BR-CR-AC-03; D-AC-27 | P1 `checkAgentRequest`; P5 verify | TC-AC-011; TC-AC-013 | Covered |
| L1-18 | PF §8b **O9**: deny by default | business-rules §10; U1's unknown path | S3 routing | *QA enrichment*: any other method or path on S3 is a bare `404` | Covered |
| L1-19 | PF §8b **O10**: no entry point treats another's traffic as pre-validated | D-AC-27 | S3 runs its own checks; S4 (U7) runs `checkAgentRequest` again | TC-AC-021; U7's | Covered |
| L1-20 | PF §8b **O11**, FR-022: environment identity configured, never inferred | D-AC-09; BR-CR-AC-03 | S3 configuration (P9) | *QA enrichment*: the credential's `env` equals the configured identity, whatever host serves it | Covered |
| L1-21 | PF §8b **O12 does not apply** to bootstrap or renewal | D-AC-28 | S3: no origin check | *QA enrichment*: an agent registered **without** autonomy declared bootstraps and renews | Covered |
| L1-22 | PF §6: **agent credential (per instance)**, **credential identifier**, **instance identifier** keyed on environment | domain-entities *Record*; D-AC-32 | P5 record (three columns) | TC-AC-013; *QA enrichment*: one test per access path (record, revocation, slot, failed attempt) that E's reads never return E2's rows | Covered |
| L1-23 | PF §6 *Credentials* isolation: compromise of one environment's issuance **cannot mint for another**; no shared minting material | D-AC-03; BR-CR-AC-02 | Per-environment agent key ring | TC-AC-020 | Covered |
| L1-24 | PF §6: **revocation state cache** and **credential validation cache** keyed on environment; **no global revocation list** | BR-RC-04; BR-RV-03 | P5 cache; per-environment store | *QA enrichment*: the cache key includes E; a revocation in E2 never affects E | Covered |
| L1-25 | PF §9 *Failure Modes*: unrecognised material denied and recorded; a retired or revoked agent denied; expired: renew or re-bootstrap; revoked: terminal; revocation state unavailable: cache until the bound, then deny | BR-BS; BR-RN; BR-RC-03 | S3; P5 | TC-AC-007; TC-AC-009; TC-AC-010; TC-AC-011; TC-AC-014 | Covered |
| L1-26 | PF §9 *NFR Profile*: **two latency classes**; availability bounded by the cache, not the store; throughput by request volume | business-rules §17 (NFR Requirements) | NFR Requirements and Design | *NFR Requirements* sets the targets; Build and Test reports them | Covered |
| L1-27 | PF FR-025, §7b; M1-FR-12: **bootstrap and renewal attributed**: scope, agent actor (instance, registration, resolved sponsor); sponsorship resolvable. **No chain, origin, or re-broadening, and the record states why from the record alone: its operation, `exchangeBootstrap` or `renewAgentCredential`, is one that never carries an envelope (GAP-INT-008)** (the user's precision on P-12) | D-AC-21, 33; BR-AT-AC-01 to 03 | P7 (the envelope-free list, its refusal, the CHECK); S3 | TC-AC-005; *QA enrichment*: from the record alone, the operation is in the envelope-free list and the envelope columns are empty; an agent record for either operation with envelope facts is refused | Covered (GAP-INT-008 work-around) |
| L1-28 | PF FR-025 vs §8a (GAP-INT-009): **the internal revocation read writes no attribution record** | D-AC-17; BR-RV-06 | P5 reads | TC-AC-019 | Covered (GAP-INT-009 work-around) |
| L1-29 | PF FR-001, §11 (GAP-INT-008): **neither bootstrap nor renewal carries an envelope** | D-AC-28; BR-BQ-01; BR-RN-05 | S3 schemas; the contract | TC-AC-004; *QA enrichment*: a draft envelope in the bootstrap body is `malformed_request` | Covered (GAP-INT-008 work-around) |
| L1-30 | PF §11 *Harness Surface*: *Acquire* (material recognised, live registration, neither retired nor revoked, instance recorded); *Renew* (O1 to O3); *Hold and present* (O1 to O4) | BR-BS; BR-RN; D-AC-27 | S3; P1 (S4 at U7) | TC-AC-001; TC-AC-003; TC-AC-021 (raw calls) | Covered |
| L1-31 | PF §17 *Revocation Behaviour*: terminal, without redeploying, within a finite published bound; past it, unreadable state denies | BR-RV-02; BR-RC-03; §13 (the bound published) | P5; the contract conventions | TC-AC-015 (as adjusted); *QA enrichment*: the published bound equals the configured value | Covered |
| L1-32 | ID §8b *Entry points by principal*, FR-023: **every human credential refused at S3**; an agent credential beside a human's, or with `Soorma-Delegation`, refused | D-AC-10; BR-PR-AC-04 | P1 presenter at S3 | TC-AC-012; *QA enrichment*: each presenter row of ID §8b at S3 | Covered |
| L1-33 | M1-NFR-08; ID FR-009: **no organization-level dependency** on the data face | D-AC-11, 12; business-rules §12 | S3's closure; no S1 address | TC-AC-017; *QA enrichment*: the closure test (no `@soorma/org-identity` or `@soorma/identity-resolution`) | Covered |
| L1-34 | PF §8b *What a credential asserts*: **registration, not code identity**; nothing assumes a managed runtime | BR-CR-AC-01; D-AC-23 | P5 token claims | *QA enrichment* (with I10 review): no claim or check reads code identity or topology | Covered |

## Not Applicable to U6

| L1 requirement | Reason |
|---|---|
| PF §7a *Permission Grant*; §8a's authority rows; §8b intersection and re-broadening | No authority is evaluated at S3: renewal's required authority is the credential itself (PF §8a). U3, U4, U5, U7 |
| PF §7b *Envelope Fields*; O5 to O7 | No envelope at bootstrap or renewal (GAP-INT-008, L1-29) |
| PF FR-011 initiation; §8a *Revoke a credential*, *Revoke a logical agent* | Deferred (RA run-1 Q7). U6 builds the read and a test-only fixture only (D-AC-16) |
| PF FR-008 rotation and retirement | Absent from M1 (M1-FR-04); renewal already honours their independence (L1-06) |
| PF FR-013 retention and pruning | No pruning in M1 (U4) |
| PF FR-025's read; §8a *Read attribution records* | Absent from M1 |
| PF §7a *Logical Agent Registration*'s writes | U5's. U6 reads `state` and `sponsor` only (L1-04, L1-27) |
| ID §7a's human records; ID FR-019 to FR-021 | Refused by kind at S3, never read (L1-32); delegation out of M1 |

## PRD-Sourced Gaps

| Gap | Rows | Status |
|---|---|---|
| GAP-INT-008 (inherited) | L1-27, L1-29 | Open, soorma-prd#27. Worked around: no envelope on either operation; the record's operation states why |
| GAP-INT-009 (inherited) | L1-28 | Open, soorma-prd#28. Worked around: no record for the internal read |
| (none raised in U6) | — | Q1 to Q9 classified as technology |
