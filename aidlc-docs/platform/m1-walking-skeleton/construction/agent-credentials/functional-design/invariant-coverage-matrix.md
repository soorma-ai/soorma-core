# Invariant Coverage Matrix: U6 `agent-credentials`

**Invariants source**: soorma-prd `references/platform/invariants.md` @
`prd-platform-foundations-v1.3` and @ `prd-identity-v1.0`. The text is identical at both tags
(re-checked 2026-11-12, at this unit's resumption; both tags at `80dd7c9`).
**PRD compliance tables**: PF §15 @ `prd-platform-foundations-v1.3` (the main one for this unit)
and ID §15 @ `prd-identity-v1.0`: **I1 to I11 Addressed in both, none N/A, none Gap**.

**Status values**: `Covered` · `N/A` (with a reason) · `Missing` (blocking). Code Generation
moves rows to `Implemented`; Build and Test to `Verified`. *QA enrichment* marks a test case the
QA construction enrichment adds before the Construction Design PR gate.

**QA construction enrichment (2026-11-12)**: every *QA enrichment* marker is replaced by its TC id
(`inception/test-cases/agent-credentials/`, TC-AC-001 to 093).

**Result**: I1 to I10 `Covered`; I11 `N/A`. **0 `Missing`.** I1, I2, I3, and I10 are this unit's
centre: per-environment credentials, revocation, and cache; raw-call enforcement at a new
surface; the credential as the only identity input; the instance asserted, never verified.

**Updated at NFR Design (2026-11-12)**: no status changed. I1's access paths gain their
physical form (every new table with E's three columns; foreign keys keeping revocations and
failed attempts within E; the cache key with E; one `attempt_slots` table and counter secret per
environment; NP-AC-03 to 07). I4 gains `0004`'s CHECK (NP-AC-02). I5 and I8 gain the closure
checks in the manifests and the images, S2's included (NP-AC-10). I7 gains the published numbers
tested against the code constants (NP-AC-01).

**Code Generation (2026-11-12)**: I1 to I10 `Implemented`; I11 N/A. The I8 packaging table
re-checked (TC-AC-046): every capability core-assigned; no revocation initiation, rotation
surface, or seeding path in any image.

| Code | PRD Status | Applies to Unit | Code-Level Risk in This Unit | Implementation Target | Verification Target | Status |
|---|---|---|---|---|---|---|
| I1 Isolation | Addressed | **Yes** | A credential, revocation, slot, or failed-attempt read with no environment constraint; a cache key without E; a token verified with another environment's keys; one key ring shared across environments | **Access paths** (all in E's own store; every row with the three columns, every statement constrained on them, U4 D-EHA-29): the registration and secret read at bootstrap (BR-BS-03); the credential record write and read (BR-BS-06, BR-RN-02); revocation reads, direct and cached (BR-RV-03, BR-RC-04); the bound's slots (BR-AB-AC-05); failed attempts (BR-FA-01); attribution (U4's). Tokens: E's agent key ring only (BR-CR-AC-02) | TC-AC-013; TC-AC-020; TC-AC-033, TC-AC-034, TC-AC-078 (assigned at QA construction enrichment, 2026-11-12): one test per access path that a principal of E cannot read, write, or be refused by anything of E2's (records, revocations, slots, failed attempts, cache entries) | Verified |
| I2 Perimeter enforcement | Addressed | **Yes** | A check relying on the SDK (lineage cap, instance, binding); S3 trusting a token because S4 accepted it; a bootstrap check skipped for "our" clients | Every check runs at S3 from the raw request (business-rules §10); renewal copies the binding from the verified token, never from the request (BR-RN-08); `checkAgentRequest` runs independently per surface (D-AC-27) | TC-AC-021; TC-AC-042, TC-AC-093 (assigned at QA construction enrichment, 2026-11-12): every refusal of §7 of the business logic model sent as a raw call, and *done when* 2 by raw calls (D-AC-31) | Verified |
| I3 Portable credential | Addressed | **Yes** | Identity taken from a source address, host, or network position; bootstrap trusted from inside the stack's network; the instance taken from where the call comes from | The agent is the verified secret's registration (BR-BS-03); the instance is the asserted field (D-AC-23); renewal's identity is the verified token only (BR-RN-01). Nothing reads a source address, hostname, or deployment label | TC-AC-043, TC-AC-031 (assigned at QA construction enrichment, 2026-11-12): the same secret and the same credential from another source address give the same identity; a renewal with no credential from inside the stack's network is refused | Verified |
| I4 Attribution recoverable | Addressed | **Yes** | A bootstrap or renewal without its attribution record; the sponsor not resolvable; a record whose missing chain and origin cannot be told apart from an omission | One record per success, in the same transaction (D-AC-21); agent actor with registration, instance, resolved sponsor; **the operation states why there is no chain or origin** (BR-AT-AC-02), enforced by P7's envelope-free list (D-AC-33); sponsorship two hops through a registration never deleted (BR-AT-AC-03). The revocation read writes none (GAP-INT-009, D-AC-17) | TC-AC-005; TC-AC-019; TC-AC-035, TC-AC-036 (assigned at QA construction enrichment, 2026-11-12): reconstruct scope, actor, instance, and sponsor, and the reason for no chain or origin, from the record alone; a failed attribution write leaves no credential | Verified |
| I5 Monotonic authority | Addressed | Yes | Renewal widening the binding (another agent, instance, or environment), or extending past revocation or the lineage end; a credential carrying permissions; origin assumed at bootstrap | Renewal copies the binding (BR-RN-08) and keeps the `cid` (D-AC-14); the token carries no permission (BR-CR-AC-01); no origin at bootstrap or renewal (O12 excluded, D-AC-28). **No effective authority is computed in U6**: P3 stays the one place (U3); S3 imports no evaluator | TC-AC-016; TC-AC-040 (assigned at QA construction enrichment, 2026-11-12): S3 imports nothing from `packages/authority` | Verified |
| I6 Two faces | Addressed | **Yes** | A control-face operation on S3; a human credential accepted at S3; an agent operation on S2; one NFR configuration for both faces | S3 is data-face only, in its own contract document (business-rules §12); its own NFR profile (PF §9) and throttle values (D-AC-29); human credentials refused by kind (D-AC-10) | TC-AC-012; TC-AC-021; TC-AC-044 (assigned at QA construction enrichment, 2026-11-12): `data-gateway.openapi.yaml` holds no control-face operation, and S2's holds no data-face one | Verified |
| I7 Contract compatibility | Addressed | Yes | A new surface or a widened code unclassified; the instance clarification read as a breaking change | business-rules §13: a new surface document, `authentication_failed` widened, `identifiers.md` clarified, the bound published, all compatible, recorded in `contract/CHANGELOG.md` | TC-AC-021; TC-AC-045 (assigned at QA construction enrichment, 2026-11-12): U1's compatibility check over the changed contract | Verified |
| I8 Packaging rule | Addressed | **Yes** | A revocation initiation surface (deferred, core) or secret rotation built partly, flagged, or stubbed; the test-only seeding fixture compiled into the product; anything unassigned | Packaging table below; D-AC-16; BR-RV-05 | TC-AC-046 (assigned at QA construction enrichment, 2026-11-12): the packaging table re-checked at Code Generation and Build and Test; the seeding fixture is absent from every built image | Verified |
| I9 Mechanism, not instance | Addressed | Yes | A tenant's agent or instance names hard-coded | Agent and instance identifiers come from requests and records; test fixtures labelled as such | TC-AC-047 (assigned at QA construction enrichment, 2026-11-12) (Code Generation review, with a check) | Verified |
| I10 Runtime-later | Addressed | **Yes** | The instance identifier verified or derived from the runtime (a pod name, a host); a credential claiming code identity; scoping keyed on deployment topology | The instance is asserted and recorded, never verified (D-AC-23, 07); the token asserts registration, not code identity (BR-CR-AC-01); environment from configuration (D-AC-09). **Places tempted**: deriving `instance` from the caller's host; refusing a reused instance name (D-AC-07 chose not to) | TC-AC-002; TC-AC-024, TC-AC-041 (assigned at QA construction enrichment, 2026-11-12): two instances asserting one name both work; nothing reads a host, cluster, or deployment label | Verified |
| I11 No technology selection | Addressed | N/A | — | — | — | N/A: Construction is where technology is selected |

