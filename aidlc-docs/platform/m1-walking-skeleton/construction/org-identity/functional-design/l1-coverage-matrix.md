# L1 Coverage Matrix: U2 `org-identity`

**Sources** (registered in `aidlc-state.md` `## PRD Intake`, each read at its tag):
- ID: soorma-prd/aiprd-docs/identity/requirements/prd.md @ `prd-identity-v1.0`, the main
  source for this unit
- PF: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`

**Status values**: `Covered` (design traced; implementation and verification targets set) ·
`N/A` (with a reason) · `Missing` (blocking). Code Generation moves rows to `Implemented`;
Build and Test moves them to `Verified`.

**Verification targets**: `TC-OI-001` to `025` are the inception specs; `TC-OI-026` to `061`
were added by the QA construction enrichment (2026-11-08), which replaced every *QA
enrichment* marker below with a test-case ID.

**Result**: 32 applicable rows, all `Covered`. 11 `N/A`. **0 `Missing`.**

---

## Applicable to U2

| # | L1 requirement | Design coverage | Implementation target | Verification target | Status |
|---|---|---|---|---|---|
| L1-01 | ID FR-001, §6: a human principal is organization-scoped; its identifier is unique within the organization, composed with it, never allocated globally | BR-HP-01; D-OI-01, D-OI-21 | P10 principal record keyed on `{organization, principal}`; `HumanPrincipalReference*` in `components.openapi.yaml` | TC-OI-018 | Covered |
| L1-02 | ID FR-001, §7a: lifecycle `pending → active` (M1's states) | BR-HP-02; BR-FA-02 | P10 state transition at first authentication | TC-OI-001, TC-OI-002 | Covered |
| L1-03 | ID FR-001: **never deleted, never pruned** | BR-HP-03; D-OI-08 | P10 has no delete path; no S1 operation removes a principal | TC-OI-022, TC-OI-051 | Covered |
| L1-04 | ID §7a Human Principal: registered-at, registered-by | BR-HP-04; BR-CFG-05 | P10 `ensureFirstAdmin` | TC-OI-001 | Covered |
| L1-05 | ID FR-004: organization, project, and environment identity **configured, never inferred** | BR-CFG-01; D-OI-09 | P9 `loadOrganization` | TC-OI-019 | Covered |
| L1-06 | ID FR-004: an environment's configuration names its first Admin, who is registered with enrollment material **if absent** | BR-CFG-02, 03, 05; D-OI-12 | P9; P10 `ensureFirstAdmin` | TC-OI-001, TC-OI-017 | Covered |
| L1-07 | ID FR-004, FR-007: configuration never re-registers or re-enrolls an existing principal (no reset by redeploy) | BR-CFG-04 | P9 start-up; the "ignored" log | TC-OI-017, TC-OI-049 | Covered |
| L1-08 | ID FR-006: classes K and P; core accepts **K, or K + P**; once P is enrolled, sign-in needs both | BR-P-01, 07 | P10 required-class check; P6 | TC-OI-003, TC-OI-004, TC-OI-016 | Covered |
| L1-09 | ID FR-006: the organization's configuration may require P for every human; refused until enrolled | BR-CFG-06; BR-P-02; BR-SI-05; BR-FA-05 | P9 setting; P10 | TC-OI-014, TC-OI-035, TC-OI-040 | Covered |
| L1-10 | M1-TECH-07 constraint 2 (from ID FR-011): a human for whom P is required can enroll P **without a sign-in, by presenting K** | BR-P-03, 04, 05; D-OI-14 | S1 `changeMaterial` (`beginSecondFactor`, `confirmSecondFactor`) | TC-OI-008 | Covered |
| L1-11 | ID FR-006, §6: material held and verified **at the organization level only**; K only in a form that can verify | BR-K-08; BR-CFG-02, 09; BR-SEAM-02 | P10, P6 at the organization level; the org store | TC-OI-043, TC-OI-048 | Covered |
| L1-12 | ID §7a Human Authentication Material: principal, class, state, established-at, established-by; `enrollment → active → retired` | Domain entities; BR-REC-02; business-logic-model §3 | P10 material records | TC-OI-021, TC-OI-007, TC-OI-037 | Covered |
| L1-13 | ID FR-006, FR-027 (external types out): class X absent | D-OI-10; BR-SEAM-03 | Closed request bodies | TC-OI-025 | Covered |
| L1-14 | ID FR-007: enrollment material is **single use**, replaced by the human on first authentication | BR-FA-01 to 03; D-OI-04 | P10 atomic transition | TC-OI-002, TC-OI-009, TC-OI-034 | Covered |
| L1-15 | ID FR-007: the deployer never holds a working credential | BR-CFG-02, 09; D-OI-19; misuse cases | P9; enrollment material is single use and replaced | TC-OI-009, TC-OI-017; Infrastructure Design (delivery, M1-TECH-06) | Covered |
| L1-16 | ID FR-008: sign-in and first authentication are unauthenticated surfaces; failures recorded against the principal; volume bounded per principal | BR-AB-01 to 07; BR-REC-03 | P8 `admit`, `recordFailure` | TC-OI-010, TC-OI-011 | Covered |
| L1-17 | ID FR-009: a short-lived sign-in asserting subject, organization, time, and classes used | BR-SI-01, 02, 04 | P10 `issueSignIn` | TC-OI-003, TC-OI-004 | Covered |
| L1-18 | ID §7a Organization Sign-In: subject, organization, authenticated-at, classes, expiry, state; `live → ended` | Domain entities; BR-REC-01; BR-SI-06 | P10 sign-in records | TC-OI-006, TC-OI-021 | Covered |
| L1-19 | ID FR-009, PF §6: environments hold **verify-only** material, never material that can mint | BR-SI-03; BR-INT-03 | Internal interface `verifyOnlyMaterial` | TC-OI-046 | Covered |
| L1-20 | ID FR-009: the organization level sits outside every environment, on no per-request path | BR-INT-01, 08; D-OI-22 | Separate deployable and internal listener | TC-OI-045, TC-OI-047; M1-NFR-08 at U6, U7 | Covered |
| L1-21 | ID FR-009: the sign-in is refused at every environment's perimeter except E's issuance | BR-SI-02, 08 (asserts no environment; `soorma_si_` kind) | U2: the token's assertions and kind. Refusal: U4 (S2), U6 (S3), U7 (S4) | U2: TC-OI-044. The refusals: U4, U6, U7 test cases | Covered (U2's part) |
| L1-22 | ID FR-011: renew and end one's own sign-in; change one's own material by presenting the current material | BR-SI-04, 06; BR-MC-01 to 06; D-OI-15 | S1 `renewSignIn`, `endSignIn`, `changeMaterial` | TC-OI-005, TC-OI-006, TC-OI-007, TC-OI-015 | Covered |
| L1-23 | ID §8a: *Authenticate* requires valid material, K or K + P where enrolled or required; self-service requires *self* | BR-P-01, 02; BR-MC-06 | P10 | TC-OI-003, TC-OI-014, TC-OI-016 | Covered |
| L1-24 | ID §8b, the sign-in column: O1 to O3 apply; O9, O10 apply; O5 to O7 N/A (no envelope) | D-OI-05, 06; business-logic-model §1 | P1 sign-in checks at S1 | TC-OI-020, TC-OI-024, TC-OI-006, TC-OI-027 | Covered |
| L1-25 | ID FR-022, PF FR-001 v1.3: **a direct human operation carries no envelope** | `org-gateway.openapi.yaml` (no draft); BR-OP-01 | S1 operations | TC-OI-023 | Covered |
| L1-26 | ID FR-023, §8b matrix: the organization sign-in is *reached* at the organization's operations; other presenters are refused there | D-OI-05, D-OI-26; BR-RF-06 | P1 `classifyPresenter` at S1 | TC-OI-026, TC-OI-027 | Covered |
| L1-27 | ID §6 isolation: authentication material never crosses into any environment | BR-CFG-02; D-OI-12 | P9: the environment part has no material field | TC-OI-048 | Covered |
| L1-28 | ID §7b *Recoverability*: a human actor is the principal and the credential or sign-in presented; no origin mode | BR-REC-04 | P10 records | TC-OI-021 | Covered |
| L1-29 | ID §7b *Compatibility Policy*: a new material class or credential attribute is compatible; withdrawing a class is breaking | Contract changes (business-rules §10); D-OI-14 (`type`-discriminated P) | `contract/CHANGELOG.md`; U1's compatibility test | TC-OI-023; U1 compatibility test over `org-gateway.openapi.yaml` | Covered |
| L1-30 | ID §10 *Failure Modes*: over the bound, refused and recorded; second factor required, refused until enrolled; enrollment reuse, refused | BR-AB-02, 07; BR-P-02; BR-FA-03 | P8; P10 | TC-OI-011, TC-OI-014, TC-OI-009 | Covered |
| L1-31 | ID §10 *NFR Profile*: highest durability for the principal record; interactive sign-in; read-your-writes; sign-in and first authentication bounded | BR-REC-05; carried to NFR Requirements (business-rules §14) | U2 NFR Requirements and NFR Design | U2 NFR Requirements targets | Covered (carried) |
| L1-32 | PF §12 v1.3, ID FR-027, ID §12: the identity-resolution seam's human half returns a human principal reference; **decides identity, never authority**; single use and the human record stay behind no seam | BR-SEAM-01 to 03; D-OI-11 | `seams/identity-resolution` (types); P6 | TC-OI-025, TC-OI-060 | Covered |

## Not Applicable to U2

| L1 requirement | Reason |
|---|---|
| ID §7a Human Environment Credential; ID FR-010 | Environment-scoped; U4 `env-human-access`. U2 supplies `signInStatus` and verify-only material |
| ID FR-004, the first grant (`grant:human`, `human:manage`) | An environment record; U4 applies it |
| ID FR-013, FR-015; PF §8b human-only class | Grants and the ceiling; U4 and U5 |
| ID FR-002, FR-003 | Registration of further humans; suspension and deactivation. Out of M1 (requirements, *Absent from M1*) |
| ID FR-005, the setting by API | Out of M1. The P requirement is set by configuration only (BR-CFG-06) |
| ID FR-012 | Acting on another's credentials or material. Out of M1 |
| ID FR-014, FR-017, FR-018 | Coverage, reading principals, organization-level attribution. Out of M1; M1 performs no organization-wide operation |
| ID §7a Delegation Credential; ID FR-019 to FR-021 | Delegation is out of M1 |
| ID §7a Configured Identity Source; ID FR-024 | Out of M1 |
| ID §7a Grant Mapping; ID FR-025 | Out of M1 |
| ID §7a Organization-Level Attribution | ID FR-018 out (D-OI-07) |

## PRD-Sourced Gaps

None. No applicable row is `Missing`, and no answer in the Functional Design plan was
classified as specification.
