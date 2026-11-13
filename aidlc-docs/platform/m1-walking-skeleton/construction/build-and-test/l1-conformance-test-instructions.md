# L1 Domain Conformance

Every applicable row of every unit's `functional-design/l1-coverage-matrix.md`, verified against
this stage's run (2026-11-13). The L1 sources are PF @ `prd-platform-foundations-v1.3` and ID @
`prd-identity-v1.0` (the PRD intake), each at its own tag.

## Method

1. Run every suite: `pnpm test` (1707 passed), `pnpm test:e2e` on a fresh stack (27 passed),
   `pnpm stack:smoke` (106 checks), `pnpm stack:outage` (40 checks), the image checks, and the
   performance runs. Each test reporter wrote a JSON report.
2. For each row, expand every test case id in its *Verification target* (including the shorthand
   `TC-ET-002, 003, 004` and ranges) and find it in a **passed** test's name, or in the source of a
   test file whose every test passed, or in a stack script or check that passed in this run.
3. A row whose target is a review or a reference to other rows is mapped by hand to the evidence
   that covers it, and says so.
4. Pass: every test case id the row cites is found passing, or its hand-mapped evidence passed.
   Each matrix row's status then moves from `Implemented` to `Verified`.

Evidence names the file where each test case id passed. The test names carry the ids, so
`grep -rn "TC-XX-nnn" <file>` finds the test.

## Result

| Unit | Applicable rows | Pass | Fail | Unverified |
|---|---|---|---|---|
| U1 `wire-contract` | 32 | 32 | 0 | 0 |
| U2 `org-identity` | 32 | 32 | 0 | 0 |
| U3 `authority-evaluation` | 38 | 38 | 0 | 0 |
| U4 `env-human-access` | 33 | 33 | 0 | 0 |
| U5 `agent-registration` | 32 | 32 | 0 | 0 |
| U6 `agent-credentials` | 34 | 34 | 0 | 0 |
| U7 `event-transport` | 36 | 36 | 0 | 0 |
| **Total** | **237** | **237** | **0** | **0** |

Each matrix's non-applicable rows stay `N/A` with their reasons, in the matrix.

**Rows resting on a specification gap's work-around** pass as built. Each is reported with its gap
in the summary, not hidden by the pass: U7 L1-26 (GAP-ET-001) and L1-30 (GAP-INT-003); U6 L1-27 and
L1-29 (GAP-INT-008) and L1-28 (GAP-INT-009); U5 L1-17 and L1-31 (GAP-INT-006); U3 L1-07, 21, 25,
27, and 38 (GAP-AE-001 and GAP-INT-007).

## Rows

