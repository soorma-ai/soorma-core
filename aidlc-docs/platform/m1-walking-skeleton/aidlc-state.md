# AI-DLC State Tracking

## Project Information
- **Project**: soorma-core: M1 walking skeleton (server side)
- **Project Type**: Greenfield
- **Start Date**: 2026-10-05T02:24:31Z
- **Milestone**: M1, Walking skeleton (from the slice brief; matches `aiprd-docs/build-sequence.md`)
- **Current Stage**: INCEPTION. User Stories (minimal depth): changes requested; GAP-INT-007 classified, routing pending
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
- **Status**: NOT YET FIRED (fires after Units Generation, the GitHub-issue tickets, and the QA inception test specs; before Construction)
- **PR**: **soorma-core#2** (`dev` → `main`), by the user's instruction (2026-11-02). Use it instead of opening a new PR or creating an `aidlc/.../inception` branch. At the gate, **update #2's description** per `pr-checkpoint.md` Section 4.2. #2 stays open until the gate is approved; this supersedes the earlier "merge after RA" note
- **Branch**: `dev`
- **Instructions**: — (written at the gate)
- **Approved**: —

## PRD Specification Gaps

Full entries: `inception/prd-intake/specification-gaps.md`.

| ID | Unit | Summary | Status | Raised Against | Resolved By | Issue |
|---|---|---|---|---|---|---|
| GAP-INT-001 | (pre-unit) | Human principal identity and control-plane authentication (OB-4) | Resolved — answered elsewhere | PF @ `prd-platform-foundations-v1.1` | ID @ `prd-identity-v1.0` FR-001, FR-006, FR-009, FR-010, FR-022 | soorma-prd#12 |
| GAP-INT-002 | (pre-unit) | First human grant; how a sponsor obtains `agent:register` (OB-3, PF R-2) | Resolved — answered elsewhere | PF @ `prd-platform-foundations-v1.1` | ID @ `prd-identity-v1.0` FR-004, FR-007, FR-015 | soorma-prd#12 |
| GAP-INT-003 | (pre-unit) | Event delivery guarantees (Event plane) | **Awaiting PRD: Event**. Worked around in M1 (live subscribers only; semantics stated as unspecified; pre-release contract) | PF @ `prd-platform-foundations-v1.1` | — | soorma-prd#13 |
| GAP-INT-004 | (pre-unit) | Re-broadening evaluation rule (PF FR-017, I5) | Resolved — PRD amended. **Work-around comes out** | PF @ `prd-platform-foundations-v1.1` | PF @ `prd-platform-foundations-v1.3` FR-017, §8b *Re-broadening* (v1.2) | soorma-prd#14 |
| GAP-INT-005 | (pre-unit) | Meaning of the sponsor's "grantable set" (PF FR-016) | Resolved — PRD amended | PF @ `prd-platform-foundations-v1.1` | PF @ `prd-platform-foundations-v1.3` FR-016, §8b *Sponsorship* (v1.2); ID @ `prd-identity-v1.0` FR-015 for `grant:human` | soorma-prd#14 (re-routed half: #12) |
| GAP-INT-006 | (pre-unit) | Which permissions are *valid in E* (ID FR-015's ceiling); tenant-defined identifiers in core | Open: raised; worked around in M1 (plane-declared identifiers only; re-intake Q2, routing E) | ID @ `prd-identity-v1.0` | — | soorma-prd#24 |
| GAP-INT-007 | (pre-unit) | Origin at an autonomous first hop: agent-asserted (PF §8b) or platform-stamped (PF §11, FR-015, §7b); found at User Stories | Classified as specification; **routing pending**; worked around in M1 (reject and stamp, M1-FR-01) | PF @ `prd-platform-foundations-v1.3` | — | (pending) |

**Counts**: Open 1 (GAP-INT-006, worked around) · Awaiting PRD 1 (GAP-INT-003, worked around) · Resolved 4 · Routing pending 1 (GAP-INT-007, worked around).

**Errata (not a gap)**: E-1, PF §17 and §4 counts. soorma-prd#15, closed. Corrected at PF v1.2.

## Tickets

*Created at the end of Inception.*

## Deferred Questions

| ID | Question | Deferred To | Reason | Source | Status |
|---|---|---|---|---|---|

*None. PF OQ-1 to OQ-14 and ID OQ-1 to OQ-6 and P1-OQ-1 to P7-OQ-2 are all Answered at their tags, so none were imported.*

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection (greenfield)
- [x] PRD Intake (run 1 approved at RA Q1; run 2 approved at re-intake Q1, 2026-11-01)
- [ ] Reverse Engineering: SKIPPED (greenfield)
- [x] Requirements Analysis (run 1 approved 2026-10-06; re-opened by re-intake run 2; run 2 approved 2026-11-02)
- [ ] User Stories: generated (minimal depth; plan approved 2026-11-02), **awaiting approval**
- [ ] Workflow Planning
- [ ] Application Design
- [ ] Units Generation

**Session stop point**: User Stories approval gate. Next, once approved: Workflow Planning.
