# AI-DLC State Tracking

## Project Information
- **Project**: soorma-core: M1 walking skeleton (server side)
- **Project Type**: Greenfield
- **Start Date**: 2026-10-05T02:24:31Z
- **Milestone**: M1, Walking skeleton (from the slice brief; matches `aiprd-docs/build-sequence.md`)
- **Current Stage**: CONSTRUCTION. **Current unit: U6 `agent-credentials` (soorma-core#9). Functional Design APPROVED 2026-11-12T03:59:45Z; NFR Requirements APPROVED 2026-11-12T04:19:07Z; NFR Design APPROVED 2026-11-12T04:42:09Z; Infrastructure Design APPROVED 2026-11-12T05:09:55Z; QA construction enrichment APPROVED 2026-11-12T06:01:35Z; Construction Design PR gate PENDING**. U1 to U5 complete (U5: soorma-core#21 merged as `7f8d872`; #8 open until Build and Test). Stage history is under *Stage Progress*
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
- **Status**: APPROVED
- **PR**: **soorma-core#13** (`dev` → `main`), opened 2026-11-08 at the user's request
- **Branch**: `dev`, PR to `main` (confirmed by the user, 2026-11-08)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/org-identity-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-08T22:11:06Z
- **Approved**: 2026-11-08T22:27:46Z (user confirmed; #13 merged to `main` at 2026-11-08T22:26:42Z, merge commit `27619c4`)

### Construction Design PR Gate — authority-evaluation
- **Status**: APPROVED
- **PR**: **soorma-core#16** (`dev` → `main`), opened 2026-11-10 at the user's request
- **Branch**: `dev`, PR to `main` (confirmed by the user, 2026-11-10)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/authority-evaluation-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-10T16:07:33Z
- **Changes requested**: 2026-11-10T20:19:53Z, one fix: the entry point named `createEnvelopeAdmission(dependencies).admit(request)` throughout (formerly `admitEnvelopeRequest` in Functional Design and `component-methods.md`); pushed to #16
- **Approved**: 2026-11-10T21:31:28Z (the user confirmed; #16 merged 2026-11-10T21:30:40Z as fbb567c)

### Construction Design PR Gate — env-human-access
- **Status**: APPROVED
- **PR**: **soorma-core#18** (`dev` → `main`), opened 2026-11-11 at the user's request; checks green at 2026-11-11 (head `7d33d3d`)
- **Branch**: `dev`, PR to `main` (confirmed by the user, 2026-11-11)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/env-human-access-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-11T07:09:43Z
- **Approved**: 2026-11-11T07:17:28Z (the user confirmed; #18 merged 2026-11-11T07:16:59Z as 1a19082)

### Construction Design PR Gate — agent-registration
- **Status**: APPROVED
- **PR**: **soorma-core#20** (`dev` → `main`), opened 2026-11-12 at the user's request
- **Branch**: `dev`, PR to `main` (confirmed by the user, 2026-11-12)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/agent-registration-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-12T00:35:04Z
- **Approved**: 2026-11-12T00:46:08Z (the user confirmed; #20 merged 2026-11-12T00:44:32Z as `1903711`; checks green at `eb9ddb8`)

### Construction Design PR Gate — agent-credentials
- **Status**: PENDING
- **PR**: opened 2026-11-12T06:02:43Z (`dev` → `main`), Refs #9, #3
- **Branch**: `dev`, PR to `main` (the user's instruction, 2026-11-12, as for U1 to U5)
- **Instructions**: aidlc-docs/platform/m1-walking-skeleton/construction/working/agent-credentials-design-pr-checkpoint-instructions.md
- **Created**: 2026-11-12T06:02:43Z
- **Approved**: —

## PRD Specification Gaps

Full entries: `inception/prd-intake/specification-gaps.md` (GAP-INT); `construction/authority-evaluation/prd-gaps/specification-gaps.md` (GAP-AE); `construction/env-human-access/prd-gaps/specification-gaps.md` (GAP-EHA).

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
| GAP-AE-001 | U3, U7 | Origin for a forwarded autonomous envelope when the presenter has not declared autonomy (PF O12 vs FR-015, §8b, §11; §8b's forwarded rows give `delegated`); found at U3 Functional Design | Open: raised; worked around in M1 (deny under O12; routing A) | PF @ `prd-platform-foundations-v1.3` | — | soorma-prd#30 |
| GAP-EHA-001 | U4 | Whether ending a sign-in refuses the environment credentials issued from it (ID FR-010 vs FR-003, FR-011, §7a, §8b); found at U4 Functional Design (U2 forward obligation 1) | Resolved — clarified, no PRD change (the user's decision, plan Q1 D: R2, renewal only; R1 contradicts ID FR-009, §9, §10, §18 and U2 BR-INT-08). Not raised | ID @ `prd-identity-v1.0` | The user's decision, 2026-11-11T03:59:19Z (D-EHA-01) | — |

**Counts**: Open 5 (GAP-INT-006, 007, 008, 009, GAP-AE-001; all worked around) · Awaiting PRD 1 (GAP-INT-003, worked around) · Resolved 5 (GAP-INT-001, 002, 004, 005, GAP-EHA-001).

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
  - [x] Construction Design PR gate: **APPROVED** 2026-11-08T22:27:46Z; soorma-core#13 merged as `27619c4`. Opened (2026-11-08T22:11:06Z); branch `dev`, PR to `main` (confirmed by the user, 2026-11-08T21:51:00Z)
  - [x] Code Generation: **APPROVED** 2026-11-09T13:24:27Z. soorma-core#14 merged as `e61c620`; CI green on Linux (build, check, and test; image, image secret scan, and stack smoke test; dependency review). Part 1 approved 2026-11-09T00:54:48Z (revision 3: amendments 1 and 2); Q-CG-1 A, Q-CG-2 A, Q-CG-3 B (SecLists `xato-net-10-million-passwords-1000000.txt` at `00f80ec`), Q-CG-4 B (the per-level secrets-init container; shared-infrastructure.md *Secrets* and Infrastructure Design §3, §7 amended). Commits `4089286`, `5ebcb9b`, `42a293f`, `dfa6c97`, `032b718`, `787b3be`, `9beb42c`, then the review changes `4ddf535` (the missing-version refusal and the bare 404 written into the contract) and `8e75f2b` (secrets-init). 456 tests; the stack smoke test 22 checks; L1 matrix 32 rows Implemented, 0 Missing; invariants I1 to I10 Implemented, I11 N/A. Summary: `construction/org-identity/code/code-summary.md`
- **Unit U2 `org-identity` (#5): COMPLETE** 2026-11-09T13:24:27Z
- **Current unit**: U3 `authority-evaluation` (#6). Session resumed 2026-11-09T13:57:36Z: re-intake check clean (brief unchanged at `0aad84a`; no new PF or ID tag; soorma-prd#13, #24, #25, #27, #28 open). Construction Phase Initialization re-run: rules loaded for all five enabled extensions; prd-gap-classification.md active; invariant text identical at both tags. Unit Initialization and the L1 gate's initial assessment done (0 Missing; one case to classify at Functional Design: O12 against FR-015 for a non-declaring agent forwarding an autonomous envelope)
  - [x] Functional Design: **APPROVED** 2026-11-10T07:43:41Z (presented 2026-11-10T06:51:35Z). Plan answered 2026-11-10T06:40:00Z: Q1 specification, **GAP-AE-001** raised as soorma-prd#30 (routing A; deny built meanwhile, D-AE-01); Q2 to Q6 technology, all A (Q5 as corrected: U1 amendment A6); P-01 to P-11 accepted (D-AE-07 to 17). Artifacts: domain-entities, business-rules (D-AE-01 to 26; BR-IN, VR, DV, FX, CD, OR, AU, ST, RF, SEAM, PE), business-logic-model, l1-coverage-matrix (38 Covered, 4 on the GAP-AE-001 work-around and 1 on GAP-INT-007's; 17 N/A; 0 Missing), invariant-coverage-matrix (I1 to I10 Covered, I11 N/A). U1 amendment A6 recorded in U1 business-rules; Application Design correction notes (components.md, component-methods.md). Contract changes for U3's Code Generation (business-rules §13). D-AE-18, 19, 23 accepted as written. At approval, the user added a U7 obligation (S4's step-1 body limit admits a maximum-size forwarding draft; floor set at U7's NFR Requirements; a test). Forward obligations (§16) posted on #7 to #10. Next-stage assessment: NFR Requirements execute, NFR Design execute, Infrastructure Design skip (no deployable; sealing-material provisioning to U7)
  - [x] NFR Requirements: **APPROVED** 2026-11-10T14:56:01Z (presented 2026-11-10T14:40:41Z). Q1 to Q7 answered 2026-11-10 (all technology; Q4 B as the user specified: batched reads plus a bounded cache of agent standing sets and Registration Views, TTL = the one propagation bound, failures never cached); P-NFR-01 to 07 accepted. Artifacts: nfr-requirements (NFR-AE-01 to 23), tech-stack-decisions (T-AE-01 to 06; no new dependency). At approval: NFR-AE-04, 11 to 14 accepted; NFR-AE-19's depth test fixed at a 1 MiB raw body (U7's edge test uses its actual limit); BR-FX-07 and `jcs_invalid` added to Functional Design as a consistency fix. Obligations posted on #7, #9, #10. Next: NFR Design run; Infrastructure Design skip (key ring and bound delivered at U7's Infrastructure Design)
  - [x] NFR Design: **APPROVED** 2026-11-10T15:40:14Z (presented 2026-11-10T15:30:09Z). Q1 to Q4 answered 2026-11-10, all A (Q3 with the user's byte-vector and seed-decryption condition on the U2 swap); P-ND-01 to 06, 08 accepted; P-ND-07 replaced by the user's agent-facts design (one port, one batched all-or-nothing read at the start of step 9, one caching decorator, humans bypass). Artifacts: nfr-design-patterns (NP-01 to 08), logical-components (new `packages/jcs`). Consistency fixes in Functional Design and NFR Requirements, marked in place. At approval: NP-02 matched to U2 exactly (sealKeys { current, keys: [{ id, secret }] }, base64url 256-bit secrets via SecretReader.key); NP-04 TTL from read issue; NP-07 own-data-property copy with a __proto__ test. Obligations posted on #7, #8, #10
  - [x] Infrastructure Design: **SKIPPED** 2026-11-10T15:40:14Z (no deployable; key ring and propagation bound delivered at U7's Infrastructure Design)
  - [x] QA construction enrichment: **APPROVED** 2026-11-10T16:07:33Z (generated 2026-11-10T15:46:05Z) (`inception/test-cases/authority-evaluation/`: 40 cases; TC-AE-001 to 022 enriched in place, TC-AE-023 to 040 added; `enrichment-delta.md`; every QA enrichment marker in the L1 and invariant matrices replaced by TC IDs). Sources: functional-design/, nfr-requirements/ (by the user's instruction at the review, F38, as for U1 and U2), nfr-design/. At the review: TC-AE-040 added (NFR-AE-07 p99, reported, modelled on TC-OI-062); TC-AE-034, 039 gained NFR-AE-03, 10, 22, 23 steps; TC-AE-006 retitled "decides containment, never composition"
  - [x] Construction Design PR gate: **APPROVED** 2026-11-10T21:31:28Z (opened 2026-11-10T16:07:33Z as soorma-core#16, `dev` → `main`; one change requested 2026-11-10T20:19:53Z, the entry point named `createEnvelopeAdmission(dependencies).admit(request)` throughout, fixed in `1a44021`; merged 2026-11-10T21:30:40Z as `fbb567c`)
  - [x] Code Generation: **APPROVED** 2026-11-11T02:39:10Z. soorma-core#17 merged as `a9aa74b` (2026-11-11T02:38:46Z); CI green at `cad1772` (build, check, and test; image, image secret scan, and stack smoke test; dependency review). Plan APPROVED 2026-11-10T21:53:41Z (two amendments; Q-CG-AE-1 A). Part 2 generated 2026-11-10T22:31:47Z: Steps 0 to 23 on `dev` (`4821788`, `8d90404` the U2 guard alone, `626ed4b` the swap with the guard unchanged, `ef7c392`, `90dc1fd`, `6508782`, `b6a59c5`, and Group 7); code-review PR **soorma-core#17** from `dev` to `main` (not merged). L1: 38 rows Implemented; I1 to I10 Implemented. Local run: 766 passed, 2 skipped; every check passes; `pnpm audit` clean. TC-AE-040 reported only. **Request Changes 2026-11-11T02:25:14Z**: (1) the S1 image copies `packages/jcs` (#17's image check), and the gate builds the image for a group reaching S1's dependencies; (2) an unresolved upstream agent is the empty set and evaluation continues (D-AE-09 consistency fix; TC-AE-016 step 2; the first build missed stop condition 2); (3) `errors[]` at most 10 (D-AE-18 consistency fix; TC-AE-029 step 5). Local run after: 771 passed, 2 skipped; image builds. Fixes committed as `cad1772`
  - **Standing note (NFR-AE-16)**: no M1 operation changes a standing set, re-broadening declaration, or autonomy declared, or suspends or retires an agent, so U3's term cache cannot serve stale data in M1. **The unit that first adds such an operation must account for the cache's staleness window** (up to the propagation bound)
- **Current unit**: U4 `env-human-access` (#7). Session resumed 2026-11-11T03:43:04Z: re-intake check clean (brief unchanged at `0aad84a`; no new PF or ID tag; soorma-prd#13, #24, #25, #27, #28, #30 open). Construction Phase Initialization re-run: rules loaded for all five enabled extensions; prd-gap-classification.md active; invariant text identical at both tags. Unit Initialization and the L1 gate's initial assessment done (0 Missing; one case to classify at Functional Design: ID FR-010, whether ending a sign-in refuses the environment credentials issued from it)
  - [x] Functional Design: **APPROVED** 2026-11-11T04:17:24Z (presented 2026-11-11T04:08:50Z). At approval: D-EHA-23 accepted (`principalExists` is `grantToHuman`'s own lookup, not a per-request freshness check), and its consequence added to §16 as an accepted residual (during an organization-level outage, issuance, renewal, and `grantToHuman` are `unavailable`; ending and O1 to O4 unaffected), with a Build and Test obligation to show it with S1 stopped; D-EHA-24 to 31 accepted as written. Plan answered 2026-11-11T03:59:19Z: Q1 D (specification, **GAP-EHA-001 Resolved — clarified, no PRD change**: R2, renewal only; SECURITY-12 reading: ending the environment credential is its own logout); Q2 A (**U2 amendment A7**, `signInStatus` with the current expiry and the principal's state); Q3 A; Q4 A plus the resolved sponsor and the re-broadening outcome; Q5 A (`unknown_principal`); Q6 A (`unknown_permission`); Q7 A plus at most one configuration grant under concurrent start-ups (a uniqueness constraint, tested); P-01 to P-15 accepted. Artifacts: domain-entities, business-rules (D-EHA-01 to 31), business-logic-model, l1-coverage-matrix (33 Covered, 20 N/A, 0 Missing), invariant-coverage-matrix (I1 to I10 Covered, I11 N/A), prd-gaps/specification-gaps.md. Consistency fix: requirements *Absent from M1* gains PF §8a project-scope grants (D-EHA-19). Correction notes on component-methods.md and services.md. Next-stage assessment: NFR Requirements, NFR Design, and Infrastructure Design all execute
  - [x] NFR Requirements: **APPROVED** 2026-11-11T06:19:46Z (presented 2026-11-11T05:55:53Z; revised and re-presented after review; committed as `159e5f0`). Q1 to Q5 answered 2026-11-11T05:53:43Z, all A, all technology: credential lifetime 15 minutes (capped at the sign-in); per-instance throttling (64 requests, 8 S1 calls, 1 s, then 503), with the user's instance-flood residual recorded in the SECURITY-11 row and per-principal and per-source limits carried to the first hosted deployment; one PostgreSQL 18 instance per environment; p95 300/200 ms reported, not gated; no pruning. P-01 to P-10 accepted, with the user's P-04 addition (U2 rotation step 2 waits at least 5 minutes; Infrastructure Design obligation for the operations notes). Artifacts: nfr-requirements (NFR-EHA-01 to 26, 08a), tech-stack-decisions (T-EHA-01 to 10; no new dependency). Review 2026-11-11T06:17:39Z: two corrections (NFR-EHA-03: sign-in leeway applies to the token check only, A7 judges expiry on S1's clock, three test cases; P-04 rotation paragraph: the wait covers the normal case, the unknown-kid refetch covers a failed or late refresh, NFR-EHA-08a gains the failed-refresh case); Retry-After: 5 and throttle.refused accepted. Functional Design committed as `b7f8904`; obligations posted on #8, #9, #10, and A7 on #5
  - [x] NFR Design: **APPROVED** 2026-11-11T06:44:26Z (presented 2026-11-11T06:33:52Z; revised after review and committed as `63d0ea8`). Obligations (logical-components.md §7) posted on [#8](https://github.com/soorma-ai/soorma-core/issues/8#issuecomment-6789072918), [#9](https://github.com/soorma-ai/soorma-core/issues/9#issuecomment-6789073310), [#10](https://github.com/soorma-ai/soorma-core/issues/10#issuecomment-6789073655). Q1 to Q4 answered 2026-11-11T06:27:05Z, all A, all technology: a typed JWT credential (`soorma-ec+jwt`; `env`, `sub`, `cid`, `jti`, `iat`, `exp`); a new `packages/service-kit` so S2 never links P10, with the user's conditions (Application Design notes; checks keep working; secret types; the move is Code Generation's first commit, pure, U2 tests green, S1 image rebuilt); attribution records as typed columns with CHECK constraints; a new `packages/env-store` owning one migration sequence and the transaction handle. P-01 to P-10 accepted with the user's two changes (key fetch on its own single-socket pool; request slot released in onResponse and onRequestAbort behind a release-once guard, with the 64-abort test). Artifacts: nfr-design-patterns (NP-EHA-01 to 15), logical-components. Found while writing: `@soorma/perimeter` depends on `@soorma/org-identity` at run time; fixed in the generalisation commit (P1's sign-in checker takes verify keys), and problem documents move to service-kit to avoid a cycle. Correction notes in components.md, component-methods.md, component-dependency.md; L1-24 and L1-32 targets updated. Review 2026-11-11T06:37:26Z: commit 2 gains the sign-in verification generalisations (leeway parameter with an explicit iat-ahead check; an `unknownKey` result with S2's refetch-then-verify-once flow in NP-EHA-03; the status callback returns A7's answer, one `signInStatus` call per request with `expiresAt` kept for the cap; a structural key source read on every verification), S1's behaviour unchanged; leeway and unknown-kid tests through P1 added
  - [x] Infrastructure Design: **APPROVED** 2026-11-11T06:58:38Z (presented 2026-11-11). Q1 to Q3 answered 2026-11-11T06:52:06Z, all A, all technology: one compose.yaml written out per environment; S1 `publicKeys` per environment with the user's addition (refuse a `kid` in two environments or twice in one; tested; Code Generation with S1's image rebuilt, as A7); an Operations section per service README (S1's rotation: "wait at least 5 minutes", with a docs test). P-01 to P-11 accepted, P-09 with the user's second case (S2 started while S1 is stopped) and case 1's corrected recovery wording. Artifacts: infrastructure-design (§1 to §17; O-1 to O-13 discharged), deployment-architecture; shared-infrastructure.md extended (Compose structure, configuration parts, secrets, stores, networks and ports, monitoring, internal callers, operations notes, organization-level outage)
  - [x] QA construction enrichment: **APPROVED** 2026-11-11T07:08:34Z (presented 2026-11-11). `inception/test-cases/env-human-access/`: TC-EHA-001 to 024 enriched in place; **TC-EHA-025 to 091 added** (67), covering every verification target in Functional Design, NFR Requirements, NFR Design, and Infrastructure Design, including the outage cases (084, 085), the Compose-model (079), privilege (080) and docs (081) tests, the caller-key refusals (082), the 64-abort test (059), and the concurrency tests (030, 035). `enrichment-delta.md` written (git-ignored). The Functional Design matrices' *QA enrichment* markers now name their TC ids. Next: the Construction Design PR gate
  - [x] Construction Design PR gate: **APPROVED** 2026-11-11T07:17:28Z (soorma-core#18 merged as `1a19082`)
  - [x] Code Generation: **APPROVED** 2026-11-11T21:18:26Z. soorma-core#19 merged as `95b96e5` (2026-11-11T21:16:53Z); every check green at `0904091` (build, check, and test; images, image secret scans, stack smoke test, and the S1-stopped demonstration; dependency review; CLA). Plan APPROVED 2026-11-11T07:26:16Z (D-CG-EHA-12, 13: the stack run per group, each push run green). Part 2 in eight groups on `dev`: `6b679e0` (the pure move into `packages/service-kit`), `d2db9e0` (D-CG-EHA-15), `1297d8d`, `cb3deea` (A7; `publicKeys`), `a50f8fc` (the contract, `env-store`, P4, P5, P7, P3, P9, P1), `fcc4d3d` (S2), `7e00606` (E and E2 on the stack), `4c6bb1d` (READMEs), `0904091` (the six test cases without a test, D-CG-EHA-31; summary; matrices). Decisions D-CG-EHA-01 to 31; U2 assertion changes D-CG-EHA-16, Group 3's A7, D-CG-EHA-17, D-CG-EHA-28, each approved (diffs in `construction/env-human-access/code/code-summary.md`); D-CG-EHA-29 the user's standing approval. L1: 33 rows Implemented; I1 to I10 Implemented. Local run: 1050 passed, 3 skipped; every check; `pnpm audit` clean; both images; smoke 52 checks; outage both cases. **Latency in process only** (stub S1, no TLS; p95 about 5 ms per operation): **corrected at approval** (NFR-EHA-15, D-CG-EHA-10 call for the stack), with the stack measurement carried to Build and Test
- **Unit U4 `env-human-access` (#7): COMPLETE** 2026-11-11T21:18:26Z. soorma-core#7 stays open until Build and Test, with a [completion comment](https://github.com/soorma-ai/soorma-core/issues/7#issuecomment-6807264561) linking #18 and #19
- **Current unit**: U5 `agent-registration` (#8). Session resumed 2026-11-11T21:36:46Z: re-intake check clean (brief unchanged at `0aad84a`; no new PF or ID tag; soorma-prd#13, #24, #25, #27, #28, #30 open). Construction Phase Initialization re-run: rules loaded for all five enabled extensions; prd-gap-classification.md active; invariant text identical at both tags. Unit Initialization and the L1 gate's initial assessment done (0 Missing; one case to classify at Functional Design: who may issue a registration secret, PF §8a "Admin or sponsoring Developer" read through ID §3's definition of Admin). **The user's standing rules for U5 Code Generation** (earlier units' test changes in three classes; the per-group gate with image builds and the local stack; push and wait for CI per group; stop for merges, nothing recorded as merged until GitHub shows it) are recorded in the Functional Design plan and verbatim in audit.md; they replace the handoff's request to confirm D-CG-EHA-29 for U5
  - [x] Functional Design: **APPROVED** 2026-11-11T22:06:11Z, with the user's two additions (business-rules §17: each `soorma_rs_` value carries its record's id, at least 256 random bits, a fast hash stored, never a slow password hash; U6's bootstrap loads exactly that one record, active and of the named registration, compares in constant time, every mismatch the unknown-secret refusal; D-AR-16 and domain-entities noted). **Next-stage assessment**: NFR Requirements executes; NFR Design executes; **Infrastructure Design decided at the end of NFR Requirements** (it runs if the verifier needs a server-side key, a new mounted-file secret). Committed as `5d8294f`; push run 43108905552 green. Obligations (§17) posted on [#9](https://github.com/soorma-ai/soorma-core/issues/9#issuecomment-6808306600) and [#10](https://github.com/soorma-ai/soorma-core/issues/10#issuecomment-6808307067). Plan answered 2026-11-11T21:50:31Z: Q1 A (**specified**, no gap: `agent:register` and the sponsor or an Admin, Admin per ID §3; the user's observation that ID FR-026's replacement rule diverges from ID §3's Admin recorded as a forward obligation for the slice that builds FR-026, not resolved); Q2 A (client-chosen `agent`, `registration_exists` 409); Q3 A (`human_only_permission`, `declaration_outside_standing`, `exceeds_sponsor_ceiling`); Q4 A (several active secrets, cap at NFR Requirements); Q5 A (`unknown_registration`); Q6 A (standing set on the registration only); P-01 to P-19 accepted, P-03 with the user's condition (D-AR-07: one read, one evaluator, `evaluateHuman` refactored around `evaluateHeld`; U4's obligation kept in substance), P-08 as following PF §8a (D-AR-12). Artifacts: domain-entities, business-rules (D-AR-01 to 27), business-logic-model, l1-coverage-matrix (32 Covered, 0 Missing; L1-17, L1-31 on the GAP-INT-006 work-around), invariant-coverage-matrix (I1 to I10 Covered, I11 N/A). No specification gap in U5. Correction notes on component-methods.md and components.md
  - [x] NFR Requirements: **APPROVED** 2026-11-11T22:27:32Z; committed as `c0b222a`, push run 43111942139 green; the verifier obligation posted on [#9](https://github.com/soorma-ai/soorma-core/issues/9#issuecomment-6808678348); with the user's addition to NFR-AR-09 and 10 (the backup's password from the mounted secret through a pgpass file built from /run/secrets, PGPASSFILE only, never PGPASSWORD, a variable, or an argument; a one-shot Compose service on {env}'s network mounting only the migrator's subpath; the Compose-model test sees no password in it). Plan answered 2026-11-11T22:17:08Z, all technology: Q1 A (unkeyed, domain-separated SHA-256; no server-side key), Q2 A (no checksum; `soorma_rs_{id}.{secret}`), Q3 A (cap 10, `secret_limit_reached` 409; with the user's addition: a security bound, not a tenant quota, in the I8 table), Q4 A (U4's store guarantees plus documented backup and restore; with the user's addition: the dump holds human identifiers, git-ignored path, mode 0600, README says so, restore test on a temporary path deleted), Q5 A (no registration bound; residual); P-01 to P-12 accepted, P-07 corrected by the user (the cap serialised per registration without UPDATE privilege, for example pg_advisory_xact_lock; physical form NFR Design's). Artifacts: nfr-requirements (NFR-AR-01 to 24), tech-stack-decisions (T-AR-01 to 05; no new dependency). Consistency fixes to Functional Design, marked in place: `secret_limit_reached` (business-rules §10, §13, BR-SE-06, BR-RF-AR-03, D-AR-23 wording; domain-entities) and the I8 table row. **Infrastructure Design: SKIPPED** (decided here: Q1 A, no server-side key; no new deployable, store, network, or secret)
  - [x] NFR Design: **APPROVED** 2026-11-11T22:45:47Z; committed as `c6da1ff`, push run 43114570442 green; the U6 obligation (logical-components §7) posted on [#9](https://github.com/soorma-ai/soorma-core/issues/9#issuecomment-6809034256); with NP-AR-09 (3) replaced by the user (the checksum test and the normalised projection dropped; an archive validity check after each backup: the PGDMP magic bytes and pg_restore --list exiting 0; custom format kept). Plan answered 2026-11-11T22:38:59Z, all technology: Q1 A (pg_advisory_xact_lock over a domain-separated key), Q2 A (the secret format in packages/registry; U6 obligation: S3 must not link org-identity), Q3 A (streamed; with the user's correction: run --rm -T, stdin open for restore, diagnostics to stderr, a stable-checksum test), Q4 A (db:test round trip and a CI stack step; with the user's addition: restore into an empty database, migrate applies nothing, the privilege test re-run), Q5 A (flat-set `<@` CHECKs, the human-only class never in SQL); P-01 to P-09 accepted, P-09 corrected by the user (a dedicated backup/ subdirectory, uid 999, mounting only it; verify-full with the stack CA). Artifacts: nfr-design-patterns (NP-AR-01 to 10), logical-components; matrices' targets noted
  - [x] Infrastructure Design: **SKIPPED** (decided at NFR Requirements: unkeyed verifier, no server-side key; no new deployable, store, network, or secret)
  - [x] QA construction enrichment: **APPROVED** 2026-11-12T00:34:08Z (generated 2026-11-11) (`inception/test-cases/agent-registration/`: TC-AR-001 to 022 enriched in place, **TC-AR-023 to 072 added** (50); `enrichment-delta.md` written, git-ignored). Sources: functional-design/, nfr-requirements/ (by the user's instruction), nfr-design/. Every verification target in the L1 and invariant matrices, nfr-requirements.md, and nfr-design-patterns.md now names its TC id
  - [x] Construction Design PR gate: **APPROVED** 2026-11-12T00:46:08Z (soorma-core#20 merged as `1903711`; every check green at `eb9ddb8`); recorded in `923bc16`, push run 43129729467 green
  - [x] Code Generation: **APPROVED** 2026-11-12T03:07:00Z. soorma-core#21 merged as `7f8d872` (2026-11-12T03:05:04Z); every check green at `68e9e9b`. Part 1 plan written 2026-11-12 (`construction/working/agent-registration-code-generation-plan.md`: Step 0 and Steps 1 to 29 in nine groups; Group 1 the `evaluateHuman` refactor alone with U4's tests unchanged; D-CG-AR-01 to 12; the user's standing rules; stop conditions 1 to 8). **Plan APPROVED** 2026-11-12T01:02:26Z. Part 2: Step 0 `cbed37e`; Group 1 `143f073` (the evaluateHuman refactor; U4's tests unchanged; run 43132470557); Group 2 `0a90d67` (run 43133270078); Group 3 `5b9ccc2` (run 43134373872); Group 4 `3e9e98f` (run 43135835915); Group 5 `167011c` (run 43137498916), every push run green. Earlier units' test changes so far: D-CG-AR-13 to 18 (class 1; D-CG-AR-17 part 2 class 2). **Stopped for review after Group 5** (2026-11-12T01:59:10Z), as the user asked. Groups 1 to 5 reviewed and accepted by the user (2026-11-12T02:01:58Z; D-CG-AR-17 confirmed class 2); Groups 6 to 9 in progress, after the review stop. Q-CG-AR-1 (stop condition 3 in Group 6) answered A by the user: the archive check is a full read (D-CG-AR-20); U4's per-service Compose-model rules applied to the backup services (D-CG-AR-21, class 2). Group 6 `b2cc93a` + CI fix `a217d34` (D-CG-AR-23; run 43140929923 green); Group 7 `5819f6b` + CI fix `c4bda89` (D-CG-AR-24); Group 8 `68e9e9b` (run 43143924152 green); Group 9: **PR soorma-core#21** opened, every check green (pull_request run 43144696101: build, check, and test; images, stack smoke, the S1-stopped demonstration, and the e2e proofs; dependency review; cla-assistant), **not merged**. Completion presented 2026-11-12T03:03:03Z
- **Unit U5 `agent-registration` (#8): COMPLETE** 2026-11-12T03:07:00Z. soorma-core#8 stays open until Build and Test, with a [completion comment](https://github.com/soorma-ai/soorma-core/issues/8#issuecomment-6813177498) linking #20 (design) and #21 (code), the open obligations, and TC-AR-061, 064, 065
- **Current unit**: U6 `agent-credentials` (#9). Session resumed 2026-11-12T03:40:07Z: re-intake check clean (brief unchanged at `0aad84a`; no new PF or ID tag; soorma-prd#13, #24, #25, #27, #28, #30 open). Construction Phase Initialization re-run: rules loaded for all five enabled extensions; prd-gap-classification.md active; invariant text identical at both tags. Unit Initialization and the L1 gate's initial assessment done (0 Missing; nine questions to classify at Functional Design, all assessed as technology). Obligations read from #9 (seven comments). Found while planning: `packages/abuse-bound` declares `@soorma/org-identity` as a production dependency (test harness only), so S3 linking P8 would link it (plan P-03). **The user's standing rules for U6 Code Generation** (the three classes of earlier-unit test changes, U1 to U5; the per-group gate with image builds and the local stack; push and wait for CI per group; stop for merges, nothing recorded as merged until GitHub shows it; Infrastructure Design to check U4's Compose-model rules against S3's services, including any under a profile) are confirmed and recorded in the Functional Design plan and verbatim in audit.md
  - [x] Functional Design: **APPROVED** 2026-11-12T03:59:45Z, D-AC-33 included, with the user's rule at approval: **the store's repeat of D-AC-33 is a new migration in `env-store`'s sequence; `0001` and `0002` stay untouched**; the reverse rule stays U7's, under the standing rules. Committed as `3ba54bf`; push run 43151870272 green; §17's U7 obligations posted on [#10](https://github.com/soorma-ai/soorma-core/issues/10#issuecomment-6814198317) (`construction/agent-credentials/functional-design/`: domain-entities, business-rules (D-AC-01 to 34), business-logic-model, l1-coverage-matrix (34 Covered, 0 Missing; L1-27, 29 on the GAP-INT-008 work-around, L1-28 on GAP-INT-009's), invariant-coverage-matrix (I1 to I10 Covered, I11 N/A)). Plan answered 2026-11-12T03:49:08Z, all technology, no gap: Q1 A (renewal reads revocation directly; P5's cache built now, wired at S4 by U7); Q2 A (a lineage's maximum age M); Q3 A (a separate agent key ring per environment); Q4 A (one `secret` field typed by its prefix); Q5 A (`authentication_failed` widened); Q6 A (U2's bound shape per environment, keyed on the presented agent, known or not), **with the user's addition**: the lockout residual recorded, and the secret-record mitigation carried to the first hosted deployment; Q7 A (instance identifiers may repeat; `identifiers.md` clarified); Q8 A (`packages/agent-identity`); Q9 A (the endpoint names the environment). P-01 to P-23 accepted, **P-12 with the user's precision** (BR-AT-AC-02: the record's operation, `exchangeBootstrap` or `renewAgentCredential`, never carries an envelope, GAP-INT-008, so its absence is readable from the record alone; P7 holds the envelope-free list, D-AC-33). The gate's image secret scan and `test:e2e` on a fresh stack confirmed as part of "the full checks and tests". Correction notes on components.md and component-methods.md. **Next-stage assessment**: NFR Requirements, NFR Design, and Infrastructure Design all execute
  - [x] NFR Requirements: **APPROVED** 2026-11-12T04:19:07Z (`construction/agent-credentials/nfr-requirements/`: nfr-requirements (NFR-AC-01 to 27), tech-stack-decisions (T-AC-01 to 07; no new dependency)). Plan answered 2026-11-12, all technology, no gap: Q1 B (**B = 60 s**); Q2 A (**L = 15 min**); Q3 B (**M = 24 h**); Q4 B (60 live attempts per agent in 60 s; backoff from the 10th failure, capped at 60 s; the lockout at most 60 s after an attack stops); Q5 A (cache hit 0.1 ms p99, bootstrap and renewal 200 ms p95, reported, not gated). P-01 to P-17 accepted, **P-08 with the user's precision**: B published as the platform's bound; L and M as upper bounds only, the contract stating that clients schedule renewal from `expiresAt`, re-bootstrap on `credential_expired` at the end of the lineage, and never hard-code L or M; the same noted for soorma-sdk's session (the brief's consumer; the brief not edited). Consistency fix to Functional Design §13, marked in place. Next: NFR Design, then Infrastructure Design (both run). Committed as `add607f`; push run 43154023186 green
  - [x] NFR Design: **APPROVED** 2026-11-12T04:42:09Z; committed as `64c2f79`, push run 43156543236 green; NP-AC-12 included, with the user's condition: a test fixture that would trip the new patterns uses obviously fake values, never an exception in the check (`construction/agent-credentials/nfr-design/`: nfr-design-patterns (NP-AC-01 to 13), logical-components). Push run 43154023186 on `add607f` confirmed passed before starting. Plan answered 2026-11-12, all A, all technology: Q1 **B, L, M as code constants** (`PROPAGATION_BOUND_MS` and two more in `packages/credentials`), with the user's addition: NFR-AC-01 and 04 (and Functional Design BR-RC-04, D-AC-18; L1-11's target) fixed in place citing PF FR-012's "platform-set and not tenant-configurable" and its rejected alternative, and **U7 passes `PROPAGATION_BOUND_MS` to U3's term cache** (in the U7 obligations); Q2 a new `agent_credentials` table; Q3 the cache per credential, read through, 16,384 entries; Q4 P8's generic core with U2's API and vectors kept (a change stops Code Generation); Q5 two revocation tables with foreign keys; Q6 the closure test over the manifests and the built image, with the user's addition (class 2): the same installed-packages check on S2's image, beside S3's, S2's manifest test unchanged. P-01 to P-23 accepted. Migrations `0003_agent_credentials.sql` and `0004_attribution_envelope_free.sql`; `0001`, `0002` untouched. Made at design and flagged: NP-AC-12 (two secret patterns, class 2). Found while designing: TC-EHA-068 pins the migration list (gains two names, class 1, as U5's D-CG-AR-13); U5's restore e2e stops `e-control-gateway` and `e-db` by name and gains `e-data-gateway` (class 1, checked at Code Generation)
  - [x] Infrastructure Design: **APPROVED** 2026-11-12T05:09:55Z; committed as `7172d18`, push run 43159561380 green; with the user's addition (the `soorma_env_data` privilege test runs P8's actual `statement()` objects and S3's own statements as the role and they succeed, beside the refusals; NP-AC-06 and §5) (`construction/agent-credentials/infrastructure-design/`: infrastructure-design (D-ID-AC-01 to 18, §1 to §19), deployment-architecture; `construction/shared-infrastructure.md` extended). Q1 to Q4 A; **Q2's caveat fired** before generating (U4's subpath rule failing on `e-restore`, `e2-restore`) and **Q5 A resolved it: the user's explicit approval of exactly one class-3 change** (the restore services' own `restore/` subdirectory; `deploy/test/backup.test.ts`'s expected subpath for them, `backup` to `restore`; D-ID-AC-14 with its diff); so U4's Compose-model test renders with every profile, its rules unchanged (D-ID-AC-13, class 2, with class-1 list additions). **D-ID-AC-07, the user's decision**: S3's own role `soorma_env_data` (env-roles.sql; granted in `0003`; nothing on `grants`, `credentials`, `schema_migrations`; no `DELETE`), with the accepted additions (D-ID-AC-08: `{env}-db-data-password` in `db/` and `data-gateway/` instead of the app password; the `env-pg_hba.conf` line). NFR Design NP-AC-06 corrected in place, and Functional Design D-AC-16, BR-CR-AC-05, BR-RV-05 and logical-components §3 marked. S3: `e-data-gateway` `127.0.0.1:8444`, `e2-data-gateway` `8445`, U7 from `8446`; `{env}` network only; `{env}-agent-signing-key-1` and its verify half (unmounted until U7), `{env}-bootstrap-counter-secret`; TC-AC-017 as `stack:outage` Case 3; U5's backup e2e lists gain `e-data-gateway`; S3's README Operations with "wait at least 15 minutes" and the upgrade note (re-create a pre-U6 local stack once)
  - [x] QA construction enrichment: **APPROVED** 2026-11-12T06:01:35Z (`inception/test-cases/agent-credentials/`: TC-AC-001 to 022 enriched in place, TC-AC-009, 010, 015 adjusted for D-AC-01; **TC-AC-023 to 093 added** (71); `enrichment-delta.md` written, git-ignored). Sources: functional-design/, nfr-requirements/ (by the user's instruction), nfr-design/, infrastructure-design/. **Every verification target in the five U6 design artifacts with verification targets names a TC-AC id**: l1-coverage-matrix (34 rows), invariant-coverage-matrix (I1 to I10), nfr-requirements (NFR-AC-01 to 27), nfr-design-patterns (NP-AC-01 to 13), infrastructure-design (§20, D-ID-AC-01 to 18). Next: the Construction Design PR gate, after review
  - [ ] Construction Design PR gate: **PENDING**, opened 2026-11-12T06:02:43Z (`dev` → `main`, Refs #9, #3, no closing keyword); the user merges and says so. Nothing recorded as approved until then
- [ ] Per unit: Functional Design, NFR Requirements, NFR Design, Infrastructure Design (EXECUTE; may skip per unit), Code Generation (EXECUTE). Done: U1, U2, U3, U4, U5. Next: U6. Remaining: U6, U7
- [ ] Build and Test: EXECUTE

### 🟡 OPERATIONS PHASE
- [ ] Operations: PLACEHOLDER

**Session stop point** (2026-11-12T03:07:00Z): U5 `agent-registration` COMPLETE (Code Generation approved;
soorma-core#21 merged as `7f8d872`; `dev` fast-forwarded to `main`). soorma-core#8 stays open until
Build and Test, with a completion comment linking #20 (design) and #21 (code).

**Next: U6 `agent-credentials` (soorma-core#9), in a new session.** Start with:
1. Session resumption (`common/session-continuity.md`); re-intake check: brief still at `0aad84a`,
   no new PF or ID tag, the gap issues' states (soorma-prd#24, #25, #27, #28, #30; #13 for
   GAP-INT-003). U6 rests on GAP-INT-008's work-around (neither bootstrap nor renewal carries an
   envelope, soorma-prd#27) and GAP-INT-009's (the internal revocation read writes no attribution
   record, soorma-prd#28)
2. Construction Phase Initialization (extension rules; `prd-gap-classification.md` active), then
   Unit Initialization and the L1 gate's initial assessment for U6
3. Read the forward obligations posted on soorma-core#9 (seven comments: U3's Functional Design and
   NFR Requirements; U4's Functional Design and NFR Design; U5's Functional Design, NFR
   Requirements, and NFR Design), summarised below
4. Toolchain: `node --version` 26.13.0, `pnpm --version` 12.18.0; Docker Engine 26 and Compose
   2.26.0 or later for the stack. The database tests need `pnpm db:test` and both values it prints,
   `TEST_DATABASE_URL` and `TEST_DATABASE_CONTAINER`. `pnpm test:e2e` runs on a fresh stack
   (`down -v`, `stack:up`), and needs the workspace built

**What U6 inherits** (posted on soorma-core#9):
- **From U3**: the agent credential asserts organization, project, environment, logical agent, and
  instance; S3 emits Problems through P1 and runs the shared assertion on every Problem (BR-PE-06);
  **the propagation bound is one configured value** (M1-NFR-01), read by P5's revocation cache and
  by U3's term cache as its TTL; U6 sets the value at its NFR Requirements
- **From U4**: S3 refuses `soorma_ec_` and `soorma_si_` by kind, without verifying; P5
  (`packages/credentials`) gains the agent kind and the propagation-bound revocation cache;
  bootstrap and renewal write attribution records through P7 with an **agent actor** (logical agent,
  instance, credential where presented, registration reference, **resolved sponsor**) and no chain,
  origin, or re-broadening (no envelope, GAP-INT-008); U6's tables join `env-store`'s one migration
  sequence with the three environment columns; NP-EHA-01's token shape is a working pattern for
  `soorma_ac_` (U6's Functional Design decides); shared runtime from `packages/service-kit`; **S3
  must not have `@soorma/org-identity` in its production dependency closure**
- **From U5**: bootstrap names the registration by its `agent` and requires `state` = `registered`;
  it **parses the secret record's `id` from the `soorma_rs_{id}.{secret}` value, loads that one
  record** (`active`, of the named registration in E), and **compares in constant time** through
  `registrationSecretMatches`; every failure (malformed value, unknown id, another registration or
  environment, not active, mismatch) is the same refusal as an unknown secret, and nothing iterates a
  registration's secrets; **import `parseRegistrationSecret` and `registrationSecretMatches` from
  `packages/registry`**, never a copy; the verifier is unkeyed (no new secret for S3); nothing logs
  the value or its digest; **P6's agent half must not make S3 link `org-identity`** (today
  `packages/identity-resolution` depends on it: keep the agent half apart, or split the package);
  read registrations and secrets through P4 on the four-column keys; the app role holds `SELECT` and
  `INSERT` only on both tables, so U6's own per-secret bookkeeping is its own table
- **Standing note (NFR-AE-16)** above applies to the first unit that changes a standing set,
  declaration, or autonomy, or suspends or retires an agent

**The user's standing rules, carried over for U6's Code Generation** (set for U5, recorded verbatim
in `audit.md` 2026-11-11T21:36:46Z; confirm at U6's plan):
- **Changes to an earlier unit's tests (U1 to U5)**, in three classes: *required by the approved
  design* (an item the design adds, nothing removed or reworded): proceed and record it; *strictly
  stronger* (a negative check scanning more sources or values, the existing ones unchanged): proceed
  and record it; **anything else (removed, relaxed, or replaced, such as a changed expected value):
  stop for the user**. A changed test helper an earlier unit's assertions depend on is in the third
  class unless shown to behave the same. The completion message lists every such change as a
  before/after diff, with its reason
- **The pre-commit gate, for each commit group**: the full checks and tests (with `db:test`); an
  image build (and scan) for every deployable whose dependencies the group touches; when the group
  changes a deployable's runtime, the local stack (`stack:init`, `up`, `smoke`, `down -v`), and
  `test:e2e` on a fresh stack once it covers the unit
- **Push after each group, and wait for its CI run to pass before the next.** Present completion
  only when every check on the code PR passes
- **When a PR needs merging, stop and tell the user.** Nothing is recorded as merged until GitHub
  shows it merged

**Carried to Build and Test** (from U5): TC-AR-061 (U5's residuals stated in the summary), TC-AR-064
(p95 of `registerAgent` and `issueRegistrationSecret` on the running stack, reported, NFR-AR-15),
TC-AR-065 (`pnpm bench:admit` with P4's agent-facts source, reported, NFR-AE-07); U5's residuals
(no registration bound in M1; a lost volume without a backup loses every registration; a taken
identifier learnable within E by a holder of `agent:register`; a registration made by mistake not
removable in M1; each active secret a separate way in). **To the first hosted deployment**:
replication, point-in-time recovery, off-host encrypted backups; registration bounds per sponsor or
environment. **To the slice that builds ID FR-026**: classify its replacement rule's divergence from
ID §3's Admin (business-rules §17).

**Carried to Build and Test** (from U4): **p95 latency on the running stack** (NFR-EHA-15;
TC-EHA-070), with the real S1 and TLS, against 300 ms (issuance, renewal) and 200 ms (ending,
`grantToHuman`), reported, not a gate (U4's Code Generation figures are in process only, about
5 ms, with a stub S1); Infrastructure Design §11's two outage cases (`pnpm stack:outage`); the
rotation test (NFR-EHA-08a); the Compose-model, privilege, and docs tests; U4's accepted residuals
(the post-logout credential, at most 15 minutes; the Admin self-grant; the organization-level
outage; the instance flood) and the user's SECURITY decisions. **To the first hosted deployment**:
per-principal and per-source limits on S2 (NFR-EHA-06). From U3: TC-AE-040 (`pnpm bench:admit`),
reported.

**Carried to Build and Test** (from U2): TC-OI-059 and TC-OI-062 (`pnpm test:perf`); on the
workstation, Argon2id at 64 MiB measured about 710 ms late in U2's session, which puts NFR-OI-19's
500 ms p95 for `authenticate` at risk on that machine; the user's "not applicable in M1" decisions
(SECURITY-01 at rest, SECURITY-03's log service, SECURITY-14) and U2's accepted residuals. U4's
obligations from U2 are on soorma-core#7. From U1: Build and Test also uses U1's verification (CI on
soorma-core#12, `pnpm run check:github`), and U1's work-around gaps GAP-INT-003 and GAP-INT-008 stand.
