# PRD Coverage Map

**Entry point**: slice brief
**Slice brief**: soorma-prd/backlog/m1-walking-skeleton.md @ `0aad84a27c94d8f6d7064c312aaaa2e553d162dd` (Status: Ready)
**Milestone**: M1, Walking skeleton
**Scope**: `soorma-core` column of *Repositories and sessions*
**Intake run**: 2, 2026-11-01T21:12:26Z (re-intake; run 1 was 2026-10-05T02:26:06Z against PF @ `prd-platform-foundations-v1.1`, with no brief pin recorded)

> The PRDs state the **target**. The slice brief decides only **delivery scope**.
> Where they appear to conflict, the PRD wins.

**ID note**: every PRD-scoped ID in this document is qualified by its key: **PF** for
`platform-foundations`, **ID** for `identity`. Unqualified IDs in artifacts dated before
run 2 refer to PF. Cross-PRD obligations (`OB-n`) and invariants (`I1` to `I11`) are global
and stay unqualified.

**Specification gaps** found at intake are in
[specification-gaps.md](specification-gaps.md). The coverage map links to them and does
not repeat them.

---

## PRDs

| Key | PRD | Version | Built against | Commit | Kind | Status verified | Review PR |
|---|---|---|---|---|---|---|---|
| PF | soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md | 1.3 | `prd-platform-foundations-v1.3` | `80dd7c98e81702bb38dece9249372ea27b0555f9` | `plane` (declared since v1.2; matches the brief) | Approved: header (2026-09-10, PR #4), amendment sign-offs v1.2 (PR #19) and v1.3 (PR #21) | #4 (v1.0), #5 (v1.1), #19 (v1.2), #21 (v1.3) |
| ID | soorma-prd/aiprd-docs/identity/requirements/prd.md | 1.0 | `prd-identity-v1.0` | `80dd7c98e81702bb38dece9249372ea27b0555f9` | `plane` (declared; matches the brief) | Approved: header (2026-10-26, PR #21) | #21 |

Both tags sit on the same merge commit, the merge of soorma-prd PR #21. At each tag, the
`**Version**:` field matches the version in the tag name.

**Run 1** was built against PF @ `prd-platform-foundations-v1.1` (`cef399f`). PF moved
v1.1 → v1.3 by **delta intake**, and ID was added by **full intake** (Step 9.3).

---

## Cross-PRD Checks

| Check | Result | Decision |
|---|---|---|
| Upstream consistency: ID declares an upstream PRD | ID declares PF @ `prd-platform-foundations-v1.3`. The brief draws on PF @ `prd-platform-foundations-v1.3`. **Consistent** | Not asked |
| Newer approved tag than the brief cites | **None**. Latest PF tag is `prd-platform-foundations-v1.3`; latest ID tag is `prd-identity-v1.0` | Not asked |
| Milestone against `build-sequence.md` (origin/main) | **Matches**. M1 exists, its *Slice brief* links to this brief, and it names both tags | Not asked |
| Invariants text at each PRD's tag (platform-invariants extension) | `references/platform/invariants.md` is **identical** at `prd-platform-foundations-v1.1`, `-v1.3`, and `prd-identity-v1.0` | No halt needed |
| A brief–PRD conflict | **None found**. The brief's ID rows match ID's FRs; PF rows unchanged from run 1 | — |

---

## Slice Scope for This Repository

From the brief's `soorma-core` column at `0aad84a`. Run 1 recorded no brief pin, so this
scope is treated as **entirely new** (Step 9.2): nothing below is assumed to have been
assessed before. Run 1 most likely read the brief at `c1abc32` (the last commit to it
before 2026-10-05). Diffed against that commit, the changes are the human side in *Builds*,
the ID requirements, and two ID *decide at intake* items. The PF requirement list, *Owns*,
and *Proves* are unchanged.

| | |
|---|---|
| **Builds** | Everything server-side: the perimeter (O1 to O12) at every entry point, registration, secret issuance, bootstrap and its abuse resistance, renewal, the revocation read, the authority algebra and minimal model, envelope stamping and validation, event transport within an environment, attribution recording, environment configuration; **and the human side**: the configured first Admin, the organization level with sign-in and its abuse resistance, environment credential issuance, the `grant:human` ceiling, human credentials at the perimeter |
| **Requirements** | PF FR-001 to FR-003, FR-005 to FR-010, FR-012, FR-014 to FR-018, FR-020 to FR-022, FR-025, FR-027; **ID FR-001, FR-004, FR-006 to FR-010, FR-013, FR-015, FR-022, FR-023** |
| **Owns** | **The wire contract** between an agent and the platform: every request and response the SDK will call. At v1.3 it also covers the human operations M1 builds (sign-in, environment credential issuance, grant to a human, registration by a human), which carry no envelope (PF FR-001) |
| **Consumes** | — |
| **Proves** | *Done when* 1, 4, 6, 7, plus 2 and 3 **with raw calls and no SDK**. Item 5 (trace emission) is `soorma-sdk`'s |

| In scope for this repository | Out of scope (absent, not simplified) |
|---|---|
| PF FR-001, FR-002, FR-003, FR-005, FR-006; PF §7 (envelope) | PF FR-004 transition machinery (the version field itself is in) |
| PF FR-007, FR-016 (registration, sponsorship ceiling) | PF FR-008 rotation and retirement |
| PF FR-008 issuance only, **with the issuer recorded** (PF §7a v1.3) | PF FR-011 initiation surface (decided at run 1, RA Q7; re-confirmed at RA) |
| PF FR-009, FR-027 (bootstrap and its abuse resistance) | PF FR-013 retention and pruning |
| PF FR-010 (renewal) | PF FR-019 (obligations on Access Policy) |
| PF FR-012; O3 (revocation read on every request) | PF FR-023 harness surface (`soorma-sdk`) |
| PF FR-014, FR-015, FR-017, FR-018 (algebra, minimal model) | PF FR-024 portal |
| PF FR-020; O1 to O12, §8 (perimeter at every M1 entry point) | PF FR-025 read surface (recording is in) |
| PF FR-021, FR-022 (environment keying; configured identity) | Everything commercial (PF §12) |
| PF FR-025 attribution **recording** | ID FR-002, FR-003, FR-012, FR-016, FR-017 (further humans, lifecycle, others' credentials, grant revocation, directory) |
| ID FR-001 (human principal; states `pending`, `active`) | ID FR-005, FR-024, FR-025, FR-027 external types (org settings, configured sources, mappings, federation) |
| ID FR-004 (configured tenancy; first Admin with `grant:human`, `human:manage`) | ID FR-014, FR-018 (coverage; org-level attribution) |
| ID FR-006 (**K**, verified at the organization level only) | ID FR-019, FR-020, FR-021, FR-028 (delegation) |
| ID FR-007 (single-use enrollment material for the first Admin) | ID FR-026 (a deactivated sponsor's secrets) |
| ID FR-008 (sign-in abuse resistance) | ID FR-029 (portal) |
| ID FR-009 (organization sign-in; verify-only material in environments) | |
| ID FR-010 (environment credential; accepted only in E; renewable) | |
| ID FR-013 (`human:manage`, `agent:delegate` human-only) | |
| ID FR-015 (the `grant:human` ceiling; self-grants recorded) | |
| ID FR-022, FR-023 (human credentials at the perimeter; no envelope on direct human operations; Event ingest refuses human credentials) | |

| Decide at intake | Decided in |
|---|---|
| PF FR-011: revocation initiation now, or O3 reading state nothing yet writes | Requirements Analysis, run 1 (RA Q7: **B**, defer initiation; tests seed state through a test-only path). Unchanged at v1.3; re-confirmed when RA re-runs |
| PF FR-026: seams from the start, or later | Requirements Analysis, run 1 (RA Q8: **B**, internal boundary only). **PF §12 changed at v1.3** (identity-resolution seam widened to human material). Re-confirmed when RA re-runs |
| ID FR-006: ship P and the organization's second-factor requirement in M1, or K only (P additive later) | **Requirements Analysis, re-run** (new at run 2) |
| ID FR-011: ship self-service (ending one's own sign-in or credential, changing one's own material) now, or later | **Requirements Analysis, re-run** (new at run 2) |

---

## Stage Coverage

| Inception Stage | Coverage | Source | Still Needed |
|---|---|---|---|
| Requirements Analysis | **Partial**. **Re-opened by re-intake (run 2)** | PF §5 FRs and §6 to §11 for the in-scope FRs; ID §5 FRs and §6 to §11 for the in-scope FRs; brief for delivery scope | Scoped re-run: see *Stages Re-opened* below |
| User Stories | **Partial** | PF §3 and ID §3 (personas, including *First Admin of an environment*); brief *Done when* items; ID §1 trace of item 1 | Assessed at the User Stories gate. Personas are settled and must not be re-derived |
| Application Design | **Partial** | PF §2 seams, §11 *Gateway Exposure*, §12 containment (widened at v1.3); ID §2 seams, §12 containment; ID FR-009 (organization level outside every environment, on no per-request path) | Components, the wire contract, and internal structure are AI-DLC's (I11). Both PRDs' placement constraints bind |
| Units Generation | **Partial** | PF §9, §10 and ID §9, §10 split owned operations by face; both PRDs are `plane`, so plane-face units apply to every unit | Unit boundaries. A capability spanning both faces (for example, the human environment credential, ID FR-010 *Face: both*) becomes two units |

---

## Stages Re-opened (run 2)

Per Step 9.6, an approved stage is re-opened only as far as the change reaches.
**Only Requirements Analysis was approved**, so it is the only stage affected. User
Stories and later stages have not started.

| Stage | Re-opened for | Requirements touched |
|---|---|---|
| Requirements Analysis | (a) Requirements citing PF sections changed v1.1 → v1.3 | M1-FR-01 (PF FR-001: agent-originated traffic only; PF §7b re-broadening record), M1-FR-03 (PF FR-016, FR-017, §7a), M1-FR-04 (PF §7a issuer), M1-FR-05 (unauthenticated-surface wording, see A-6), M1-FR-08 (PF §8b origin table, re-broadening, sponsorship), M1-FR-09 (direct human operations: O5 to O7 N/A), M1-FR-10 (PF §6 verify-only), M1-FR-12 (attribution names the human; *granted-by* may name configuration), M1-FR-13 (PF §12 seam widened) |
| | (b) Requirements blocked by, or worked around for, gaps now resolved | §2 *Status of the Outcome* (the #12 block is lifted); M1-FR-03 (GAP-INT-001, 002, 005 blocks lifted; GAP-INT-004 work-around **comes out**); M1-FR-08 (GAP-INT-004 work-around comes out); §6 *Open Specification Gaps* |
| | (c) Scope that is new from Step 9.2 | New requirements for ID FR-001, FR-004, FR-006 to FR-010, FR-013, FR-015, FR-022, FR-023; *decide at intake* ID FR-006 and ID FR-011; re-confirmation of PF FR-026 (seam widened) |
| | (d) A gap new at run 2 | GAP-INT-006 routing and its effect on the grant and standing-set input rules |
| | (e) Extension compliance at RA | SECURITY-12 is no longer partly blocked (human authentication is specified); invariant scope now inherited from **both** PRDs' §15 (all eleven Addressed in each) |

M1-TECH-01 to 05, M1-NFR-01 to 07, M1-FR-02, 06, 07, 11 are not touched beyond ID
qualification. They are carried forward unchanged unless the re-run finds otherwise.

---

## L1 Domain Sources

Registered for the per-unit L1 Domain Coverage Gate. Each is read at its PRD's
`Built against` tag. These are the most authoritative L1 sources available and outrank
anything re-derived.

| Source | Content | Applies To |
|---|---|---|
| PF §7a *Platform-Owned Records* | Logical Agent Registration (8 required attributes; states `registered`, `suspended`, `retired`; retirement never deletes; **snapshot = held set**; **re-broadening declaration ⊆ standing set**), Agent Credential, Revocation State (readable by no principal), Permission Grant (**granted-by may name configuration**, v1.3), Registration Secret (**records its issuer**, v1.3) | Registration, credential, revocation, grant, and secret handling |
| PF §7b *Envelope Fields*, *Compatibility Policy*, *Recoverability* | The seven fields with requiredness and setter; the stamped/asserted partition; re-broadening record stamped only when **load-bearing**, travelling with the chain; client contract version on the draft; two consumer obligations; I4 recoverability hops | Envelope stamping, validation, and transport |
| PF §6 *Tenancy and Isolation Specification* | Items keyed on environment; four isolation assertions; five rejected cross-environment mechanisms, **the shared-material item narrowed to material that can mint** (v1.3) | Every record, identifier, cache, and namespace |
| PF §8a *Platform-Resource Operations* | Required authority per operation; the registration ceiling row (held, no human-only permission); the grant-to-human row (ceiling per ID FR-015) | Authority evaluation at both entry points |
| PF §8b *Evaluation Mechanism* | Intersection formula; origin stamping table (**first delegated hop via a delegation credential**, v1.3); declared autonomy and O12; **Sponsorship** (grantable = held; human-only class); **Re-broadening** rule and case table; O1 to O12; L1 to L5 | The perimeter |
| PF §9, §10 | Data-plane and control-plane operations, failure modes (three new registration rejections at v1.2), NFR profiles | Per-face units |
| PF §11 | Harness surface *perimeter validates independently*; *What the SDK may not populate*; *Gateway Exposure* | The wire contract and the edge |
| PF §17 | Tenant-facing contract appendix | The wire contract's published form |
| PF FR-025 | Attribution content: scope, actor, chain, origin, resolved sponsor | Attribution recording |
| ID §7a *Platform-Owned Records* | **Applicable in M1**: Human Principal (organization-scoped; `pending → active`; never pruned; registered-by), Human Authentication Material (class K; `enrollment → active → retired`), Organization Sign-In (`live → ended`), Human Environment Credential (issued-from the sign-in; expiry; revocation state). **Registered, not in M1 scope**: Delegation Credential, Organization-Level Attribution, Configured Identity Source, Grant Mapping | Human principal, material, sign-in, and credential handling |
| ID §6 *Tenancy and Isolation Specification* | Organization-keyed items (human principal, material, sign-in); environment-keyed items (environment credential, grants, first grant, caches); isolation assertions; seven rejected cross-environment mechanisms | The organization level and every environment |
| ID §7b *Obligations on Tenant Contracts*, *Recoverability* | Credential presentation rules; no new envelope field; a direct human operation's actor is the principal and the credential presented, with no origin mode | The wire contract; attribution |
| ID §8a, §8b | Operations and required authority for the human side; human credentials at the perimeter (O1 to O4, O8 to O11; O5 to O7 N/A); **entry points by principal** matrix | The Gateway and Event ingest |
| ID §9, §10 | The control-face operations M1 builds (authenticate, first authentication, environment credentials, grants) and their failure modes and NFR profile. Data-face delegation operations are out of M1 | Per-face units |
| ID §17 | Tenant-facing contract appendix (credentials, namespacing, recognised kinds) | The wire contract's published form |
| ID FR-001, FR-004 | Composed, never-global human identifier; configured tenancy and first Admin | Configuration and identifiers |

---

## Decisions Inherited (DO NOT re-derive)

| Decision | Source | Why it must not be re-derived |
|---|---|---|
| Seven envelope fields; six platform-stamped, trace context agent-asserted | PF §7b, PF FR-001 | Settled contract; one-way once tenants build against it |
| The envelope is carried by every event and every **agent-originated** synchronous call; **a direct human operation carries none** | PF FR-001 (v1.3); ID FR-022 | The actor chain needs an instance, which a human does not have |
| A draft setting a platform-stamped field is **rejected, not overwritten** | PF FR-002, PF §11 | Overwriting would leave a tenant believing their value took effect |
| The envelope is a **platform** contract, not environment-scoped | PF FR-003 | The one platform-scoped contract in the system |
| Unknown fields preserved and forwarded; unknown enum values non-fatal | PF FR-005 | Load-bearing for attribution in choreography |
| Full actor chain travels, most recent last, minimum length 1, perimeter-appended; `maxChainDepth` rejects | PF FR-006 | Predecessor-plus-reference was rejected (hot-path lookup) |
| Origin is platform-stamped where derivable. A delegated chain's **first hop is stamped from a delegation credential** presented beside the agent's own. With no inbound context, declared autonomy gives `autonomous`; undeclared is denied (O12) | PF FR-015, PF §8b (v1.3); ID FR-020 | Closes escalation by omission; an agent acts for a human, never as one |
| `effective = standing ∩ hop1 ∩ ... ∩ hopN`; an agent never acquires its delegator's authority | PF FR-014 | I5 |
| Sponsorship is a grant-time ceiling checked once, with the snapshot recorded; **grantable = held**; a standing set holding a **human-only** permission is rejected | PF FR-016, PF §8b *Sponsorship* (v1.2) | A second principal on the hot path was rejected; you cannot confer what you do not hold |
| **Human-only class** at these tags: `grant:human` (PF), `human:manage` and `agent:delegate` (ID) | PF §8b; ID FR-013 | The class is the union plane PRDs declare |
| Re-broadening is **declared at registration within the standing set**, exercised and **recorded only when load-bearing**, **local to its hop**, and never requested; at the declaring hop `standing ∩ delegating principal ∩ (upstream agents ∪ declared)` | PF FR-017, PF §8b *Re-broadening* (v1.2) | The delegating principal's limit always stands; delegated ⊆ autonomous, the premise of O12 |
| Minimal model: flat, opaque permission identifiers with set semantics, deny by default | PF FR-018 | Minimality is load-bearing for scope and packaging. *Which identifiers are valid*: GAP-INT-006 |
| The `grant:human` ceiling: **any permission valid in E**, to any human, self-grants recorded; never requires the Admin to hold what they grant | ID FR-015; PF §8a (v1.3) | Roles compose rather than nest (OB-13). *Valid in E*: GAP-INT-006 |
| Everything keys on environment; no global identifiers, no global revocation list, **no shared material that can mint** | PF FR-021, PF §6 (v1.3) | I1 |
| Environment identity is configured, never inferred (O11); **organization and project too** | PF FR-022; ID FR-004 | The one-instance-per-environment trap |
| An environment's configuration names its **first Admin**, grants `grant:human` and `human:manage`, and registers the principal with enrollment material. The trust root is the deployment's configuration | ID FR-004 | OB-3; R-2 discharged |
| A human principal is **organization-scoped**, its identifier composed with the organization and never global; it is never deleted or pruned | ID FR-001 | A resolution target for sponsor references |
| Human material is held and verified **at the organization level only**, K only in a form that can verify; material is named by class, never by technology | ID FR-006 | No environment holds or verifies human material |
| Enrollment material is single-use; **the deployer never holds a working credential** | ID FR-007 | A registrar or deployer must not keep a working credential |
| The organization sign-in is **refused at every environment's perimeter except that environment's credential issuance**. Environments hold **verify-only** material for it | ID FR-009 | No credential an environment accepts is accepted by another (I1) |
| The human environment credential is **issued by E**, accepted **only in E**, short-lived and renewable; renewal never widens authority or outlives revocation, its sign-in, or `active` state | ID FR-010 | I1, O4 |
| The organization level sits **outside every environment**, on **no per-request path** | ID FR-009 | Placement decision, not technology |
| At the Gateway human credentials meet O1 to O4 and O8 to O11; O5 to O7 are N/A; **Event ingest refuses every human credential**; every presenter × entry point is reached or refused | ID FR-022, FR-023, ID §8b | OB-14, OB-15 |
| A credential asserts registration, not code identity; the instance identifier is asserted, not verified | PF FR-009, PF §8b | I10 |
| Core bootstrap material is a **locally-verified registration secret**; a registration secret records its **issuer** | PF §8b, PF OQ-11; PF §7a (v1.3) | Clause 1: no external dependency; issuer needed for offboarding |
| Revocation state is cached for at most a platform-set bound, then the perimeter **fails closed** | PF FR-012, PF OQ-12 | Fail-open and tenant-configurable bounds were rejected |
| Bootstrap is the only unauthenticated surface **in PF's capability**; ID adds sign-in and first authentication as unauthenticated surfaces, each bounded per principal, with failed attempts recorded | PF FR-027; ID FR-008 | PF R-6 mitigation; the same pattern for the human side |
| **No entry point treats another's traffic as pre-validated** (O10) | PF §8b, PF FR-020 | The perimeter hole most likely to open in good faith |
| Seam containment: intersection, origin stamping, chain append and `maxChainDepth`, the ceiling check, what a credential asserts, **the external-subject binding**, the human record and lifecycle, grant creation, enrollment single use, per-environment issuance and verify-only material, the human-only class: all in core, behind no seam | PF §12 (v1.3); ID §12 | A seam implementation must not widen authority or orphan principals. The seams decide containment and identity, never composition or authority |
| The identity-resolution seam accepts **authentication** material types, returning an agent registration reference, a human principal reference, or a verified external subject | PF §12 (v1.3); ID FR-027 context | Widened at v1.3; M1 shapes the boundary only (run 1, RA Q8) |
| Edge-reachable (bootstrap, renewal, credentialed data-plane calls, control plane) versus internal (revocation read and store, snapshot resolution, verification material, effective-authority evaluation) | PF §11 | Placement decision, not technology |
| Licence split: the substrate is FSL; **the envelope's machine-readable definition and the seam interfaces are Apache 2.0** | PF §22 | Bears on how the wire contract is laid out in this repository |

---

## Handed to AI-DLC

Decisions the PRDs leave to technical design, each with the constraints the PRDs still
place on it.

| Item | Source | Constraint the answer must satisfy | Decided in |
|---|---|---|---|
| Technology selection (language, datastore, transport, libraries) | — (I11) | Excluded from PRDs by design. Run 1 decided TypeScript with NestJS under three binding conditions (M1-TECH-01 to 04) | NFR Requirements, per unit |
| **Wire contract**: protocol and encoding for both entry points, **including the human operations** | Brief; PF §7, §14; ID §7b, §17 | One contract decided here, consumed by `soorma-sdk` at a pinned version. Raw callers reach identical enforcement (PF FR-023). Carries the client contract version. **Direct human operations carry no envelope.** Delegation-credential presentation must be addable later without a breaking change (A-4) | Application Design |
| Revocation propagation bound (value) | PF FR-012, PF §9; ID FR-021, ID §9 | Finite, published, platform-set, not tenant-configurable. It **is** the revocation-state cache TTL; past it, deny. **It is also the bound for human lifecycle freshness** (ID FR-021, not exercised in M1), so it is one number for both | NFR Requirements (data face) |
| Agent credential lifetime ("short-lived") | PF FR-009, FR-010 | Renewable; renewal never widens authority or outlives revocation. Choose it alongside the propagation bound | NFR Requirements (data face) |
| `maxChainDepth` value | PF FR-006, PF §7b | Implicit handover: named as a contract obligation with no value. Published as part of envelope v1; lowering it later is breaking | Functional Design (envelope) |
| Bootstrap attempt bound: value and shape | PF FR-027 | Per registration; failures recorded against the registration. A hard cap lets an attacker who knows a registration lock out the real agent | NFR Requirements (data face) |
| **Sign-in attempt bound: value and shape** | ID FR-008 | Per principal, for sign-in and first authentication; failures recorded against the principal. "The bound's value and shape are technical design." Same lock-out trade-off as bootstrap | NFR Requirements (control face) |
| **Organization sign-in lifetime** | ID FR-009 | Short-lived; asserts subject, organization, time, and classes used | NFR Requirements (control face) |
| **Human environment credential lifetime** | ID FR-010 | Short-lived, renewable; never outlives revocation, its sign-in, or the principal's `active` state | NFR Requirements |
| Trace-context standard | PF FR-001, PF §7b, PF Decision 8 | An open standard; the perimeter validates well-formedness only. Run 1: W3C Trace Context (M1-TECH-05) | Functional Design |
| Credential formats and per-environment verification material | PF §6; ID FR-009 | No material that can mint is shared across environments. **Environments hold verify-only material for the organization sign-in** | NFR Design |
| **K storage and verification** | ID FR-006 | At the organization level only, in a form that can verify, never recover. SECURITY-12 applies | NFR Design |
| Registration secret storage and verification | PF §7a, FR-008 | Locally verified; verification material internal to the substrate; issuer recorded | NFR Design |
| **Organization level placement** | ID FR-009 | Outside every environment; on no per-request path; reachable through the Gateway for organization operations and environment issuance | Application Design |
| Environment configuration mechanism, **including organization, project, and the first Admin with enrollment material** | PF FR-022, O11; ID FR-004, FR-007 | Configured, never derived from host, instance, cluster, or deployment. Enrollment material single-use; the deployer never holds a working credential | Infrastructure Design |
| Repository layout of the Apache 2.0 parts | PF §22 | Envelope definition and seam interfaces separately licensed Apache 2.0 | Application Design |
| Client contract deprecation window | PF §14; ID §7b | Published, longer than zero, announced before it starts. **Not exercised in M1** | Recorded only |
| Delegation credential lifetime | ID FR-019, ID §9 | Short, published, platform-set, never longer than its source credential. **Not in M1 scope** (ID FR-019 out) | Recorded only |

---

## Deferred Questions Imported

**None.** PF OQ-1 to OQ-14 are `Answered` at `prd-platform-foundations-v1.3`. ID OQ-1 to
OQ-6 and P1-OQ-1 to P7-OQ-2 (seventeen in all) are `Answered` at `prd-identity-v1.0`. None
is `Deferred` to engineering, and none is `Awaiting Answer`.

---

## Open Risks (owned elsewhere: context, not AI-DLC's to resolve)

| ID | Risk | Class | Owner | If the build touches it |
|---|---|---|---|---|
| PF R-1 | Access Policy's model may break L1 for hierarchical or wildcard permissions | Substantive | Access Policy PRD (OB-1) | **Not touched.** M1 builds the flat minimal model only |
| PF R-2 | The first human Admin grant must be obtainable in core | Execution | Identity plane PRD (OB-3) | **Discharged** at PF v1.3 by ID FR-004. Run 1 recorded it as touched; GAP-INT-002 is resolved |
| PF R-3 | Registry & Schema may not express the envelope compatibility policy | Substantive | Registry & Schema PRD (OB-5) | **Not touched.** M1 ships envelope v1 only and builds no registry |
| PF R-4 | An agent that declares autonomy and serves requests keeps the widening path | Accepted | — | **Touched, and accepted.** With delegation absent in M1, every agent making a first-hop request declares autonomy (A-5). Both demo agents carry it |
| PF R-5 | Orphaned sponsorships are undetectable | Accepted | — | Context |
| PF R-6 | Bootstrap is the only unauthenticated surface in PF's capability | Mitigated | — | Mitigated by PF FR-027, in scope. ID FR-008 is the matching mitigation for sign-in, also in scope |
| PF R-7 | Seam implementations become sellable after licence conversion | Accepted | — | Context for the PF FR-026 decision. PR #5's body: the seams are where the licence protects least |
| ID R-1, R-2 | Front-door agents and PF R-4; an agent holding a human's credential | Accepted | — | **Not exercised.** No delegation in M1. ID §17 guidance applies once it lands |
| ID R-3 | Compromising the organization level reaches every environment through sign-in | Accepted | — | Context. The organization level is a high-value component in M1's design |
| ID R-4, R-5, R-7 | Organization outage denies delegated requests; environment outage blocks deactivation; coverage denial discloses | Accepted / Mitigated | — | **Not touched.** No delegation, deactivation, or coverage in M1 |
| ID R-6 | A secret copied beyond its issuer is invisible | Accepted | — | Context; M1 records the issuer |
| ID R-8 | Self-granted domain approvals presented as qualified approvals | Execution, Open | Memory, Eval PRDs (OB-17) | **Not touched.** M1 has no approvals |
| ID R-9 | Access Policy does not recognise a configured-source actor | Execution, Open | Access Policy PRD (OB-16) | **Not touched.** No configured sources in M1 |
| ID R-10 | PF v1.3 not approved with ID | Execution, Open at the tag ("closes at 3.2b") | This PR | **Discharged in fact.** PF v1.3 was approved in PR #21 and tagged on the same merge commit as ID v1.0 |
| ID R-11 | A richer model may confer a human-only permission on an agent through a wildcard, hierarchy, or grouping | Substantive, Open | Access Policy PRD (OB-16) | **Not touched.** M1's flat model matches the human-only class explicitly. Bears on GAP-INT-006 option 2 |

---

## From PR Review (not in the PRD body)

Found from the tags (Step 2.3), not from the header. **Correction to run 1**: run 1 read
only PR #4, which approved v1.0. The tag run 1 built against, v1.1, was approved by PR #5,
which run 1 did not read. It is read now.

| PR | PRDs | Point | Effect |
|---|---|---|---|
| #4 | PF v1.0 | One review, `COMMENTED`, "looks good". No inline threads | None |
| #5 | PF v1.1 | No reviews, comments, or inline threads. Body: no requirement, assignment, obligation, or invariant changed. Only licence statements changed. The seams are "where the licence protects you least" | None on the build. Context for PF R-7 and PF FR-026 |
| #19 | PF v1.2 | No reviews, comments, or inline threads. Body flags **"one inference to check"**: the re-broadening record *travels with the chain* to later envelopes, with no effect on later hops' authority. Packaging sign-off was not re-taken at v1.2 | Now normative at PF §7b v1.3 ("travels with the chain"). Built as stated |
| #21 | ID v1.0, PF v1.3 | No reviews, comments, or inline threads. Body names the review focus: ID §12 (49 core assignments), ID §17, ID §19 and §13 (R-8, R-9, R-11), BD-2. PF v1.3 is one commit, `254c054` | None beyond the PRD bodies. ID R-10 closes with this merge |

**Link note**: PF §23 at v1.2 and v1.3, and the GAP-INT-005 comment on soorma-prd#14,
link run 1's coverage map **by branch** (`blob/dev/...`). Run 2 moved the gap entries to
[specification-gaps.md](specification-gaps.md). A pointer is left where they were, under
*Build-Time Questions Classified at Intake*. The branch links are in soorma-prd, and
AI-DLC does not edit them.

---

## Build-Time Questions Classified at Intake

The brief requires anything M1 needs that no PRD specifies to be classified at intake.
Run 2 re-assessed every run-1 item at the new tags. It also classified what ID's full
intake and a walk of each *Proves* item through the in-scope requirements surfaced. The
test, from `prd-gap-classification.md`:

> *Would two competent engineers, given this PRD, be free to answer differently without
> either being wrong?* Yes means technology. No, because one answer is required but the
> PRD does not say which, means specification. Unsure means specification.

### Summary

| Ref | Question | Brief's watch item | Outcome | Owner | Blocks (*done when*) | Routing |
|---|---|---|---|---|---|---|
| A-1 | Who is the human sponsor? | Q1 (Identity), struck out in the brief as **answered** | **Answered by a PRD**: the registering human, a principal of ID FR-001 holding `agent:register` by self-grant (ID FR-015; ID §1 trace) | — | — | — |
| GAP-INT-001 | How does a human principal exist and authenticate to the control plane? | Q1 | Specification. **Resolved — answered elsewhere** (ID @ v1.0) | Identity | — (block lifted) | soorma-prd#12, closed |
| GAP-INT-002 | The first human grant | Q1 | Specification. **Resolved — answered elsewhere** (ID @ v1.0 FR-004) | Identity | — (block lifted) | soorma-prd#12, closed |
| GAP-INT-005 | The sponsor's "grantable set" | Q1 | Specification. **Resolved — PRD amended** (PF @ v1.3 FR-016; ID FR-015 for `grant:human`) | PF; Identity | — (block lifted) | soorma-prd#14, closed |
| A-2 | Who creates topics? | Q2 (Event) | **Answered by a PRD for M1**, unchanged at v1.3: the environment's namespace exists with the environment (PF §8a, §6). No topics and no topic administration in M1 | — | — | — |
| T-2 | How does a subscription respect credential expiry and revocation? | Q2 | **Technology, constrained**, unchanged: delivery stops within the propagation bound once the subscriber's credential expires or is revoked (PF O2, O3, FR-012) | AI-DLC | — | Confirmed at RA run 1 |
| GAP-INT-003 | What delivery guarantees does a subscriber get? | Q2 | Specification. **Awaiting PRD: Event** (status corrected at run 2), still worked around | Event | 3 (worked around) | soorma-prd#13, open |
| T-3 | What does a trace span mean beyond the envelope field? | Q3 (Observability) | **Technology for soorma-core**, unchanged. PF §19 at v1.3 cites this classification. soorma-core emits no spans | AI-DLC | — | Confirmed at RA run 1 |
| A-3 | Does B need discovery, or only a subscription? | Q4 (Registry & Schema) | **Answered by a PRD**, unchanged: only a subscription (PF §8a) | — | — | — |
| GAP-INT-004 | Re-broadening evaluation | Not on the list | Specification. **Resolved — PRD amended** (PF @ v1.3 §8b). The work-around comes out | PF | — | soorma-prd#14, closed |
| E-1 | §17 and §4 counts | Not on the list | Erratum. **Corrected** at PF v1.2 (§23) | soorma-prd | — | soorma-prd#15, closed |
| **A-4** | How does M1 handle the ID FR-023 matrix rows that involve a delegation credential, when the exchange (ID FR-019) is absent? | Not on the list (new, run 2) | **Answered by a PRD** | — | — | — |
| **A-5** | With delegation absent, what origin does an M1 chain start with? | Not on the list (new, run 2) | **Answered by a PRD** | — | — | — |
| **A-6** | Is bootstrap still the only unauthenticated surface? | Not on the list (new, run 2) | **Answered by a PRD** | — | — | — |
| **T-4** | How is the configured first Admin's enrollment material delivered? | Not on the list (new, run 2) | **Technology, constrained** | AI-DLC | — | To confirm at RA |
| **GAP-INT-006** | Which permissions are **valid in E** (ID FR-015's ceiling), and are tenant-defined identifiers grantable in core? | Not on the list (new, run 2) | **Specification** | Identity (term); PF FR-018 bears | **None**; blocks the grant and standing-set input rule | **Pending**: re-intake gate, question 2 |

**Bottom line for both PRDs' success claims.** ID §1 claims M1's registration path has
no architectural decision left to invent. PF §19 at v1.3 claims the same, apart from
Event and Observability. **Both hold for every *done when* item this repository
proves.** GAP-INT-006 does not break them: no *done when* step depends on how it
resolves. It does leave one input rule of a published, one-way contract to a reading.
Raising it costs a conversation, whereas deciding it here would cost a contract change
later.

---

### Gap entries moved

The full entries for **GAP-INT-001, GAP-INT-002, GAP-INT-003, GAP-INT-004, and
GAP-INT-005**, which run 1 kept in this section, were moved verbatim to
[specification-gaps.md](specification-gaps.md) at run 2 (Step 9.5). Each is now followed
by its run-2 re-assessment. **GAP-INT-006** is recorded there too.

---

### A-1 and T-1 (became GAP-INT-005): the sponsor, and the sponsor's grantable set

*Run 1 reasoning, kept so the change of classification stays visible.*

> **Reclassified at Requirements Analysis.** The user reclassified T-1 as
> **specification** (RA Q6). It became **GAP-INT-005**, resolved at run 2 (PF v1.2 §8b
> and ID FR-015).

**A-1**: in core's single-actor form, "the registering Developer is the sponsor". At
PF v1.3 §12 the check "passes whenever the Developer grants within what they hold". The
sponsor is therefore a human principal, which ID FR-001 now specifies. The sponsor
reference on the registration (PF §7a) points at an organization-scoped human principal
(PF §6; ID §6).

**T-1** (run 1): FR-016 required the granted standing set to be a subset of the sponsor's
grantable set. No section defined *grantable* separately from *held*. Run 1 read it as
*held* and called that "an interpretation rather than an invention". That framing was
the error: an undefined term is specification. The rule file now records this case
explicitly.

---

### A-2 and T-2: topics, and subscription lifetime

*Unchanged at v1.3.*

**A-2**: PF §8a specifies "Publish to an event namespace: `event:publish` in **that
environment's** namespace". PF §6 keys the event namespace on environment. The namespace
exists by virtue of the environment, so nobody creates it. Topics, sub-namespaces, and
topic administration are Event's (PF §2) and are **absent** in M1. Adding them later is
additive.

*Residual*: whole-namespace subscription becomes a behaviour the future Event PRD
inherits. If "event namespaces" (plural, PF §17) is read as several per environment, this
becomes specification.

**T-2**: a subscription outlives a single request. O2 and O3 apply to every request, and
PF FR-012 promises that revocation takes effect within the published bound. Whatever the
subscription mechanism, **delivery to a subscriber must stop within the propagation bound
once its credential expires or is revoked**. O4 applies at subscribe time. At v1.3, Event
ingest also refuses every human credential (ID FR-023), so only agents subscribe.

---

### T-3: trace context in soorma-core

*Unchanged at v1.3. PF §19's trace, step 10, cites this classification.*

PF reserves and requires the field (PF §7b). It is agent-asserted and validated "for
well-formedness against an open standard" only. Choosing the standard is technology:
**W3C Trace Context** (`traceparent` required, `tracestate` optional), M1-TECH-05.
soorma-core **emits no spans in M1**. Done-when 5 belongs to `soorma-sdk`, which
classifies span semantics (OB-8) for itself.

---

### A-4: delegation-credential rows of the entry-point matrix

ID FR-023 (in scope) requires every presenter × entry point combination in ID §8b's
matrix to be reached or refused. One row is *agent credential + delegation credential
bound to it: Reached*. The exchange that issues delegation credentials (ID FR-019) is
**out of M1**, and so are presentation and resolution (ID FR-020, FR-021).

**Answered by a PRD**: with no exchange, no delegation credential can be live. ID FR-020
admits a delegation credential only if it is "live, unexpired, unrevoked, bound to this
logical agent and this environment". In M1 that row is therefore **refused by its own
checks**, and every other row behaves as the matrix states. FR-023 is built in full; the
row is unreachable because what it presupposes is absent. That is not a simplification.

*Residual, technology*: the wire contract must leave room to add delegation-credential
presentation **additively** (ID §14: "additive only"). Application Design records how.

---

### A-5: origin in M1, with delegation absent

At PF v1.3 §8b a delegated chain starts **only** from a delegation credential. The v1.1
row, *invoked through the Gateway by an authenticated principal*, is gone. A human acting
directly carries no envelope and has no origin mode (ID §8a).

**Answered by a PRD**: in M1 every chain **starts autonomous**. An agent's first-hop
request (publish, subscribe, any agent-originated call) with no inbound context is
`autonomous` if the agent declared autonomy, and **denied** if not (O12). An
event-triggered hop propagates the origin unchanged.

Consequences that RA must carry:
- every M1 agent that makes a first-hop request is registered with **autonomy
  declared**. That includes both demo agents: A to publish, and B to subscribe. PF R-4 is
  accepted for both
- the *delegating principal* field is never stamped in M1, and the delegated-origin
  paths are absent, not simplified
- re-broadening (GAP-INT-004, now built) is exercised at event-triggered hops, where
  the delegating-principal term reads *yes*

---

### A-6: unauthenticated surfaces

PF FR-027 says the bootstrap exchange is "the only unauthenticated surface **in this
capability**". ID FR-008 adds sign-in and first authentication as unauthenticated
surfaces, each bounded per principal, with failed attempts recorded.

**Answered by a PRD**: the two PRDs agree, because PF's claim is scoped to PF's own
capability. M1 has **three** unauthenticated surfaces: bootstrap, sign-in, and first
authentication. Run 1's M1-FR-05 says "It is the only unauthenticated surface", which is
now wrong in M1's scope. It is corrected when RA re-runs.

---

### T-4: delivering the first Admin's enrollment material

ID FR-004 has the environment's configuration register the first Admin, if absent, "with
enrollment material". ID FR-007 makes that material single-use, replaced on first
authentication, and says "the deployer never holds a working credential".

**Technology, constrained**: how the configuration carries the material and how it
reaches the human is a configuration-mechanism choice. Two engineers could choose
differently without either being wrong. The constraints the answer must satisfy:
- single use, refused on reuse (ID §10 failure modes)
- never a working credential in the deployer's hands
- configured, never inferred (PF O11; ID FR-004)
- held only at the organization level once consumed (ID FR-006)

It is decided with the environment configuration mechanism at Infrastructure Design and
confirmed at RA.

---

### E-1: Errata

Run 1 found two count errors: PF §17 "Five are platform-stamped" listed six, and PF §4
said "Thirteen" operations where §8a and §12 count sixteen. **Corrected at PF v1.2**
(§23; soorma-prd#15, closed). Neither changed what is built.