### U1 `wire-contract` (32 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `contract/test/envelope.test.ts`: TC-WC-001, TC-WC-006; `contract/test/conventions.test.ts`: TC-WC-005 |
| L1-02 | Pass | `contract/test/draft.test.ts`: TC-WC-007, TC-WC-012 |
| L1-03 | Pass | `contract/test/components.test.ts`: TC-WC-009 |
| L1-04 | Pass | `contract/test/conventions.test.ts`: TC-WC-028; `contract/test/compatibility.test.ts`: TC-WC-030, TC-WC-031 |
| L1-05 | Pass | `contract/test/envelope.test.ts`: TC-WC-008; `contract/test/draft.test.ts`: TC-WC-015 |
| L1-06 | Pass | `contract/test/envelope.test.ts`: TC-WC-017; `contract/test/generation.test.ts`: TC-WC-032 |
| L1-07 | Pass | `contract/test/conventions.test.ts`: TC-WC-018 |
| L1-08 | Pass | `contract/test/envelope.test.ts`: TC-WC-001, TC-WC-006, TC-WC-016; `contract/test/conventions.test.ts`: TC-WC-019 |
| L1-09 | Pass | `contract/test/draft.test.ts`: TC-WC-010 |
| L1-10 | Pass | Done when 4 on the stack: TC-ET-002, 003, 004 (`e2e/agent-registration.test.ts`); TC-EHA-046 (`packages/attribution/test/record.test.ts`, zero hops and a multi-hop chain); U3's I4 row below |
| L1-11 | Pass | `contract/test/draft.test.ts`: TC-WC-007 |
| L1-12 | Pass | `contract/test/draft.test.ts`: TC-WC-015 |
| L1-13 | Pass | `contract/test/conventions.test.ts`: TC-WC-028 |
| L1-14 | Pass | `contract/test/conventions.test.ts`: TC-WC-029 |
| L1-15 | Pass | `contract/test/envelope.test.ts`: TC-WC-021; `contract/test/conventions.test.ts`: TC-WC-022; `contract/test/draft.test.ts`: TC-WC-022 |
| L1-16 | Pass | As L1-04 to L1-06 of this matrix (Verified, above) |
| L1-17 | Pass | `contract/test/checks.test.ts`: TC-WC-011 |
| L1-18 | Pass | Raw calls, no SDK: TC-AR-043, TC-AC-093, TC-ET-040 (`e2e/`); every rule is enforced at a perimeter (the I2 rows below) |
| L1-19 | Pass | `contract/test/envelope.test.ts`: TC-WC-001 |
| L1-20 | Pass | `contract/test/components.test.ts`: TC-WC-026; `contract/test/conventions.test.ts`: TC-WC-026 |
| L1-21 | Pass | Conventions reviewed at Code Generation; `pnpm check:contract` and TC-WC-031 (`contract/test/compatibility.test.ts`) passed in this run |
| L1-22 | Pass | TC-ET-013 (`services/event-ingest/test/refusals.test.ts`); S3's refusal of `Soorma-Delegation` (`services/data-gateway/test/refusals.test.ts`); TC-WC-007 (`contract/test/draft.test.ts`) |
| L1-23 | Pass | `contract/test/conventions.test.ts`: TC-WC-022; `contract/test/draft.test.ts`: TC-WC-022 |
| L1-24 | Pass | `contract/test/conventions.test.ts`: TC-WC-005 |
| L1-25 | Pass | `contract/test/conventions.test.ts`: TC-WC-005 |
| L1-26 | Pass | `contract/test/conventions.test.ts`: TC-WC-004 |
| L1-27 | Pass | `contract/test/draft.test.ts`: TC-WC-007 |
| L1-28 | Pass | TC-EHA-013, 038 (`services/control-gateway/test/flows.test.ts`, `packages/registry/test/registry.test.ts`); U5 L1-17 and L1-31 (the accepted set for standing sets) |
| L1-29 | Pass | `contract/test/envelope.test.ts`: TC-WC-008; `contract/test/conventions.test.ts`: TC-WC-020 |
| L1-30 | Pass | TC-AC-010 (`services/data-gateway/test/failures.test.ts`); TC-AC-015 (`packages/credentials/test/revocation.test.ts`); TC-ET-028, 029 (`services/event-ingest/test/`) |
| L1-31 | Pass | `contract/test/conventions.test.ts`: TC-WC-025 |
| L1-32 | Pass | `contract/test/generation.test.ts`: TC-WC-003, TC-WC-032, TC-WC-033 |