## I8 Packaging Table

PF §12 assigns 52 items to core and 8 to commercial; ID §12, 49 and 7. Every U6 capability is a
core item, and lands in `soorma-core`.

| Capability U6 implements | Assignment | Repository |
|---|---|---|
| The bootstrap exchange, with its abuse bound and failed attempts recorded | PF §12 core: operation (§8a *Exchange bootstrap material*); FR-009, FR-027 | soorma-core |
| Credential renewal | PF §12 core: operation (§8a *Renew credential*); FR-010 | soorma-core |
| The agent credential and its record | PF §12 core: record (*Agent Credential*) | soorma-core |
| The revocation read, its state record, and the fail-closed cache with a published bound | PF §12 core: record (*Revocation State*); operation (§8a *Read revocation state*); FR-012 | soorma-core |
| The identity-resolution seam's agent half (types) and its default implementation | PF §12 seam (Apache 2.0 interface) and core default; FR-026 (publication absent in M1, M1-FR-13) | soorma-core |
| Attribution of bootstrap and renewal | PF §12 core (record) | soorma-core |
| The bootstrap bound's numbers (window, live attempts, backoff; NFR Requirements) | **A security bound, not a tenant quota**: PF FR-027 requires attempt volume per registration bounded; platform constants, not configuration, governing no tenant's capacity | soorma-core |

**Not built, and absent from core in any form**: revocation initiation (PF FR-011, core, deferred
in M1; only a test-only fixture, outside the product's build, writes revocation state); secret
rotation and retirement (core, absent from M1); anything commercial. No flag, stub, or disabled
path for any.

## Invariant Findings

None.

**Build and Test (2026-11-13)**: I1 to I10 `Verified` against the stage run (every suite, the e2e proofs on a fresh stack, the smoke and outage runs, the image checks). Evidence per row: [`../../build-and-test/invariant-conformance-test-instructions.md`](../../build-and-test/invariant-conformance-test-instructions.md).
