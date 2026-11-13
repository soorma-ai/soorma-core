# Invariant Coverage Matrix: U1 `wire-contract`

**Invariants source**: soorma-prd `references/platform/invariants.md` @ `prd-platform-foundations-v1.3` and @ `prd-identity-v1.0` (identical text)
**PRD compliance tables**: PF §15 @ `prd-platform-foundations-v1.3`; ID §15 @ `prd-identity-v1.0`. All eleven are `Addressed` in both; none is N/A

**Status values**: `Covered` / `N/A` (with a reason) / `Missing` (blocking) /
`Implemented` / `Verified`.

| Code | PRD status | Applies to unit | Code-level risk in this unit | Implementation target | Verification target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed (PF, ID) | Yes | A contract identifier or envelope that is not scoped to an environment; a forwarded envelope accepted across environments | `scope` `{ organization, project, environment }` (D-WC-04); identifiers composed with scope (BR-ID-07); the seal bound to the environment's own material (BR-FC-01 to 03); `credential_expired` only after verification in this environment (BR-ERR-02) | U3: a seal from E2 is refused in E; U7 *done when* 6 e2e | Verified (U1 part: `scope` and the environment-bound seal rules in the contract); verified by U3, U7 |
| I2 Perimeter enforcement | Addressed | Yes | A contract rule that only the SDK keeps; a field trusted because a client built it; a credential prefix that admits | Every rule stated as perimeter-enforced; the draft closed (BR-DR-01); forwarded context verified by seal, never trusted (D-WC-06); the prefix never admits (BR-CR-04) | Raw-call e2e (U5 to U7); U3 forged-`inbound` test; cumulative SDK check at Build and Test | Verified (U1 part: closed draft, stamped fields forbidden by name, prefix never admits); verified by U3, U5 to U7 and the cumulative check at Build and Test |
| I3 Portable credential | Addressed | Yes | A contract field carrying network location or host identity as an identity input | Credentials presented as bearer tokens only (BR-CR-01); no location field anywhere in the contract; the instance identifier is asserted, not identity (domain-entities *Actor Reference*) | Review at Code Generation; U6 *same credential from another origin* test | Verified; reviewed at Code Generation: no location or host field anywhere in the contract; bearer presentation only. Runtime test by U6 |
| I4 Attribution recoverable | Addressed | Yes | An envelope shape that conflates scope with delegation; a chain an agent can invent or alter | Scope, actor chain, and origin are separate fields (BR-ENV-01); `delegatingPrincipal` separate from the chain; sponsorship resolvable through `actorChain[i].agent` (BR-ENV-09). **The seal (D-WC-06) guarantees that a forwarded chain prefix was stamped by this environment's perimeter and is unaltered, so no hop in it is invented.** It does **not** guarantee that the forwarder was delivered that envelope, or that it is recent: the causal link from the prefix to the new hop is not proven (accepted residual, business-rules.md Section 14) | U3 reconstruction from the envelope at 0 hops and across a chain; U3 forged and altered `inbound` refused; U7 *done when* 4 | Verified (U1 part: separate scope, chain, origin, delegating principal; sealed forwarding stated); verified by U3, U7 |
| I5 Monotonic authority | Addressed | Yes | A draft that sets origin or the re-broadening record; a request for re-broadening over the wire; a forged upstream chain | Origin, chain, and `reBroadening` platform-stamped and rejected from drafts (BR-DR-02, 03); no request field for re-broadening; the forwarded chain sealed (BR-FC-01). U3 is the single computation point | U3 tests: origin unchanged after N hops; low-authority caller | Verified (U1 part: origin, chain, and re-broadening stamped and refused in drafts); verified by U3 |
| I6 Two faces | Addressed | Yes, for the contract layout | One surface document mixing data-face and control-face operations | Each surface document belongs to one face: S1, S2 control; S3, S4 data (Application Design). U1's shared conventions hold no operation | Review at Code Generation (U2 to U7) | Verified; reviewed at Code Generation: the shared components hold no operation (`paths: {}`); surface documents arrive with U2 to U7 |
| I7 Contract compatibility | Addressed | **Yes, primarily** | An unversioned schema; an untested change; a server assuming every SDK upgraded | SemVer contract version (D-WC-02); client contract version on every call (BR-VER-02); acceptance of every version ever accepted (BR-VER-03); classification of every change (BR-VER-05); open enums and unknown fields (BR-ENV-05, 06); envelope v1 fixed (D-WC-03) | TC-WC-030, 031 (compatibility over the fixture corpus); TC-WC-008, 010, 017, 021, 032 | Verified: SemVer contract version, accepted set, change classification, the 0.1.0 fixture corpus, and the compatibility test (TC-WC-030, 031) |
| I8 Packaging rule | Addressed | Yes | A commercial capability, or one with no assignment, in `contract/`; the wrong licence | Packaging table below; `contract/` Apache 2.0 (BR-LG-01) | TC-WC-011; packaging table re-checked at Code Generation | Verified: `contract/` Apache 2.0 with SPDX on every file (TC-WC-011); packaging table re-checked below |
| I9 Mechanism, not instance | Addressed | Yes | A tenant schema, payload rule, or identifier in the contract | `payload` any JSON value, never inspected (BR-DL-03); no tenant-specific name or constant; test fixtures labelled | Review at Code Generation | Verified; reviewed at Code Generation: `payload` any JSON value; no tenant name or constant; fixture values are labelled test data (`o1`, `agent-a`) |
| I10 Runtime-later | Addressed | Yes | A contract field claiming code identity or attestation; scoping keyed on deployment | The instance identifier asserted, not verified; `scope` configured, never inferred (D-WC-04); the seal proves the platform stamped the envelope, not what code runs | Review at Code Generation | Verified; reviewed at Code Generation: the instance identifier is asserted; nothing claims code identity or attestation |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## Code Generation (2026-11-08)