### U2 `org-identity` (32 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-018 |
| L1-02 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-001, TC-OI-002 |
| L1-03 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-022; `packages/org-identity/test/store.test.ts`: TC-OI-022, TC-OI-051 |
| L1-04 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-001 |
| L1-05 | Pass | `packages/config/test/tenancy.test.ts`: TC-OI-019 |
| L1-06 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-001, TC-OI-017 |
| L1-07 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-017; `services/org-gateway/test/logs-and-timing.test.ts`: TC-OI-049 |
| L1-08 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-003, TC-OI-004, TC-OI-016 |
| L1-09 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-014, TC-OI-035, TC-OI-040 |
| L1-10 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-008 |
| L1-11 | Pass | `packages/org-identity/test/crypto.test.ts`: TC-OI-043; `packages/config/test/tenancy.test.ts`: TC-OI-048 |
| L1-12 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-021, TC-OI-007, TC-OI-037 |
| L1-13 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-025; `services/org-gateway/test/logs-and-timing.test.ts`: TC-OI-025 |
| L1-14 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-002, TC-OI-009, TC-OI-034 |
| L1-15 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-009, TC-OI-017 |
| L1-16 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-010, TC-OI-011; `packages/abuse-bound/test/abuse-bound.test.ts`: TC-OI-011 |
| L1-17 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-003, TC-OI-004 |
| L1-18 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-006, TC-OI-021 |
| L1-19 | Pass | `services/org-gateway/test/internal.test.ts`: TC-OI-046 |
| L1-20 | Pass | `services/org-gateway/test/internal.test.ts`: TC-OI-045, TC-OI-047; `services/org-gateway/test/edge.test.ts`: TC-OI-047 |
| L1-21 | Pass | `packages/org-identity/test/crypto.test.ts`: TC-OI-044 |
| L1-22 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-005, TC-OI-006, TC-OI-007, TC-OI-015 |
| L1-23 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-003, TC-OI-014, TC-OI-016 |
| L1-24 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-020, TC-OI-006; `packages/perimeter/test/presenter.test.ts`: TC-OI-024, TC-OI-027 |
| L1-25 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-023 |
| L1-26 | Pass | `packages/perimeter/test/presenter.test.ts`: TC-OI-026, TC-OI-027; `services/org-gateway/test/edge.test.ts`: TC-OI-026 |
| L1-27 | Pass | `packages/config/test/tenancy.test.ts`: TC-OI-048 |
| L1-28 | Pass | `packages/org-identity/test/domain.test.ts`: TC-OI-021 |
| L1-29 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-023 |
| L1-30 | Pass | `packages/abuse-bound/test/abuse-bound.test.ts`: TC-OI-011; `packages/org-identity/test/domain.test.ts`: TC-OI-011, TC-OI-014, TC-OI-009 |
| L1-31 | Pass | TC-OI-059 on the running stack in this run: `authenticate` p95 334 ms (target 500), renewal 20 ms and logout 17 ms (target 200) (`services/org-gateway/test/perf/latency.test.ts`); durability by U2's store tests |
| L1-32 | Pass | `contract/test/org-gateway.test.ts`: TC-OI-025; `services/org-gateway/test/logs-and-timing.test.ts`: TC-OI-025; `packages/identity-resolution/test/resolver.test.ts`: TC-OI-060 |

