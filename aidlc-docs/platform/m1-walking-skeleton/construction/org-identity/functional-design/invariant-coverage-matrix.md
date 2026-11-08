# Invariant Coverage Matrix: U2 `org-identity`

**Invariants source**: soorma-prd `references/platform/invariants.md` @ `prd-identity-v1.0`
and @ `prd-platform-foundations-v1.3`. The text is identical at both tags (checked
2026-11-08).
**PRD compliance tables**: ID §15 @ `prd-identity-v1.0` (the main one for this unit); PF §15
@ `prd-platform-foundations-v1.3`. Both mark **I1 to I11 Addressed, none N/A, none Gap**.

**Status values**: `Covered` · `N/A` (with a reason) · `Missing` (blocking). Code Generation
moves rows to `Implemented`; Build and Test to `Verified`.

**Result**: I1 to I10 `Covered`; I11 `N/A`. **0 `Missing`.**

| Code | PRD Status | Applies to Unit | Code-Level Risk in This Unit | Implementation Target | Verification Target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed | Yes | Enrollment or other authentication material reaching an environment's configuration; a sign-in usable as an environment credential; minting material leaving the organization level; one organization's principals reachable through another's gateway | BR-CFG-02 (environment part has no material field); BR-SI-02, 08 (the sign-in asserts no environment); BR-SI-03, BR-INT-03 (verify-only material only); D-OI-21 and BR-RF-01 (another organization is `authentication_failed`). **Access paths**: the org store is reached only by P10, P8, and P9 at the organization level; no environment deployable links P10 (component-dependency.md) | TC-OI-018; QA enrichment: an environment part with material is rejected; the token asserts no environment; a request naming another organization is refused generically; the served material cannot mint | Covered |
| I2 Perimeter enforcement | Addressed | Yes | A check that exists only because a client usually behaves (there is no human SDK, so every caller is raw); a refusal skipped for a familiar client | Every check in S1 itself (business-logic-model §1), schema-driven; no client-supplied claim is trusted | TC-OI-023 (a schema-violating raw request is refused); TC-OI-024 (an altered sign-in is refused) | Covered |
| I3 Portable credential | Addressed | Yes | Trusting an environment's call to the internal interface because it comes from inside the network; deriving the organization from the host; a sign-in asserting a location | BR-INT-02 (a configured per-environment credential, never network location), **implemented as a per-request signed JWS bound to method, full target, and body hash** (NFR Design P-06); D-OI-09 (organization from configuration); BR-SI-02 (no location or code identity asserted) | TC-OI-019; QA enrichment: an internal call without the environment's credential is refused, from any address | Covered |
| I4 Attribution recoverable | Addressed | Yes | A principal pruned, so a sponsor reference no longer resolves; material or a sign-in changed without who did it and when | BR-HP-03 (never pruned); BR-REC-01 to 04 (sign-in, material, and failed-attempt records; human actor, no origin mode); D-OI-07 (no organization-level record in M1, ID FR-018 out) | TC-OI-021, TC-OI-022 | Covered |
| I5 Monotonic authority | Addressed | Yes, narrowly | U2 computes **no** effective authority. The risk is a sign-in or self-service conferring authority, or the seam deciding more than identity | BR-SEAM-02 (identity only); BR-SI-08 (the sign-in serves only self-service at the organization level and issuance in E); BR-MC-06 (self only). No grant, permission, or authority code is in U2 | TC-OI-025; QA enrichment: P6 returns a reference or a rejection and changes no state | Covered |
| I6 Two faces | Addressed | Yes | Serving organization operations and data-plane traffic from one surface; one NFR configuration for both | S1 is control-face only, one deployable, ID §10's profile; the internal interface is a separate listener (BR-INT-01); no data-face operation exists at the organization level | Contract check: `org-gateway.openapi.yaml` holds only S1's five operations; QA enrichment: the internal interface is not on the edge listener | Covered |
| I7 Contract compatibility | Addressed | Yes | Operations or error codes added with no version or classification | `org-gateway.openapi.yaml` under contract 0.1.0 (pre-release); every change classified in `CHANGELOG.md` (business-rules §10); P proofs discriminated by `type`, so a new type is additive | TC-OI-023; U1's compatibility test run over the new document | Covered |
| I8 Packaging rule | Addressed | Yes | A commercial capability (IdP federation, second-factor policy by group or risk) landing in core, enabled or stubbed; an unassigned capability landing in core | Packaging table below: every capability is core in ID §12; none is commercial; nothing unassigned | Packaging table, re-checked at Code Generation and across all units at Build and Test | Covered |
| I9 Mechanism, not instance | Addressed | Yes | A tenant's humans, identifiers, or enrollment material hard-coded in platform code | Every principal comes from configuration (BR-CFG-01, 02); nothing tenant-specific outside labelled test fixtures | Code Generation review; QA enrichment: no fixture identifier outside `test/` | Covered |
| I10 Runtime-later | Addressed | Yes | Organization identity from the deployment or host; the internal interface trusting deployment topology | D-OI-09; BR-INT-02. **Places tempted**: reading the organization from the host name, and trusting an environment because it shares a network. Both are rejected | TC-OI-019; the I3 enrichment case | Covered |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## I8 Packaging Table

ID §12 assigns 49 items to core and 7 surfaces to commercial. Every U2 capability is in the
core list, and lands in `soorma-core`.

| Capability U2 implements | ID §12 assignment | Repository |
|---|---|---|
| Human Principal record and lifecycle (`pending`, `active`) | core: Records (Human Principal) | soorma-core |
| Human Authentication Material, classes K and P | core: Records (Human Authentication Material: K, P, X; X not built) | soorma-core |
| Organization Sign-In | core: Records (Organization Sign-In) | soorma-core |
| The human credential contract: the sign-in at the organization level | core: Contracts (Human credential contract) | soorma-core (`contract/`, Apache 2.0) |
| Authenticate; renew or end one's own sign-in; change one's own material | core: Operations (§8a) | soorma-core |
| Enrollment single use | core: Mechanisms | soorma-core |
| Sign-in abuse bound | core: Mechanisms | soorma-core |
| Second-factor requirement | core: Mechanisms | soorma-core |
| First Admin by configuration (organization half) | core: Mechanisms (first grant and recovery) | soorma-core |
| Settings by configuration (the P requirement) | core: Mechanisms | soorma-core |
| Verify-only sign-in material | core: seam containment, *per-environment issuance; verify-only sign-in material* | soorma-core |
| Identity-resolution seam, human half (K, P) | PF's seam, widened; core default K and K + P | soorma-core (`seams/`, Apache 2.0, unpublished) |

**Not built, and absent from core in any form** (ID §12 commercial): IdP configuration;
federated authentication and SSO; provisioning; the org role model; lifecycle audit;
**second-factor policy by group, condition, or risk** (the core requirement is all-or-none,
BR-CFG-06); cross-environment identity views. No flag, stub, or disabled path for any of
them.

## Invariant Findings

None.
