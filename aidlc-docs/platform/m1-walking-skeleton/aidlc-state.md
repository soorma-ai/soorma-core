# AI-DLC State Tracking

## Project Information
- **Project**: soorma-core: M1 walking skeleton (server side)
- **Project Type**: Greenfield
- **Start Date**: 2026-10-05T02:24:31Z
- **Milestone**: M1, Walking skeleton (from the slice brief; matches `aiprd-docs/build-sequence.md`)
- **Current Stage**: CONSTRUCTION. **U4 `env-human-access` (soorma-core#7): Functional Design APPROVED 2026-11-11T04:17:24Z; NFR Requirements APPROVED 2026-11-11T06:19:46Z; NFR Design APPROVED 2026-11-11T06:44:26Z; Infrastructure Design APPROVED 2026-11-11T06:58:38Z; QA construction enrichment APPROVED 2026-11-11T07:08:34Z; Construction Design PR gate APPROVED 2026-11-11T07:17:28Z (#18 merged as 1a19082); Code Generation plan APPROVED 2026-11-11T07:26:16Z; Part 2 Group 1 complete (6b679e0, push CI green); paused for the user before Group 2** (GAP-EHA-001 resolved — clarified, no PRD change; U2 amendment A7). U1, U2, and U3 complete. Stage history is under *Stage Progress*
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
  - [x] Construction Design PR gate: **APPROVED** 2026-11-11T07:17:28Z (soorma-core#18 merged as `1a19082`)
  - [ ] Code Generation: plan **APPROVED** 2026-11-11T07:26:16Z, with the user's two changes (D-CG-EHA-13: S1's healthcheck shim; D-CG-EHA-12: the local stack run in Groups 1, 2, 3, and 5, and each group's push CI run green before the next). Part 2: **Group 1 complete** (`6b679e0`, the pure move into `packages/service-kit`; push CI run green); paused for the user before Group 2
  - [x] Construction Design PR gate: **APPROVED** 2026-11-10T21:31:28Z (opened 2026-11-10T16:07:33Z as soorma-core#16, `dev` → `main`; one change requested 2026-11-10T20:19:53Z, the entry point named `createEnvelopeAdmission(dependencies).admit(request)` throughout, fixed in `1a44021`; merged 2026-11-10T21:30:40Z as `fbb567c`)
  - [x] Code Generation: **APPROVED** 2026-11-11T02:39:10Z. soorma-core#17 merged as `a9aa74b` (2026-11-11T02:38:46Z); CI green at `cad1772` (build, check, and test; image, image secret scan, and stack smoke test; dependency review). Plan APPROVED 2026-11-10T21:53:41Z (two amendments; Q-CG-AE-1 A). Part 2 generated 2026-11-10T22:31:47Z: Steps 0 to 23 on `dev` (`4821788`, `8d90404` the U2 guard alone, `626ed4b` the swap with the guard unchanged, `ef7c392`, `90dc1fd`, `6508782`, `b6a59c5`, and Group 7); code-review PR **soorma-core#17** from `dev` to `main` (not merged). L1: 38 rows Implemented; I1 to I10 Implemented. Local run: 766 passed, 2 skipped; every check passes; `pnpm audit` clean. TC-AE-040 reported only. **Request Changes 2026-11-11T02:25:14Z**: (1) the S1 image copies `packages/jcs` (#17's image check), and the gate builds the image for a group reaching S1's dependencies; (2) an unresolved upstream agent is the empty set and evaluation continues (D-AE-09 consistency fix; TC-AE-016 step 2; the first build missed stop condition 2); (3) `errors[]` at most 10 (D-AE-18 consistency fix; TC-AE-029 step 5). Local run after: 771 passed, 2 skipped; image builds. Fixes committed as `cad1772`
  - **Standing note (NFR-AE-16)**: no M1 operation changes a standing set, re-broadening declaration, or autonomy declared, or suspends or retires an agent, so U3's term cache cannot serve stale data in M1. **The unit that first adds such an operation must account for the cache's staleness window** (up to the propagation bound)
- **Current unit**: U4 `env-human-access` (#7). Session resumed 2026-11-11T03:43:04Z: re-intake check clean (brief unchanged at `0aad84a`; no new PF or ID tag; soorma-prd#13, #24, #25, #27, #28, #30 open). Construction Phase Initialization re-run: rules loaded for all five enabled extensions; prd-gap-classification.md active; invariant text identical at both tags. Unit Initialization and the L1 gate's initial assessment done (0 Missing; one case to classify at Functional Design: ID FR-010, whether ending a sign-in refuses the environment credentials issued from it)
  - [x] Functional Design: **APPROVED** 2026-11-11T04:17:24Z (presented 2026-11-11T04:08:50Z). At approval: D-EHA-23 accepted (`principalExists` is `grantToHuman`'s own lookup, not a per-request freshness check), and its consequence added to §16 as an accepted residual (during an organization-level outage, issuance, renewal, and `grantToHuman` are `unavailable`; ending and O1 to O4 unaffected), with a Build and Test obligation to show it with S1 stopped; D-EHA-24 to 31 accepted as written. Plan answered 2026-11-11T03:59:19Z: Q1 D (specification, **GAP-EHA-001 Resolved — clarified, no PRD change**: R2, renewal only; SECURITY-12 reading: ending the environment credential is its own logout); Q2 A (**U2 amendment A7**, `signInStatus` with the current expiry and the principal's state); Q3 A; Q4 A plus the resolved sponsor and the re-broadening outcome; Q5 A (`unknown_principal`); Q6 A (`unknown_permission`); Q7 A plus at most one configuration grant under concurrent start-ups (a uniqueness constraint, tested); P-01 to P-15 accepted. Artifacts: domain-entities, business-rules (D-EHA-01 to 31), business-logic-model, l1-coverage-matrix (33 Covered, 20 N/A, 0 Missing), invariant-coverage-matrix (I1 to I10 Covered, I11 N/A), prd-gaps/specification-gaps.md. Consistency fix: requirements *Absent from M1* gains PF §8a project-scope grants (D-EHA-19). Correction notes on component-methods.md and services.md. Next-stage assessment: NFR Requirements, NFR Design, and Infrastructure Design all execute
  - [x] NFR Requirements: **APPROVED** 2026-11-11T06:19:46Z (presented 2026-11-11T05:55:53Z; revised and re-presented after review; committed as `159e5f0`). Q1 to Q5 answered 2026-11-11T05:53:43Z, all A, all technology: credential lifetime 15 minutes (capped at the sign-in); per-instance throttling (64 requests, 8 S1 calls, 1 s, then 503), with the user's instance-flood residual recorded in the SECURITY-11 row and per-principal and per-source limits carried to the first hosted deployment; one PostgreSQL 18 instance per environment; p95 300/200 ms reported, not gated; no pruning. P-01 to P-10 accepted, with the user's P-04 addition (U2 rotation step 2 waits at least 5 minutes; Infrastructure Design obligation for the operations notes). Artifacts: nfr-requirements (NFR-EHA-01 to 26, 08a), tech-stack-decisions (T-EHA-01 to 10; no new dependency). Review 2026-11-11T06:17:39Z: two corrections (NFR-EHA-03: sign-in leeway applies to the token check only, A7 judges expiry on S1's clock, three test cases; P-04 rotation paragraph: the wait covers the normal case, the unknown-kid refetch covers a failed or late refresh, NFR-EHA-08a gains the failed-refresh case); Retry-After: 5 and throttle.refused accepted. Functional Design committed as `b7f8904`; obligations posted on #8, #9, #10, and A7 on #5
  - [x] NFR Design: **APPROVED** 2026-11-11T06:44:26Z (presented 2026-11-11T06:33:52Z; revised after review and committed as `63d0ea8`). Obligations (logical-components.md §7) posted on [#8](https://github.com/soorma-ai/soorma-core/issues/8#issuecomment-6789072918), [#9](https://github.com/soorma-ai/soorma-core/issues/9#issuecomment-6789073310), [#10](https://github.com/soorma-ai/soorma-core/issues/10#issuecomment-6789073655). Q1 to Q4 answered 2026-11-11T06:27:05Z, all A, all technology: a typed JWT credential (`soorma-ec+jwt`; `env`, `sub`, `cid`, `jti`, `iat`, `exp`); a new `packages/service-kit` so S2 never links P10, with the user's conditions (Application Design notes; checks keep working; secret types; the move is Code Generation's first commit, pure, U2 tests green, S1 image rebuilt); attribution records as typed columns with CHECK constraints; a new `packages/env-store` owning one migration sequence and the transaction handle. P-01 to P-10 accepted with the user's two changes (key fetch on its own single-socket pool; request slot released in onResponse and onRequestAbort behind a release-once guard, with the 64-abort test). Artifacts: nfr-design-patterns (NP-EHA-01 to 15), logical-components. Found while writing: `@soorma/perimeter` depends on `@soorma/org-identity` at run time; fixed in the generalisation commit (P1's sign-in checker takes verify keys), and problem documents move to service-kit to avoid a cycle. Correction notes in components.md, component-methods.md, component-dependency.md; L1-24 and L1-32 targets updated. Review 2026-11-11T06:37:26Z: commit 2 gains the sign-in verification generalisations (leeway parameter with an explicit iat-ahead check; an `unknownKey` result with S2's refetch-then-verify-once flow in NP-EHA-03; the status callback returns A7's answer, one `signInStatus` call per request with `expiresAt` kept for the cap; a structural key source read on every verification), S1's behaviour unchanged; leeway and unknown-kid tests through P1 added
  - [x] Infrastructure Design: **APPROVED** 2026-11-11T06:58:38Z (presented 2026-11-11). Q1 to Q3 answered 2026-11-11T06:52:06Z, all A, all technology: one compose.yaml written out per environment; S1 `publicKeys` per environment with the user's addition (refuse a `kid` in two environments or twice in one; tested; Code Generation with S1's image rebuilt, as A7); an Operations section per service README (S1's rotation: "wait at least 5 minutes", with a docs test). P-01 to P-11 accepted, P-09 with the user's second case (S2 started while S1 is stopped) and case 1's corrected recovery wording. Artifacts: infrastructure-design (§1 to §17; O-1 to O-13 discharged), deployment-architecture; shared-infrastructure.md extended (Compose structure, configuration parts, secrets, stores, networks and ports, monitoring, internal callers, operations notes, organization-level outage)
  - [x] QA construction enrichment: **APPROVED** 2026-11-11T07:08:34Z (presented 2026-11-11). `inception/test-cases/env-human-access/`: TC-EHA-001 to 024 enriched in place; **TC-EHA-025 to 091 added** (67), covering every verification target in Functional Design, NFR Requirements, NFR Design, and Infrastructure Design, including the outage cases (084, 085), the Compose-model (079), privilege (080) and docs (081) tests, the caller-key refusals (082), the 64-abort test (059), and the concurrency tests (030, 035). `enrichment-delta.md` written (git-ignored). The Functional Design matrices' *QA enrichment* markers now name their TC ids. Next: the Construction Design PR gate
- [ ] Per unit: Functional Design, NFR Requirements, NFR Design, Infrastructure Design (EXECUTE; may skip per unit), Code Generation (EXECUTE). Done: U1, U2, U3. In progress: U4. Remaining: U5 to U7
- [ ] Build and Test: EXECUTE

### 🟡 OPERATIONS PHASE
- [ ] Operations: PLACEHOLDER

**Session stop point** (2026-11-11T02:39:10Z): U3 `authority-evaluation` COMPLETE (Code Generation
approved; soorma-core#17 merged as `a9aa74b`; `dev` fast-forwarded to `main`). soorma-core#6 stays
open until Build and Test, with a completion comment linking #16 and #17.

**Next: U4 `env-human-access` (soorma-core#7), in a new session.** Start with:
1. Session resumption (`common/session-continuity.md`); re-intake check: brief still at `0aad84a`,
   no new PF or ID tag, the gap issues' states (soorma-prd#24, #25, #27, #28, #30; #13 for
   GAP-INT-003)
2. Construction Phase Initialization (extension rules; `prd-gap-classification.md` active), then
   Unit Initialization and the L1 gate's initial assessment for U4
3. Toolchain: `node --version` 26.13.0, `pnpm --version` 12.18.0; Docker for the S1 image build.
   The database tests need `pnpm db:test` and the `TEST_DATABASE_URL` it prints

**What U4 inherits from U3** (U3 business-rules §16 and NFR Requirements §4, posted on soorma-core#7):
- Add `evaluateHuman` in P3 (`packages/authority`) through the same seam: `grantedSet(human, E)`,
  then `contains`. No second place computes authority (BR-AU-01; I5)
- Fill P11's human `GrantSource` (`humanGrants` on `createEnvelopeAdmission`): the union of the
  human's grants in E. Human grants are never cached by U3
- S2 emits Problems through P1 (`problemResponse`) and runs `@soorma/perimeter/testing`'s
  `assertProblem` on every Problem (BR-PE)
- **The pre-commit gate builds S1's image** (`docker build -f services/org-gateway/Dockerfile .`)
  for any group whose changes reach S1's dependencies, and a new workspace package S1 reaches is
  added to the Dockerfile's install and source layers (the user, 2026-11-11)
- **Standing note (NFR-AE-16)** above applies to the first unit that changes a standing set,
  declaration, or autonomy, or suspends or retires an agent

**Carried to Build and Test** (from U2): TC-OI-059 and TC-OI-062 (`pnpm test:perf`); on the
workstation, Argon2id at 64 MiB measured about 710 ms late in U2's session, which puts NFR-OI-19's
500 ms p95 for `authenticate` at risk on that machine; the user's "not applicable in M1" decisions
(SECURITY-01 at rest, SECURITY-03's log service, SECURITY-14) and U2's accepted residuals. U4's
obligations from U2 are on soorma-core#7. From U1: Build and Test also uses U1's verification (CI on
soorma-core#12, `pnpm run check:github`), and U1's work-around gaps GAP-INT-003 and GAP-INT-008 stand.