### U3 `authority-evaluation` (38 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-001; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-001 |
| L1-02 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-009, TC-AE-023; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-009, TC-AE-014; `packages/authority/test/evaluate.test.ts`: TC-AE-020, TC-AE-023 |
| L1-03 | Pass | `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-008, TC-AE-027; `packages/authority/test/admission.test.ts`: TC-AE-027 |
| L1-04 | Pass | `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-008; `packages/authority/test/admission.test.ts`: TC-AE-025; `packages/authority/test/evaluate.test.ts`: TC-AE-025 |
| L1-05 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-003, TC-AE-017; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-017 |
| L1-06 | Pass | `packages/authority/test/evaluate.test.ts`: TC-AE-004, TC-AE-020; `packages/authority/test/admission.test.ts`: TC-AE-015 |
| L1-07 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-002, TC-AE-003, TC-AE-011, TC-AE-023; `packages/authority/test/evaluate.test.ts`: TC-AE-011, TC-AE-023 |
| L1-08 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-005, TC-AE-016, TC-AE-018, TC-AE-019, TC-AE-022; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-014; `packages/authority/test/evaluate.test.ts`: TC-AE-016 |
| L1-09 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-021; `packages/authority/test/evaluate.test.ts`: TC-AE-021; `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006 |
| L1-10 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-035 |
| L1-11 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006; `packages/authority/test/admission.test.ts`: TC-AE-024; `packages/authority/test/agent-facts.test.ts`: TC-AE-034 |
| L1-12 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-001; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-001; `packages/authority/test/structure.test.ts`: TC-AE-039 |
| L1-13 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006; `packages/authority/test/structure.test.ts`: TC-AE-039 |
| L1-14 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-002, TC-AE-011; `packages/authority/test/evaluate.test.ts`: TC-AE-011 |
| L1-15 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006; `packages/authority/test/agent-facts.test.ts`: TC-AE-034 |
| L1-16 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-001; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-001; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-007, TC-AE-012 |
| L1-17 | Pass | As L1-03, 04, 05, 07 of this matrix (Verified, above) |
| L1-18 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-001, TC-AE-003; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-001 |
| L1-19 | Pass | `packages/authority/test/evaluate.test.ts`: TC-AE-004, TC-AE-020 |
| L1-20 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-002, TC-AE-003, TC-AE-011; `packages/authority/test/evaluate.test.ts`: TC-AE-011 |
| L1-21 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-002, TC-AE-011, TC-AE-023; `packages/authority/test/evaluate.test.ts`: TC-AE-011, TC-AE-023 |
| L1-22 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-022 |
| L1-23 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-009; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-009, TC-AE-010 |
| L1-24 | Pass | `packages/authority/test/evaluate.test.ts`: TC-AE-004, TC-AE-021; `packages/authority/test/admission.test.ts`: TC-AE-021 |
| L1-25 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-011, TC-AE-023; `packages/authority/test/evaluate.test.ts`: TC-AE-011, TC-AE-023 |
| L1-26 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-021; `packages/authority/test/evaluate.test.ts`: TC-AE-021 |
| L1-27 | Pass | `packages/envelope/test/version-and-draft.test.ts`: TC-AE-010 |
| L1-28 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-026; `packages/authority/test/evaluate.test.ts`: TC-AE-026 |
| L1-29 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-017, TC-AE-009, TC-AE-011; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-017; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-009, TC-AE-010; `packages/authority/test/evaluate.test.ts`: TC-AE-011 |
| L1-30 | Pass | `packages/authority/test/agent-facts.test.ts`: TC-AE-034; `packages/registry/test/perf/admit-store.test.ts`: TC-AE-040; `packages/authority/bench/admit.bench.ts`: TC-AE-040 |
| L1-31 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-009, TC-AE-013; `packages/envelope/test/version-and-draft.test.ts`: TC-AE-009, TC-AE-013 |
| L1-32 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-003, TC-AE-011, TC-AE-017; `packages/authority/test/evaluate.test.ts`: TC-AE-011; `packages/envelope/test/inbound-and-stamp.test.ts`: TC-AE-017 |
| L1-33 | Pass | `packages/envelope/test/version-and-draft.test.ts`: TC-AE-007, TC-AE-012 |
| L1-34 | Pass | `packages/authority/test/structure.test.ts`: TC-AE-039 |
| L1-35 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006 |
| L1-36 | Pass | `packages/policy-decision/test/policy-decision.test.ts`: TC-AE-006; `packages/authority/test/structure.test.ts`: TC-AE-039 |
| L1-37 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-024; `packages/envelope/test/seal.test.ts`: TC-AE-032 |
| L1-38 | Pass | `packages/authority/test/admission.test.ts`: TC-AE-023; `packages/authority/test/evaluate.test.ts`: TC-AE-023 |

### U4 `env-human-access` (33 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-002; `services/control-gateway/test/flows.test.ts`: TC-EHA-002, TC-EHA-004, TC-EHA-014; `packages/credentials/test/records.test.ts`: TC-EHA-014 |
| L1-02 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-002; `services/control-gateway/test/flows.test.ts`: TC-EHA-002, TC-EHA-011, TC-EHA-025; `packages/authority/test/human.test.ts`: TC-EHA-011 |
| L1-03 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-010; `services/control-gateway/test/flows.test.ts`: TC-EHA-010 |
| L1-04 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-003, TC-EHA-026 |
| L1-05 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-019, TC-EHA-020, TC-EHA-017, TC-EHA-028, TC-EHA-029 |
| L1-06 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-004, TC-EHA-014; `packages/credentials/test/records.test.ts`: TC-EHA-014, TC-EHA-030 |
| L1-07 | Pass | `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-009; `services/control-gateway/test/flows.test.ts`: TC-EHA-009 |
| L1-08 | Pass | `deploy/test/compose-model.test.ts`: TC-EHA-022; `services/control-gateway/test/isolation.test.ts`: TC-EHA-022 |
| L1-09 | Pass | `services/control-gateway/test/isolation.test.ts`: TC-EHA-031; `deploy/local/scripts/s1-outage.ts`: TC-EHA-084, TC-EHA-085; `.github/workflows/ci.yml`: TC-EHA-084, TC-EHA-085 |
| L1-10 | Pass | `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-009; `services/control-gateway/test/flows.test.ts`: TC-EHA-009, TC-EHA-010, TC-EHA-014, TC-EHA-017, TC-EHA-021; `packages/credentials/test/token.test.ts`: TC-EHA-010; `packages/credentials/test/records.test.ts`: TC-EHA-014; `services/control-gateway/test/failures.test.ts`: TC-EHA-023 |
| L1-11 | Pass | `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-009, TC-EHA-015, TC-EHA-016, TC-EHA-032; `services/control-gateway/test/flows.test.ts`: TC-EHA-009, TC-EHA-010; `packages/credentials/test/token.test.ts`: TC-EHA-010 |
| L1-12 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-021 |
| L1-13 | Pass | `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-009, TC-EHA-016; `services/control-gateway/test/flows.test.ts`: TC-EHA-009, TC-EHA-010; `packages/credentials/test/token.test.ts`: TC-EHA-010 |
| L1-14 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-005; `services/control-gateway/test/flows.test.ts`: TC-EHA-021 |
| L1-15 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-001; `packages/env-store/test/store.test.ts`: TC-EHA-035; `packages/registry/test/registry.test.ts`: TC-EHA-035 |
| L1-16 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-005, TC-EHA-006; `services/control-gateway/test/flows.test.ts`: TC-EHA-007; `packages/authority/test/human.test.ts`: TC-EHA-008 |
| L1-17 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-013, TC-EHA-038; `services/control-gateway/test/flows.test.ts`: TC-EHA-013, TC-EHA-038 |
| L1-18 | Pass | `packages/authority/test/human.test.ts`: TC-EHA-008 |
| L1-19 | Pass | `packages/authority/test/human.test.ts`: TC-EHA-012; `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-015 |
| L1-20 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-002; `services/control-gateway/test/flows.test.ts`: TC-EHA-002, TC-EHA-003, TC-EHA-004, TC-EHA-011; `packages/authority/test/human.test.ts`: TC-EHA-011 |
| L1-21 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-010; `services/control-gateway/test/flows.test.ts`: TC-EHA-010; `deploy/test/compose-model.test.ts`: TC-EHA-022; `services/control-gateway/test/isolation.test.ts`: TC-EHA-022; `packages/registry/test/registry.test.ts`: TC-EHA-040 |
| L1-22 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-018, TC-EHA-041 |
| L1-23 | Pass | TC-OI-022 (`packages/org-identity/test/store.test.ts`: the app role has no DELETE on principals); TC-EHA-080 (`packages/env-store/test/store.test.ts`: no DELETE on grants, credentials, attribution records) |
| L1-24 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-005, TC-EHA-027; `services/control-gateway/test/flows.test.ts`: TC-EHA-027 |
| L1-25 | Pass | `services/control-gateway/test/failures.test.ts`: TC-EHA-023, TC-EHA-043; `services/control-gateway/test/org-level.test.ts`: TC-EHA-043 |
| L1-26 | Pass | `services/control-gateway/test/flows.test.ts`: TC-EHA-001; `packages/registry/test/registry.test.ts`: TC-EHA-005 |
| L1-27 | Pass | `packages/authority/test/human.test.ts`: TC-EHA-012 |
| L1-28 | Pass | `packages/authority/test/human.test.ts`: TC-EHA-012; `services/control-gateway/test/closure.test.ts`: TC-EHA-044 |
| L1-29 | Pass | `packages/credentials/test/records.test.ts`: TC-EHA-014; `services/control-gateway/test/flows.test.ts`: TC-EHA-014; `services/control-gateway/test/failures.test.ts`: TC-EHA-023 |
| L1-30 | Pass | `packages/credentials/test/token.test.ts`: TC-EHA-010, TC-EHA-045; `services/control-gateway/test/flows.test.ts`: TC-EHA-010 |
| L1-31 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-005; `services/control-gateway/test/flows.test.ts`: TC-EHA-021; `packages/attribution/test/record.test.ts`: TC-EHA-046, TC-EHA-047 |
| L1-32 | Pass | `packages/registry/test/registry.test.ts`: TC-EHA-005 |
| L1-33 | Pass | `packages/perimeter/test/environment-presenter.test.ts`: TC-EHA-009; `services/control-gateway/test/flows.test.ts`: TC-EHA-009, TC-EHA-049; `packages/perimeter/test/environment-sign-in.test.ts`: TC-EHA-064 |

