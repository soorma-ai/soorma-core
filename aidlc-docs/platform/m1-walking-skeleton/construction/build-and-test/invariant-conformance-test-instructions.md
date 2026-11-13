# Invariant Conformance

Every applicable row of every unit's `functional-design/invariant-coverage-matrix.md`, verified
against this stage's run (2026-11-13), with the three checks the soorma Platform Invariants
extension requires across units: the **I8 packaging table as a set**, **I2 cumulatively across the
harness surface**, and a source check for **I3 and I10**.

**Invariants source**: soorma-prd `references/platform/invariants.md`, identical at
`prd-platform-foundations-v1.3` and `prd-identity-v1.0`. **Applicability**: inherited from PF §15
and ID §15, where I1 to I11 are all *Addressed*.

## Result

| Unit | I1 to I10 | Pass | Fail | Unverified | I11 |
|---|---|---|---|---|---|
| U1 `wire-contract` | 10 | 10 | 0 | 0 | N/A |
| U2 `org-identity` | 10 | 10 | 0 | 0 | N/A |
| U3 `authority-evaluation` | 10 | 10 | 0 | 0 | N/A |
| U4 `env-human-access` | 10 | 10 | 0 | 0 | N/A |
| U5 `agent-registration` | 10 | 10 | 0 | 0 | N/A |
| U6 `agent-credentials` | 10 | 10 | 0 | 0 | N/A |
| U7 `event-transport` | 10 | 10 | 0 | 0 | N/A |
| **Total** | **70** | **70** | **0** | **0** | 7 N/A |

I11 is N/A in every matrix by the extension's rule: it constrains the PRD, and Construction is
where technology is selected.

The method is `l1-conformance-test-instructions.md`'s. **One correction**: U7's I4 row still read
`Covered (GAP-ET-001 work-around)`, although the matrix's own Code Generation note records I1 to
I10 `Implemented`. Its evidence passed in this run (TC-ET-004, 005, 034, 035, 042), and it moves to
`Verified (GAP-ET-001 work-around)` with the rest.

## I8: the packaging table as a set

Each unit's table (in its invariant matrix) assigns every capability it implemented. Checked
together:

