# AI-DLC State Tracking

## Project Information
- **Project**: soorma-core: M1 walking skeleton (server side)
- **Project Type**: Greenfield
- **Start Date**: 2026-10-05T02:24:31Z
- **Current Stage**: INCEPTION - Requirements Analysis (requirements.md written; awaiting approval)
- **Slice brief**: soorma-prd/backlog/m1-walking-skeleton.md (`soorma-core` column of *Repositories and sessions*)
- **Requirements depth**: Comprehensive (irreversible core assignments, security boundary, a contract other sessions consume)

## Workspace State
- **Existing Code**: No (README, licence, contributor documents, and `.github/` only)
- **Programming Languages**: None yet
- **Build System**: None yet
- **Project Structure**: Empty
- **Reverse Engineering Needed**: No
- **Workspace Root**: . (repo root: soorma-core)
- **Context-only repositories**: soorma-sdk (empty; consumes this initiative's wire contract), soorma-prd (PRD and brief)

## Code Location Rules
- **Application Code**: . (repo root; NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/platform/m1-walking-skeleton/ only
- **Structure patterns**: See code-generation.md Critical Rules
- **Path Convention**: All paths are relative to repo root; never use absolute or machine-specific paths

## PRD Intake

- **PRD**: soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md
- **Version**: 1.1
- **Built against**: `prd-platform-foundations-v1.1` (commit `cef399f451e4a3cb0be5bed92586383cbf148afc`)
- **Kind**: plane (inferred because the header declares none; confirmed by the user)
- **Status verified**: Approved (2026-09-10, via soorma-prd PR #4, merge `b5527a8`)
- **Coverage map**: inception/prd-intake/prd-coverage-map.md
- **L1 sources**: §7a, §7b, §6, §8a, §8b, §9, §10, §11, §17, FR-025
- **Stages satisfied**: None fully. Requirements Analysis, User Stories, Application Design, and Units Generation are all Partial
- **Intake approval**: Approved (RA Q1, 2026-10-05T03:13:21Z)

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis (Q10) |
| soorma Platform Invariants | Yes | Requirements Analysis (Q11). Scope inherited from PRD §15: I1 to I11 all Addressed, none N/A; invariants read at `prd-platform-foundations-v1.1` |
| PR Checkpoint | Yes | Requirements Analysis (Q12) |
| QA Test Cases | Yes | Requirements Analysis (Q13). Opted in — scope: comprehensive |
| JIRA Tickets | Yes, adapted: **GitHub issues on soorma-core instead of JIRA** | Requirements Analysis (Q14; clarification Q3). At the end of Inception, before the PR checkpoint: one tracking issue plus one sub-issue per unit. **No markdown ticket file**; issue numbers are recorded under `## Tickets` below |

## PRD Specification Gaps

Raised at intake, before any unit exists, so the full entries live in
`inception/prd-intake/prd-coverage-map.md` rather than in a per-unit `prd-gaps/` file.

| ID | Unit | Summary | Status | Raised Against | Issue |
|---|---|---|---|---|---|
| GAP-INT-001 | (pre-unit) control-face registration | Human principal identity and control-plane authentication (OB-4) | Open: raised, **blocking** | `prd-platform-foundations-v1.1` | soorma-prd#12 |
| GAP-INT-002 | (pre-unit) control-face registration | First human grant; how a sponsor obtains `agent:register` (OB-3, R-2) | Open: raised, **blocking** | `prd-platform-foundations-v1.1` | soorma-prd#12 |
| GAP-INT-003 | (pre-unit) event transport | Event delivery guarantees (Event plane, §2) | Open: raised; worked around in M1 (live subscribers only, pre-release contract) | `prd-platform-foundations-v1.1` | soorma-prd#13 |
| GAP-INT-004 | (pre-unit) perimeter authority | Re-broadening evaluation rule (FR-017, I5) | Open: raised; worked around in M1 (declaration *none* only) | `prd-platform-foundations-v1.1` | soorma-prd#14 |
| GAP-INT-005 | (pre-unit) control-face registration | Meaning of the sponsor's "grantable set" (FR-016); reclassified from T-1 at RA Q6 | Open: raised, blocking the ceiling check (already blocked by #12) | `prd-platform-foundations-v1.1` | soorma-prd#14 (with GAP-INT-004) |

**Errata (not a gap)**: E-1, §17 and §4 counts. soorma-prd#15, non-blocking.

## Tickets

*Created at the end of Inception.*

## Deferred Questions

| ID | Question | Deferred To | Reason | Source | Status |
|---|---|---|---|---|---|

*None. The PRD's OQ-1 to OQ-14 are all Answered at the tag, so none were imported.*

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection (greenfield)
- [x] PRD Intake (approved at RA Q1)
- [ ] Reverse Engineering: SKIPPED (greenfield)
- [ ] Requirements Analysis: requirements.md written; **awaiting approval**
- [ ] User Stories
- [ ] Workflow Planning
- [ ] Application Design
- [ ] Units Generation

**Session stop point**: by the user's instruction, this session stops after Requirements
Analysis for review of the gap classification.