### U5 `agent-registration` (32 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001, TC-AR-023, TC-AR-024; `services/control-gateway/test/registration.test.ts`: TC-AR-001, TC-AR-023 |
| L1-02 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001, TC-AR-025; `services/control-gateway/test/registration.test.ts`: TC-AR-001 |
| L1-03 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001; `services/control-gateway/test/registration.test.ts`: TC-AR-001, TC-AR-008, TC-AR-026; `e2e/agent-registration.test.ts`: TC-AR-008 |
| L1-04 | Pass | `packages/authority/test/registration.test.ts`: TC-AR-002; `packages/registry/test/registrations.test.ts`: TC-AR-019; `services/control-gateway/test/registration.test.ts`: TC-AR-019 |
| L1-05 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001; `services/control-gateway/test/registration.test.ts`: TC-AR-001, TC-AR-018 |
| L1-06 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-004, TC-AR-005; `packages/authority/test/registration.test.ts`: TC-AR-012 |
| L1-07 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-003 |
| L1-08 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001; `services/control-gateway/test/registration.test.ts`: TC-AR-001 |
| L1-09 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001, TC-AR-027; `services/control-gateway/test/registration.test.ts`: TC-AR-001 |
| L1-10 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-027; `tools/test/code-checks.test.ts`: TC-AR-028 |
| L1-11 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-009, TC-AR-018; `packages/authority/test/registration.test.ts`: TC-AR-029 |
| L1-12 | Pass | `packages/authority/test/registration.test.ts`: TC-AR-010, TC-AR-011, TC-AR-030; `services/control-gateway/test/registration-structure.test.ts`: TC-AR-031 |
| L1-13 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-032 |
| L1-14 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-014 |
| L1-15 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-015, TC-AR-033 |
| L1-16 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-006, TC-AR-034 |
| L1-17 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-013, TC-AR-035 |
| L1-18 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-006 |
| L1-19 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-006, TC-AR-020, TC-AR-036 |
| L1-20 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-009, TC-AR-021; `packages/authority/test/registration.test.ts`: TC-AR-010, TC-AR-011, TC-AR-012 |
| L1-21 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-007, TC-AR-037 |
| L1-22 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001; `services/control-gateway/test/registration.test.ts`: TC-AR-001 |
| L1-23 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-014 |
| L1-24 | Pass | `services/control-gateway/test/registration-structure.test.ts`: TC-AR-031; `packages/authority/test/held.test.ts`: TC-AR-038 |
| L1-25 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-039; `services/control-gateway/test/registration.test.ts`: TC-AR-042 |
| L1-26 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-040 |
| L1-27 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-007, TC-AR-041 |
| L1-28 | Pass | `contract/test/control-gateway-registration.test.ts`: TC-AR-022 |
| L1-29 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-016, TC-AR-042 |
| L1-30 | Pass | `services/control-gateway/test/registration.test.ts`: TC-AR-008; `e2e/agent-registration.test.ts`: TC-AR-008 |
| L1-31 | Pass | `packages/authority/test/registration.test.ts`: TC-AR-011 |
| L1-32 | Pass | `packages/registry/test/registrations.test.ts`: TC-AR-001; `services/control-gateway/test/registration.test.ts`: TC-AR-001 |

