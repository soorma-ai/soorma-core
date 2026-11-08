# AI-DLC State Tracking

## Project Information
- **Project**: soorma-core: M1 walking skeleton (server side)
- **Project Type**: Greenfield
- **Start Date**: 2026-10-05T02:24:31Z
- **Milestone**: M1, Walking skeleton (from the slice brief; matches `aiprd-docs/build-sequence.md`)
- **Current Stage**: CONSTRUCTION, unit U2 `org-identity` (#5): **Construction Design PR gate: PENDING** (branch `dev`, PR to `main`; see `## PR Checkpoint State`). QA construction enrichment complete (62 cases; amendment A5 and the TC-OI-029 split at its review). Infrastructure Design APPROVED 2026-11-08T21:51:00Z (`construction/org-identity/infrastructure-design/`; Q1 to Q6 answered; SECURITY-03 finding resolved 2026-11-08T21:41:45Z by the user's decision, with the log-pseudonym amendment). NFR Design committed `5882ef8` and pushed; F-1 to F-3 posted on #7 (issuecomment-6727058030). NFR Design APPROVED 2026-11-08T21:00:25Z (`construction/org-identity/nfr-design/`; Q1 to Q4, all technology). NFR Requirements committed `95b3d53` and pushed. NFR Requirements APPROVED 2026-11-08T20:30:39Z (`construction/org-identity/nfr-requirements/`; Q1 to Q12, all technology; Q9 and Q10 conditions met by probes; Q6's condition checked at Code Generation). Functional Design committed `5f50704` and pushed; U4 obligations posted on #7 (issuecomment-6726146898). Functional Design APPROVED 2026-11-08T19:37:29Z (`construction/org-identity/functional-design/`; plan Q1 to Q12, all technology; no specification gap; U1 amendment A4). Session resumed 2026-11-08T18:39:49Z; re-intake not needed (brief unchanged at `0aad84a`, no new tags, every gap issue open); extension rules reloaded; Unit Initialization and the L1 gate's initial assessment done for U2. **Previous unit**: U1 `wire-contract` (#4) complete: Code Generation APPROVED 2026-11-08T07:53:50Z; soorma-core#12 merged to `main` 2026-11-08T07:52:11Z as `2b3a64d`, after its CI passed (dependency review included, once the user enabled the dependency graph); soorma-core#4 closed. **Next unit: U2 `org-identity` (#5), to be started in a new session.** Summary: `construction/wire-contract/code/code-summary.md`. Toolchain verified 2026-11-08T06:24:45Z (Node v26.13.0, pnpm 12.18.0); the earlier block was a stale session PATH. Construction Design PR gate APPROVED 2026-11-08T06:18:09Z (soorma-core#11 merged 2026-11-08T05:17:11Z, `15c475d`). Functional Design amended (A1, A2, A3) before the gate. QA construction enrichment complete. NFR Requirements approved 2026-11-08T04:34:32Z; NFR Design and Infrastructure Design skipped. Functional Design approved 2026-11-08T02:35:51Z. Inception complete; Inception PR gate APPROVED (soorma-core#2 merged 2026-11-02, `d348c34`)
- **Slice brief**: soorma-prd/backlog/m1-walking-skeleton.md (`soorma-core` column of *Repositories and sessions*)
- **Requirements depth**: Comprehensive (irreversible core assignments, security boundary, a contract other sessions consume)

## Workspace State
- **Existing Code**: No (README, licence, contributor documents, and `.github/` only)
- **Programming Languages**: None yet
- **Build System**: None yet
- **Project Structure**: Empty
- **Reverse Engineering Needed**: No
- **Workspace Root**: . (repo root: soorma-core)
- **Context-only repositories**: soorma-sdk (empty; consumes this initiative's wire contract), soorma-prd (PRDs and brief)

## Code Location Rules
- **Application Code**: . (repo root; NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/platform/m1-walking-skeleton/ only
- **Structure patterns**: See code-generation.md Critical Rules
- **Path Convention**: All paths are relative to repo root; never use absolute or machine-specific paths

## PRD Intake

- **Entry point**: slice brief
- **Slice brief**: soorma-prd/backlog/m1-walking-skeleton.md @ `0aad84a27c94d8f6d7064c312aaaa2e553d162dd` (Status: Ready)
- **Scope**: `soorma-core` column of *Repositories and sessions*
- **Coverage map**: inception/prd-intake/prd-coverage-map.md
- **Specification gaps**: inception/prd-intake/specification-gaps.md
- **Stages satisfied**: None fully. Requirements Analysis, User Stories, Application Design, and Units Generation are all Partial, across both PRDs
- **Intake approval**: run 1 approved (RA Q1, 2026-10-05T03:13:21Z). Run 2 approved (re-intake Q1, 2026-11-01T21:45:19Z)
- **ID note**: unqualified PRD IDs in artifacts dated before run 2 refer to **PF**. Qualify them in any artifact as it is next edited

### PRD: PF — platform-foundations

- **PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
- **Version**: 1.3
- **Built against**: `prd-platform-foundations-v1.3` (commit `80dd7c98e81702bb38dece9249372ea27b0555f9`)
- **Kind**: plane (declared since v1.2; run 1 inferred it and the user confirmed)
- **Status verified**: Approved (2026-09-10, via soorma-prd PR #4; amendments v1.2 via PR #19, v1.3 via PR #21)
- **Upstream check**: none declared
- **L1 sources**: PF §7a, PF §7b, PF §6, PF §8a, PF §8b, PF §9, PF §10, PF §11, PF §17, PF FR-025

### PRD: ID — identity

- **PRD**: soorma-prd/aiprd-docs/identity/requirements/prd.md
- **Version**: 1.0
- **Built against**: `prd-identity-v1.0` (commit `80dd7c98e81702bb38dece9249372ea27b0555f9`)
- **Kind**: plane (declared)
- **Status verified**: Approved (2026-10-26, via soorma-prd PR #21)
- **Upstream check**: declares PF @ `prd-platform-foundations-v1.3`; consistent with the brief
- **L1 sources**: ID §7a (Human Principal, Human Authentication Material, Organization Sign-In, Human Environment Credential), ID §6, ID §7b, ID §8a, ID §8b, ID §9, ID §10, ID §17, ID FR-001, ID FR-004

### Intake History

| Run | Date | Trigger | PRDs @ tags | Brief @ |
|---|---|---|---|---|
| 1 | 2026-10-05 | Initiative start | PF @ `prd-platform-foundations-v1.1` (`cef399f`) | not recorded (most likely `c1abc32`) |
| 2 | 2026-11-01 | Resume: legacy state format; no brief pin; brief's *Draws on* changed; #12, #14, #15 closed | PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0` | `0aad84a` |

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q10) |
| soorma Platform Invariants | Yes | Requirements Analysis (Q11). Scope inherited from PF §15 and ID §15: I1 to I11 all Addressed in both, none N/A. Invariants read at `prd-platform-foundations-v1.3` and `prd-identity-v1.0`; text identical at both tags (and at v1.1) |
| PR Checkpoint | Yes | Requirements Analysis (Q12). **Inception PR gate uses soorma-core#2** (dev → main); see `## PR Checkpoint State` |
| QA Test Cases | Yes | Requirements Analysis (Q13). Opted in — scope: comprehensive |
| JIRA Tickets | Yes, adapted: **GitHub issues on soorma-core instead of JIRA** | Requirements Analysis (Q14; clarification Q3). At the end of Inception, before the PR checkpoint: one tracking issue plus one sub-issue per unit. **No markdown ticket file**; issue numbers are recorded under `## Tickets` below |

## PR Checkpoint State

### Inception PR Gate
- **Status**: APPROVED
- **PR**: **soorma-core#2** (`dev` → `main`), by the user's instruction (2026-11-02): the existing PR is used, and its description updated per `pr-checkpoint.md` Section 4.2. No new PR or `aidlc/.../inception` branch
- **Branch**: `dev` (confirmed by that instruction)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/inception/working/pr-checkpoint-instructions.md
- **Created**: 2026-11-02T09:01:28Z
- **Approved**: 2026-11-02T16:37:12Z (user confirmed; #2 merged to `main` at 2026-11-02T16:36:27Z, merge commit `d348c34`)

### Construction Design PR Gate — wire-contract
- **Status**: APPROVED
- **PR**: **soorma-core#11** (`dev` → `main`), opened 2026-11-08 at the user's request
- **Branch**: `dev`, PR to `main` (confirmed by the user, 2026-11-08)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/wire-contract-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-08T05:02:21Z
- **Approved**: 2026-11-08T06:18:09Z (user confirmed; #11 merged to `main` at 2026-11-08T05:17:11Z, merge commit `15c475d`)

### Construction Design PR Gate — org-identity
- **Status**: PENDING
- **PR**: (being opened)
- **Branch**: `dev`, PR to `main` (confirmed by the user, 2026-11-08)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/org-identity-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-08T22:11:06Z
- **Approved**: —

## PRD Specification Gaps

Full entries: `inception/prd-intake/specification-gaps.md`.

| ID | Unit | Summary | Status | Raised Against | Resolved By | Issue |
|---|---|---|---|---|---|---|
| GAP-INT-001 | U2, U4 | Human principal identity and control-plane authentication (OB-4) | Resolved — answered elsewhere | PF @ `prd-platform-foundations-v1.1` | ID @ `prd-identity-v1.0` FR-001, FR-006, FR-009, FR-010, FR-022 | soorma-prd#12 |
| GAP-INT-002 | U4 | First human grant; how a sponsor obtains `agent:register` (OB-3, PF R-2) | Resolved — answered elsewhere | PF @ `prd-platform-foundations-v1.1` | ID @ `prd-identity-v1.0` FR-004, FR-007, FR-015 | soorma-prd#12 |
| GAP-INT-003 | U7, U1 | Event delivery guarantees (Event plane) | **Awaiting PRD: Event**. Worked around in M1 (live subscribers only; semantics stated as unspecified; pre-release contract) | PF @ `prd-platform-foundations-v1.1` | — | soorma-prd#13 |
| GAP-INT-004 | U3, U5 | Re-broadening evaluation rule (PF FR-017, I5) | Resolved — PRD amended. **Work-around comes out** | PF @ `prd-platform-foundations-v1.1` | PF @ `prd-platform-foundations-v1.3` FR-017, §8b *Re-broadening* (v1.2) | soorma-prd#14 |
| GAP-INT-005 | U5, U4 | Meaning of the sponsor's "grantable set" (PF FR-016) | Resolved — PRD amended | PF @ `prd-platform-foundations-v1.1` | PF @ `prd-platform-foundations-v1.3` FR-016, §8b *Sponsorship* (v1.2); ID @ `prd-identity-v1.0` FR-015 for `grant:human` | soorma-prd#14 (re-routed half: #12) |
| GAP-INT-006 | U4, U5 | Which permissions are *valid in E* (ID FR-015's ceiling); tenant-defined identifiers in core | Open: raised; worked around in M1 (plane-declared identifiers only; re-intake Q2, routing E) | ID @ `prd-identity-v1.0` | — | soorma-prd#24 |
| GAP-INT-007 | U3, U7 | Origin at an autonomous first hop: agent-asserted (PF §8b) or platform-stamped (PF §11, FR-015, §7b); found at User Stories | Open: raised; worked around in M1 (reject and stamp, M1-FR-01; routing E) | PF @ `prd-platform-foundations-v1.3` | — | soorma-prd#25 |
| GAP-INT-008 | U6, U1 | Do bootstrap and renewal carry an envelope (PF FR-001 vs §8a, §11); found at Application Design | Open: raised; worked around in M1 (neither carries an envelope; routing E) | PF @ `prd-platform-foundations-v1.3` | — | soorma-prd#27 |
| GAP-INT-009 | U6 | Does the internal revocation read produce an attribution record (PF FR-025 vs §8a); found at Units Generation | Open: raised; worked around (no record; routing E) | PF @ `prd-platform-foundations-v1.3` | — | soorma-prd#28 |

**Counts**: Open 4 (GAP-INT-006, 007, 008, 009; all worked around) · Awaiting PRD 1 (GAP-INT-003, worked around) · Resolved 4.

**Errata (not a gap)**: E-1, PF §17 and §4 counts. soorma-prd#15, closed. Corrected at PF v1.2.

## Tickets

GitHub issues on soorma-core (the jira-tickets extension, adapted), created 2026-11-02. No markdown ticket file.

| Ticket | Issue | Dependencies |
|---|---|---|
| Tracking issue: platform — m1-walking-skeleton | soorma-core#3 | — |
| U1 wire-contract | soorma-core#4 (sub-issue of #3) | None |
| U2 org-identity | soorma-core#5 | #4 |
| U3 authority-evaluation | soorma-core#6 | #4 |
| U4 env-human-access | soorma-core#7 | #4, #5, #6 |
| U5 agent-registration | soorma-core#8 | #4, #6, #7 |
| U6 agent-credentials | soorma-core#9 | #4, #7, #8 |
| U7 event-transport | soorma-core#10 | #4, #6, #7, #8, #9 |

## Deferred Questions

| ID | Question | Deferred To | Reason | Source | Status |
|---|---|---|---|---|---|

*None. PF OQ-1 to OQ-14 and ID OQ-1 to OQ-6 and P1-OQ-1 to P7-OQ-2 are all Answered at their tags, so none were imported.*

## Execution Plan Summary
*Approved at Workflow Planning (2026-11-02), with the user's edits. Full plan: `inception/working/execution-plan.md` (git-ignored).*
- **Risk**: High (security perimeter; irreversible core assignments; one-way contract, pre-release in M1)
- **Stages to execute**: Application Design (comprehensive); Units Generation (plane-face units); tickets as GitHub issues; QA inception test specs; Inception PR gate on soorma-core#2; Construction Initialization; per unit, Functional Design, NFR Requirements, NFR Design, and Infrastructure Design (each may skip for a unit), then Code Generation; Build and Test
- **Stages skipped**: Reverse Engineering (greenfield)
- **soorma-sdk coordination**, in two steps: (a) the contract **design** is published when soorma-core#2 merges, and soorma-sdk's Inception can run against it; (b) the **schema** (M1-TECH-02) is published once Code Generation produces it, at a pinnable tag on `main`, and soorma-sdk's Construction pins that tag
- **Schema production (decided at Units Generation, Q1 B)**: U1 `wire-contract` produces the cross-surface parts; each surface unit adds its own operations; the schema is tagged after U7's Code Generation

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection (greenfield)
- [x] PRD Intake (run 1 approved at RA Q1; run 2 approved at re-intake Q1, 2026-11-01)
- [ ] Reverse Engineering: SKIPPED (greenfield)
- [x] Requirements Analysis (run 1 approved 2026-10-06; re-opened by re-intake run 2; run 2 approved 2026-11-02)
- [x] User Stories (minimal depth; approved 2026-11-02)
- [x] Workflow Planning (approved 2026-11-02)
- [x] Application Design (approved 2026-11-02)
- [x] Units Generation (7 units; approved 2026-11-02, once soorma-prd#28 was open)
- [x] Tickets as GitHub issues (soorma-core#3, with sub-issues #4 to #10)
- [x] QA inception test specs (150 test cases, 7 units, comprehensive; `inception/test-cases/`)
- [x] Inception PR gate (#2): **APPROVED** 2026-11-02T16:37:12Z; merged as `d348c34`. Step (a) of contract publication is done: the contract design is on `main`

### 🟢 CONSTRUCTION PHASE
- [x] Construction Phase Initialization (2026-11-08): rules loaded for all five enabled extensions; prd-gap-classification.md active
- **Unit order**: U1 `wire-contract` (#4) first, chosen by the user 2026-11-03T04:47:01Z (pr-checkpoint.md Section 4.7). The planned sequence U1 → U7 follows
- **Current unit**: U1 `wire-contract`. Unit Initialization and the L1 gate's initial assessment done (2026-11-08)
  - [x] Functional Design: **APPROVED** 2026-11-08T02:35:51Z (`construction/wire-contract/functional-design/`: domain-entities, business-rules, business-logic-model, l1-coverage-matrix, invariant-coverage-matrix; committed `7f5249a`). Q6 answered as technology, so no U1 specification gap. `component-methods.md` `validateDraft` and `stamp` corrected
  - [x] NFR Requirements: **APPROVED** 2026-11-08T04:34:32Z (`construction/wire-contract/nfr-requirements/`: nfr-requirements, tech-stack-decisions)
  - [x] NFR Design: **SKIPPED** (no runtime patterns in U1); Infrastructure Design: **SKIPPED** (nothing deployed; CI designed at NFR Requirements T-14). Per NFR plan Q11 A, recorded 2026-11-08T04:34:32Z
  - [x] QA construction enrichment: **COMPLETE** 2026-11-08 (`inception/test-cases/wire-contract/`: TC-WC-001 to 011 enriched in place, TC-WC-012 to 041 added; 41 cases). L1 and invariant matrices now cite TC IDs for every former *enrichment* placeholder
  - [x] Functional Design amendments A1 (`traceContext` open in the envelope, closed in the draft), A2 (Problem `type` and `instance` carry no pattern) and A3 (the received Problem schema requires no field; soorma-core always emits five fields with the `urn:soorma:` forms), 2026-11-08. Forward obligation to U3 (soorma-core#6): BR-ERR-08, recorded on #6 (issuecomment-6717621632)
  - [x] Construction Design PR gate: **APPROVED** 2026-11-08T06:18:09Z; soorma-core#11 merged as `15c475d`, and `origin/main` merged back into `dev`
  - [x] Code Generation: **APPROVED** 2026-11-08T07:53:50Z. Part 1 approved (revision 2, Q-CG-1 A); Part 2 complete. PR soorma-core#12 merged as `2b3a64d` (2026-11-08T07:52:11Z); CI green; `pnpm run check:github` passes. soorma-core#4 closed. D-CG-16 accepted with the approval. Q-CG-2 answered A. Commits `2cdea76`, `b0c3411`, `d87bac6`, `882b0fe`, and Group 5. Local run: every command passes, 222 tests, audit clean. L1 matrix: 32 rows Implemented, 0 Missing; invariant matrix: I1 to I10 Implemented, I11 N/A. Decisions taken at generation: D-CG-15 (schema layout), D-CG-16 (`minimatch` override, flagged for review) (`construction/working/wire-contract-code-generation-plan.md`: 21 steps, decisions D-CG-01 to 14). Revision 1 changes requested 2026-11-08; NFR-WC-19's engines half amended (`^26.13.0`); TC-WC-030, 031, 039, 041 updated. Unit Initialization and the L1 gate re-run 2026-11-08 (0 Missing). The earlier toolchain block (06:18:09Z) was a stale session PATH; verified Node v26.13.0 and pnpm 12.18.0 at 06:24:45Z
- **Current unit**: U2 `org-identity` (#5). Construction Phase Initialization re-run on resume (2026-11-08T18:39:49Z): rules loaded for all five enabled extensions; prd-gap-classification.md active; invariant text identical at both tags. Unit Initialization and the L1 gate's initial assessment done (applicable: ID §7a Human Principal, Human Authentication Material, Organization Sign-In; ID §6; ID FR-001, 004 (organization half), 006 to 009, 011 (sign-in and material half); ID §8a, §8b (sign-in column), §10; ID §7b; PF §6, §12. Six non-applicable, 0 Missing)
  - [x] Functional Design: **APPROVED** 2026-11-08T19:37:29Z; review round 1 applied (header refusal as `malformed_request`, D-OI-26, with U1 amendment A4; Failed Attempt written off the response path, D-OI-27; step 7 scoped to `authenticate`; the K/K+P compromise residual accepted; U4 fail-closed obligation); then the Code Generation obligation to apply U1 amendment A4 (business-rules §14) and TC-WC-024, 025 updated for A4 (domain-entities, business-rules (D-OI-01 to 27), business-logic-model, l1-coverage-matrix (32 Covered, 11 N/A, 0 Missing), invariant-coverage-matrix (I1 to I10 Covered, I11 N/A)). Q1 to Q12 answered, all technology; no specification gap. Contract changes: four new error codes (403 `authentication_failed`, 403 `second_factor_enrollment_required`, 400 `secret_rejected`, 403 `second_factor_not_confirmed`), `too_many_attempts` widened, `org-gateway.openapi.yaml`, two shared definitions; all compatible. Forward obligations to U4 posted on #7 at approval
  - [x] NFR Requirements: **APPROVED** 2026-11-08T20:30:39Z, after two review edits (SECURITY-14 status: not applicable in M1, by the user's decision; the unknown-identifier flood added to the accepted residual), with the Code Generation obligation to mark the derived breached-list file binary in .gitattributes. Artifacts (nfr-requirements NFR-OI-01 to 31; tech-stack-decisions T-OI-01 to 12: NestJS 12.3.2 on Fastify 5.12.7, jose 6.2.14 with the RFC 9864 `Ed25519` algorithm, pg 8.23.1 on PostgreSQL 18, Node built-in Argon2id, TOTP, SecLists top 1M; all past the 7-day cooldown; no SWC). User's SECURITY-14 decision recorded (NFR-OI-24). Accepted residual: allowance exhaustion (Q2). NFR Design and Infrastructure Design both run
  - [x] NFR Design: **APPROVED** 2026-11-08T21:00:25Z; artifacts (nfr-design-patterns P-01 to P-17; logical-components; records R-1 to R-3; U4 obligations F-1 to F-3 posted on #7; invariant matrix I3 target updated)
  - [x] Infrastructure Design: **APPROVED** 2026-11-08T21:51:00Z; artifacts generated (infrastructure-design, deployment-architecture, construction/shared-infrastructure.md; D-ID-OI-01 to 10; NFR-OI-18 and 31, P-07, P-15, logical components amended). SECURITY-03 finding resolved by the user's decision (2026-11-08T21:41:45Z): the centralized log service not applicable in M1, carried to Build and Test and the first hosted deployment; logs carry a keyed pseudonym (HMAC-SHA-256, a dedicated log-pseudonym key), never a human identifier (NFR-OI-22, 23, BR-CFG-04, BR-RF-05, P-02, P-17 amended). Correction at approval: each environment has its own log-pseudonym key, never the organization's (shared-infrastructure.md, Logs). U4 obligations (per-environment network, per-environment log-pseudonym key) posted on #7
  - [x] QA construction enrichment: **COMPLETE** 2026-11-08T21:56:07Z (`inception/test-cases/org-identity/`: 62 cases; every QA enrichment marker in the L1 and invariant matrices replaced by TC IDs). At its review (2026-11-08T22:11:06Z): Functional Design amendment A5 (BR-K-07 reason `context_word`; `reason` an open enumeration; TC-OI-042 updated); TC-OI-029 made structural and deterministic, and TC-OI-062 added as a reported Build and Test timing measurement, not a gate (sources: functional-design/, nfr-requirements/, nfr-design/, infrastructure-design/, by the user's instruction; tooling finding F38 not yet applied to the rule)
  - [ ] Construction Design PR gate: **PENDING** (2026-11-08T22:11:06Z); branch `dev`, PR to `main` (confirmed by the user, 2026-11-08T21:51:00Z)
- [ ] Per unit: Functional Design, NFR Requirements, NFR Design, Infrastructure Design (EXECUTE; may skip per unit), Code Generation (EXECUTE)
- [ ] Build and Test: EXECUTE

### 🟡 OPERATIONS PHASE
- [ ] Operations: PLACEHOLDER

**Session stop point**: U1 `wire-contract` COMPLETE (Code Generation approved; #12 merged as
`2b3a64d`; #4 closed; `origin/main` merged back into `dev`). Next: U2 `org-identity` (#5), in a
new session, starting with Unit Initialization (extension rules, the L1 gate) and re-checking
`node --version` (26.13.0) and `pnpm --version` (12.18.0). Build and Test comes after all units
and uses U1's verification (CI on #12, `pnpm run check:github`). U1's inherited gaps: GAP-INT-003
and GAP-INT-008 (work-arounds). Forward obligations: BR-ERR-08 to U3 (soorma-core#6); D-CG-05 to
U3's NFR Requirements (the runtime regex engine for Ajv).