| Check | Result |
|---|---|
| Every capability built is assigned to core by PF §12 or ID §12 | Pass: U2 (12 capabilities), U3 (8), U4 (9), U5 (6), U6 (7), U7 (7); U1 the contract (Apache 2.0) |
| No capability is assigned twice, differently | Pass: shared capabilities (attribution recording in U4, U5, U6, U7; the minimal permission model in U3 and U4) carry the same core assignment in each |
| Nothing commercial, enabled or stubbed (IdP federation; second-factor policy by group or risk; Access Policy's richer models; separation of duties; grant mappings; an organization role model; an audit product; sponsorship policy; topic administration, durability, redelivery; the portal) | Pass: no such term in production source except the contract's statement that no durability, ordering, or redelivery is promised |
| Every numeric bound is a security bound, not a tenant quota | Pass: S1's abuse bound, S2's throttle, U5's 10-secret cap (NFR-AR-24), S3's bootstrap bound, S4's limits and stream cap, each a platform constant |
| Deferred capabilities are absent, not stubbed (PF FR-008 rotation and retirement, FR-011 revocation writer, FR-013 attribution pruning; ID FR-002, 003, 012, 016 to 021, 026) | Pass: S2 has no read, rotate, retire, suspend, or revoke surface (`services/control-gateway/test/registration-structure.test.ts`); revocation is seeded by tests only, never in an image |
| Licences | Pass: `contract/` and `seams/` Apache 2.0; everything else FSL-1.1-ALv2 (`check:deps`, licence) |
| Unpublished seams (M1-FR-13) | Pass: every workspace package is `private` |

S1's pruner (U2 NFR-OI-25) deletes only failed-attempt records and ended or expired sign-ins
after 90 days. It never touches principals, material, or attribution records, so it is neither
PF FR-013's attribution pruning nor an I4 risk.

## I2 across the harness surface

soorma-core ships no SDK. The check is that every harness operation (PF §11 *Harness Surface*) is
enforced at a perimeter independently of any client, shown by a raw call:

| Harness operation | Enforced at | Raw-call evidence (this run) |
|---|---|---|
| Acquire (bootstrap) | S3: secret parsed, one record loaded, constant-time comparison, the bound | TC-AC-093, TC-AC-013 (`e2e/`) |
| Renew | S3: lineage, revocation, the lineage's maximum age | TC-AC-093, TC-AC-009, 025, 028 (`e2e/`) |
| Hold and present | P1 `checkAgentRequest` at S3 and S4 independently (O1 to O4, O3 within B at S4) | TC-ET-006, TC-ET-014/017/028/031 (`e2e/`) |
| Draft envelope | S4 through U3's admission: closed draft, stamped fields refused, never overwritten | TC-ET-007, TC-ET-040 (`e2e/`) |
| Populate trace context | S4: `traceContext` validated in the draft, carried unchanged | TC-ET-002 (`e2e/`) |
| Forward inbound context | S4: the seal verified, under this environment's key ring only | TC-ET-005, TC-ET-090 (`e2e/`) |

No perimeter decision depends on how the request was built. The brief's *What the SDK may not
populate* fields are the stamped fields, refused at S4 (TC-ET-007).

## I3 and I10: source check

`grep` over `services/*/src` and `packages/*/src` for `remoteAddress`, `x-forwarded`,
`request.ip`, `os.hostname`, `HOSTNAME`, `POD_NAME`, `KUBERNETES`: **none found**. Identity comes
from the presented credential only. The same credential from inside the stack's network resolves
to the same principal or agent: TC-AR-044, TC-ET-041 (`e2e/`); TC-AC-043.

## Rows

### U1 `wire-contract` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | TC-ET-006, TC-ET-090, TC-ET-015 (`e2e/`); U3's I1 row below (a seal from E2 refused in E) |
| I2 | Pass | TC-AR-043, TC-ET-040 (`e2e/`, raw calls); U3's I2 row (forged `inbound` refused); the cumulative check in *I2 across the harness surface*, below |
| I3 | Pass | TC-AC-043 (`services/data-gateway/test/refusals.test.ts`); TC-AR-044, TC-ET-041 (`e2e/`); the I3 source check below |
| I4 | Pass | TC-EHA-046 (`packages/attribution/test/record.test.ts`); TC-ET-002, 003, 004 (`e2e/`); U3's I4 row below |
| I5 | Pass | U3's I5 row below (one evaluator; origin unchanged after N hops; the low-authority caller) |
| I6 | Pass | One surface document per deployable (`contract/org-gateway`, `control-gateway`, `data-gateway`, `event-ingest`); `pnpm check:contract` passed; each unit's I6 row |
| I7 | Pass | `contract/test/compatibility.test.ts`: TC-WC-030, TC-WC-031; `contract/test/envelope.test.ts`: TC-WC-008, TC-WC-017, TC-WC-021; `contract/test/draft.test.ts`: TC-WC-010; `contract/test/generation.test.ts`: TC-WC-032 |
| I8 | Pass | `contract/test/checks.test.ts`: TC-WC-011 |
| I9 | Pass | Reviewed at Code Generation; no tenant schema or constant in `contract/` outside labelled samples |
| I10 | Pass | Reviewed at Code Generation; the I3 source check below finds no network, host, or deployment identity read |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |

### U2 `org-identity` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-018, TC-OI-028; `packages/abuse-bound/test/abuse-bound.test.ts`: TC-OI-028; `packages/org-identity/test/crypto.test.ts`: TC-OI-044; `services/org-gateway/test/internal.test.ts`: TC-OI-046; `packages/config/test/tenancy.test.ts`: TC-OI-048 |
| I2 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-023; `packages/perimeter/test/presenter.test.ts`: TC-OI-024 |
| I3 | Pass | `packages/config/test/tenancy.test.ts`: TC-OI-019; `services/org-gateway/test/internal.test.ts`: TC-OI-045 |
| I4 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-021; `contract/test/org-gateway.test.ts`: TC-OI-022; `packages/org-identity/test/store.test.ts`: TC-OI-022 |
| I5 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-025; `services/org-gateway/test/logs-and-timing.test.ts`: TC-OI-025; `packages/identity-resolution/test/resolver.test.ts`: TC-OI-060 |
| I6 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-023; `services/org-gateway/test/edge.test.ts`: TC-OI-047; `services/org-gateway/test/internal.test.ts`: TC-OI-047 |
| I7 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-023 |
| I8 | Pass | The I8 set check, below |
| I9 | Pass | `services/org-gateway/test/logs-and-timing.test.ts`: TC-OI-061 |
| I10 | Pass | `packages/config/test/tenancy.test.ts`: TC-OI-019; `services/org-gateway/test/internal.test.ts`: TC-OI-045 |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |

### U3 `authority-evaluation` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006; `packages/authority/test/admission.test.ts`: TC-AE-024; `packages/config/test/tenancy.test.ts`: TC-AE-033; `packages/authority/test/agent-facts.test.ts`: TC-AE-034 |
| I2 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-009, TC-AE-024; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-009, TC-AE-010, TC-AE-014; `packages/authority/test/structure.test.ts`: TC-AE-039 |
| I3 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-001; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-001; `packages/authority/test/structure.test.ts`: TC-AE-039 |
| I4 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-003, TC-AE-005, TC-AE-017, TC-AE-019; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-008, TC-AE-017 |
| I5 | Pass | `packages/authority/test/evaluate.test.ts`: TC-AE-004, TC-AE-011, TC-AE-016, TC-AE-020, TC-AE-023, TC-AE-026; `packages/authority/test/admission.test.ts`: TC-AE-005, TC-AE-011, TC-AE-015, TC-AE-016, TC-AE-018, TC-AE-022, TC-AE-023, TC-AE-026; `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-035 |
| I6 | Pass | `pnpm check:contract` passed; U3 adds no operation to any surface document |
| I7 | Pass | `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-008 |
| I8 | Pass | The I8 set check, below |
| I9 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-026; `packages/authority/test/evaluate.test.ts`: TC-AE-026 |
| I10 | Pass | Reviewed at Code Generation; the I3 source check below |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |

### U4 `env-human-access` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-010; `services/control-gateway/test/flows.test.ts`: TC-EHA-010; `deploy/test/compose-model.test.ts`: TC-EHA-022, TC-EHA-089; `services/control-gateway/test/isolation.test.ts`: TC-EHA-022, TC-EHA-051; `packages/registry/test/registry.test.ts`: TC-EHA-040 |
| I2 | Pass | `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-009, TC-EHA-015, TC-EHA-016; `services/control-gateway/test/flows.test.ts`: TC-EHA-009, TC-EHA-049; `contract/test/control-gateway.test.ts`: TC-EHA-024 |
| I3 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-010; `services/control-gateway/test/flows.test.ts`: TC-EHA-010; `services/control-gateway/test/isolation.test.ts`: TC-EHA-050 |
| I4 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-005; `services/control-gateway/test/flows.test.ts`: TC-EHA-021; `packages/attribution/test/record.test.ts`: TC-EHA-046, TC-EHA-047 |
| I5 | Pass | `packages/authority/test/human.test.ts`: TC-EHA-012; `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-015; `services/control-gateway/test/closure.test.ts`: TC-EHA-044; `services/control-gateway/test/flows.test.ts`: TC-EHA-026 |
| I6 | Pass | `pnpm check:contract` passed; `control-gateway.openapi.yaml` holds no data-face operation; S2 refuses `soorma_ac_` by kind (TC-EHA tests in `services/control-gateway/test/`) |
| I7 | Pass | `contract/test/control-gateway.test.ts`: TC-EHA-024 |
| I8 | Pass | The I8 set check, below |
| I9 | Pass | Reviewed at Code Generation; only plane-declared identifiers in code (BR-ACC-01) |
| I10 | Pass | Reviewed at Code Generation; the I3 source check below |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |

### U5 `agent-registration` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-039, TC-AR-025; `services/control-gateway/test/registration.test.ts`: TC-AR-042 |
| I2 | Pass | `contract/test/control-gateway-registration.test.ts`: TC-AR-022; `services/control-gateway/test/registration.test.ts`: TC-AR-043; `e2e/agent-registration.test.ts`: TC-AR-043 |
| I3 | Pass | `e2e/agent-registration.test.ts`: TC-AR-044 |
| I4 | Pass | `packages/authority/test/registration.test.ts`: TC-AR-002; `services/control-gateway/test/registration.test.ts`: TC-AR-007, TC-AR-040, TC-AR-041 |
| I5 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-009, TC-AR-003; `packages/authority/test/registration.test.ts`: TC-AR-010, TC-AR-011, TC-AR-012; `services/control-gateway/test/registration-structure.test.ts`: TC-AR-031; `packages/authority/test/held.test.ts`: TC-AR-038 |
| I6 | Pass | `contract/test/control-gateway-registration.test.ts`: TC-AR-022, TC-AR-045; `services/control-gateway/test/registration.test.ts`: TC-AR-016 |
| I7 | Pass | `contract/test/control-gateway-registration.test.ts`: TC-AR-045, TC-AR-022 |
| I8 | Pass | `services/control-gateway/test/registration-structure.test.ts`: TC-AR-046 |
| I9 | Pass | `tools/test/code-checks.test.ts`: TC-AR-047 |
| I10 | Pass | `tools/test/code-checks.test.ts`: TC-AR-047 |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |

### U6 `agent-credentials` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-013; `deploy/test/data-gateway.test.ts`: TC-AC-020; `packages/env-store/test/agent-credentials.test.ts`: TC-AC-033, TC-AC-078; `packages/credentials/test/revocation.test.ts`: TC-AC-034 |
| I2 | Pass | `contract/test/data-gateway.test.ts`: TC-AC-021; `services/data-gateway/test/refusals.test.ts`: TC-AC-042; `e2e/agent-registration.test.ts`: TC-AC-093 |
| I3 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-043; `services/data-gateway/test/flows.test.ts`: TC-AC-031 |
| I4 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-005, TC-AC-019, TC-AC-035; `e2e/agent-credentials.test.ts`: TC-AC-005; `packages/attribution/test/envelope-free.test.ts`: TC-AC-036 |
| I5 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-016; `services/data-gateway/test/closure.test.ts`: TC-AC-040 |
| I6 | Pass | `packages/perimeter/test/agent-presenter.test.ts`: TC-AC-012; `contract/test/data-gateway.test.ts`: TC-AC-021, TC-AC-044 |
| I7 | Pass | `contract/test/data-gateway.test.ts`: TC-AC-021, TC-AC-045 |
| I8 | Pass | `tools/test/agent-credentials-review.test.ts`: TC-AC-046 |
| I9 | Pass | `tools/test/agent-credentials-review.test.ts`: TC-AC-047 |
| I10 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-002, TC-AC-024; `tools/test/agent-credentials-review.test.ts`: TC-AC-041 |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |

### U7 `event-transport` (11 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| I1 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-006, TC-ET-090; `e2e/agent-registration.test.ts`: TC-ET-006; `e2e/event-transport.test.ts`: TC-ET-015, TC-ET-039, TC-ET-090; `services/event-ingest/test/streams.test.ts`: TC-ET-039; `services/event-ingest/test/revocation.test.ts`: TC-ET-032 |
| I2 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-007, TC-ET-021; `contract/test/event-ingest.test.ts`: TC-ET-024; `e2e/event-transport.test.ts`: TC-ET-040 |
| I3 | Pass | `e2e/event-transport.test.ts`: TC-ET-041 |
| I4 | Pass | `e2e/agent-registration.test.ts`: TC-ET-004; `e2e/event-transport.test.ts`: TC-ET-005; `services/event-ingest/test/flows.test.ts`: TC-ET-034; `packages/attribution/test/envelope-bearing.test.ts`: TC-ET-042; `services/event-ingest/test/revocation.test.ts`: TC-ET-035 |
| I5 | Pass | `e2e/event-transport.test.ts`: TC-ET-005, TC-ET-020; `services/event-ingest/test/refusals.test.ts`: TC-ET-010, TC-ET-011, TC-ET-044; `services/event-ingest/test/composition.test.ts`: TC-ET-043 |
| I6 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-012; `contract/test/event-ingest.test.ts`: TC-ET-024, TC-ET-038 |
| I7 | Pass | `contract/test/event-ingest.test.ts`: TC-ET-024, TC-ET-045 |
| I8 | Pass | TC-ET-083: S4's image built and its installed packages checked in this run (no `org-identity`, `identity-resolution`, `agent-identity`, `abuse-bound`; no migrations); TC-ET-046: the I8 set check, below |
| I9 | Pass | `services/event-ingest/test/composition.test.ts`: TC-ET-047 |
| I10 | Pass | `services/event-ingest/test/streams.test.ts`: TC-ET-048; `e2e/event-transport.test.ts`: TC-ET-048 |
| I11 | N/A | N/A: Construction is where technology is selected (I11 constrains the PRD) |