### U6 `agent-credentials` (34 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-001, TC-AC-016 |
| L1-02 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-001, TC-AC-003; `packages/credentials/test/agent-records.test.ts`: TC-AC-023; `packages/credentials/test/agent-token.test.ts`: TC-AC-023 |
| L1-03 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-002, TC-AC-024 |
| L1-04 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-001; `services/data-gateway/test/refusals.test.ts`: TC-AC-014, TC-AC-025; `e2e/agent-credentials.test.ts`: TC-AC-025 |
| L1-05 | Pass | `packages/agent-identity/test/resolver.test.ts`: TC-AC-022, TC-AC-026; `services/data-gateway/test/refusals.test.ts`: TC-AC-022 |
| L1-06 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-007; `services/data-gateway/test/flows.test.ts`: TC-AC-027 |
| L1-07 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-003, TC-AC-011, TC-AC-016; `services/data-gateway/test/refusals.test.ts`: TC-AC-009; `e2e/agent-credentials.test.ts`: TC-AC-009 |
| L1-08 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-009, TC-AC-025; `e2e/agent-credentials.test.ts`: TC-AC-009, TC-AC-025 |
| L1-09 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-018 |
| L1-10 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-028; `e2e/agent-credentials.test.ts`: TC-AC-028 |
| L1-11 | Pass | `services/data-gateway/test/failures.test.ts`: TC-AC-010; `packages/credentials/test/revocation.test.ts`: TC-AC-015, TC-AC-054, TC-AC-065 |
| L1-12 | Pass | `contract/test/data-gateway.test.ts`: TC-AC-021 |
| L1-13 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-016 |
| L1-14 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-018 |
| L1-15 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-007, TC-AC-008, TC-AC-022; `packages/agent-identity/test/resolver.test.ts`: TC-AC-022 |
| L1-16 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-029 |
| L1-17 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-011; `services/data-gateway/test/refusals.test.ts`: TC-AC-013 |
| L1-18 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-030 |
| L1-19 | Pass | `contract/test/data-gateway.test.ts`: TC-AC-021 |
| L1-20 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-031 |
| L1-21 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-032 |
| L1-22 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-013; `packages/env-store/test/agent-credentials.test.ts`: TC-AC-033 |
| L1-23 | Pass | `deploy/test/data-gateway.test.ts`: TC-AC-020 |
| L1-24 | Pass | `packages/credentials/test/revocation.test.ts`: TC-AC-034 |
| L1-25 | Pass | `services/data-gateway/test/refusals.test.ts`: TC-AC-007, TC-AC-009, TC-AC-014; `e2e/agent-credentials.test.ts`: TC-AC-009; `services/data-gateway/test/failures.test.ts`: TC-AC-010; `services/data-gateway/test/flows.test.ts`: TC-AC-011 |
| L1-26 | Pass | `packages/credentials/bench/revocation.bench.ts`: TC-AC-066; `e2e/perf/stack-latency.test.ts`: TC-AC-067 |
| L1-27 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-005, TC-AC-035; `e2e/agent-credentials.test.ts`: TC-AC-005; `packages/attribution/test/envelope-free.test.ts`: TC-AC-036 |
| L1-28 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-019 |
| L1-29 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-004; `e2e/agent-credentials.test.ts`: TC-AC-004; `services/data-gateway/test/refusals.test.ts`: TC-AC-037 |
| L1-30 | Pass | `services/data-gateway/test/flows.test.ts`: TC-AC-001, TC-AC-003; `contract/test/data-gateway.test.ts`: TC-AC-021 |
| L1-31 | Pass | `packages/credentials/test/revocation.test.ts`: TC-AC-015; `packages/credentials/test/published-bounds.test.ts`: TC-AC-038 |
| L1-32 | Pass | `packages/perimeter/test/agent-presenter.test.ts`: TC-AC-012, TC-AC-039 |
| L1-33 | Pass | `deploy/local/scripts/s1-outage.ts`: TC-AC-017; `deploy/local/scripts/stack-client.ts`: TC-AC-017; `services/data-gateway/test/closure.test.ts`: TC-AC-040; `tools/test/image-packages.test.ts`: TC-AC-083 |
| L1-34 | Pass | `tools/test/agent-credentials-review.test.ts`: TC-AC-041 |