Every row's U1 target is built in `contract/`; rows whose runtime verification belongs to a later
unit name it. The I8 packaging table below was re-checked against what was built: everything in
U1 is the contract (`contract/`, Apache 2.0) or repository tooling (`tools/`, the root FSL licence),
and nothing commercial exists in any form. `tools/` implements no product capability: it checks
the repository's own dependencies and workflows.

## I10: Places That Would Have Been Tempted

- The actor reference could have carried a verified workload identity. It carries the
  asserted instance identifier only
- The seal could have been presented as an attestation of the agent. It is an integrity
  check by the platform, of the platform's own stamp

## I8 Packaging Table (U1)

| Capability implemented in U1 | PRD assignment | Edition | Licence | Repository |
|---|---|---|---|---|
| Envelope definition (machine-readable) | PF FR-001 to FR-006, §7b; PF §22 | core | Apache 2.0 | soorma-core `contract/` |
| Delivery definition | Part of the envelope-bearing contract (PF §7b; Application Design) | core | Apache 2.0 | soorma-core `contract/` |
| Contract conventions: versioning, errors, security schemes, statements | The wire contract (brief: owned by soorma-core; PF §14, §17) | core | Apache 2.0 | soorma-core `contract/` |
| Generated types | M1-TECH-02 | core | Apache 2.0 | soorma-core `contract/generated/` |
| Repository checks (dependency register, licences, workspace configuration, workflows) | Build tooling, not a product capability (M1-TECH-04) | core | FSL-1.1-ALv2 | soorma-core `tools/` |

No commercial capability exists in U1 in any form, enabled or not. No capability without
an assignment lands in `contract/`.

**Build and Test (2026-11-13)**: I1 to I10 `Verified` against the stage run (every suite, the e2e proofs on a fresh stack, the smoke and outage runs, the image checks). Evidence per row: [`../../build-and-test/invariant-conformance-test-instructions.md`](../../build-and-test/invariant-conformance-test-instructions.md).