### U7 `event-transport` (36 rows)

| Row | Result | Evidence (this run) |
|---|---|---|
| L1-01 | Pass | `e2e/agent-registration.test.ts`: TC-ET-001; `contract/test/event-ingest.test.ts`: TC-ET-024 |
| L1-02 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-007; `e2e/agent-registration.test.ts`: TC-ET-002 |
| L1-03 | Pass | `e2e/agent-registration.test.ts`: TC-ET-002 |
| L1-04 | Pass | `e2e/event-transport.test.ts`: TC-ET-023 |
| L1-05 | Pass | `e2e/agent-registration.test.ts`: TC-ET-003 |
| L1-06 | Pass | `contract/test/event-ingest.test.ts`: TC-ET-024; `packages/authority/test/body-form.test.ts`: TC-ET-025; `services/event-ingest/test/refusals.test.ts`: TC-ET-025 |
| L1-07 | Pass | `e2e/agent-registration.test.ts`: TC-ET-002; `services/event-ingest/test/refusals.test.ts`: TC-ET-019 |
| L1-08 | Pass | `e2e/agent-registration.test.ts`: TC-ET-002; `services/event-ingest/test/refusals.test.ts`: TC-ET-008 |
| L1-09 | Pass | `e2e/event-transport.test.ts`: TC-ET-020, TC-ET-005 |
| L1-10 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-009; `e2e/event-transport.test.ts`: TC-ET-009 |
| L1-11 | Pass | `e2e/event-transport.test.ts`: TC-ET-005; `services/event-ingest/test/flows.test.ts`: TC-ET-026 |
| L1-12 | Pass | `e2e/agent-registration.test.ts`: TC-ET-001; `services/event-ingest/test/refusals.test.ts`: TC-ET-010 |
| L1-13 | Pass | `e2e/agent-registration.test.ts`: TC-ET-001; `services/event-ingest/test/refusals.test.ts`: TC-ET-011 |
| L1-14 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-010, TC-ET-011 |
| L1-15 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-021, TC-ET-027 |
| L1-16 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-021; `services/event-ingest/test/streams.test.ts`: TC-ET-016 |
| L1-17 | Pass | `services/event-ingest/test/revocation.test.ts`: TC-ET-014, TC-ET-028; `e2e/event-transport.test.ts`: TC-ET-014, TC-ET-028; `services/data-gateway/test/refusals.test.ts`: TC-AC-009; `e2e/agent-credentials.test.ts`: TC-AC-009; `services/data-gateway/test/failures.test.ts`: TC-AC-010; `packages/credentials/test/revocation.test.ts`: TC-AC-015; `services/event-ingest/test/streams.test.ts`: TC-ET-029 |
| L1-18 | Pass | `packages/config/test/event-ingest.test.ts`: TC-ET-030; `services/event-ingest/test/composition.test.ts`: TC-ET-030 |
| L1-19 | Pass | `services/event-ingest/test/streams.test.ts`: TC-ET-031; `e2e/event-transport.test.ts`: TC-ET-031 |
| L1-20 | Pass | `services/event-ingest/test/streams.test.ts`: TC-ET-016, TC-ET-017; `e2e/event-transport.test.ts`: TC-ET-017 |
| L1-21 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-006; `e2e/agent-registration.test.ts`: TC-ET-006 |
| L1-22 | Pass | `e2e/event-transport.test.ts`: TC-ET-015; `services/event-ingest/test/refusals.test.ts`: TC-ET-006; `e2e/agent-registration.test.ts`: TC-ET-006 |
| L1-23 | Pass | `services/event-ingest/test/revocation.test.ts`: TC-ET-032 |
| L1-24 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-021 |
| L1-25 | Pass | `services/event-ingest/test/composition.test.ts`: TC-ET-033 |
| L1-26 | Pass | `e2e/agent-registration.test.ts`: TC-ET-004; `e2e/event-transport.test.ts`: TC-ET-005; `services/event-ingest/test/flows.test.ts`: TC-ET-034; `services/event-ingest/test/revocation.test.ts`: TC-ET-035 |
| L1-27 | Pass | `e2e/agent-registration.test.ts`: TC-ET-002, TC-ET-004 |
| L1-28 | Pass | `services/data-gateway/test/failures.test.ts`: TC-AC-010; `services/event-ingest/test/streams.test.ts`: TC-ET-029 |
| L1-29 | Pass | `e2e/perf/stack-latency.test.ts`: TC-ET-036 |
| L1-30 | Pass | `e2e/event-transport.test.ts`: TC-ET-018 |
| L1-31 | Pass | `services/event-ingest/test/flows.test.ts`: TC-ET-037; `e2e/event-transport.test.ts`: TC-ET-037 |
| L1-32 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-006; `e2e/agent-registration.test.ts`: TC-ET-006 |
| L1-33 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-012 |
| L1-34 | Pass | `services/event-ingest/test/refusals.test.ts`: TC-ET-013 |
| L1-35 | Pass | `contract/test/event-ingest.test.ts`: TC-ET-024, TC-ET-038 |
| L1-36 | Pass | `deploy/local/scripts/s1-outage.ts`: TC-ET-022 |
