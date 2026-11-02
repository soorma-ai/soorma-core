# Units of Work: soorma-core M1

**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`, both kind `plane`
**Shape**: **plane-face units** (units-generation.md Step 2.5). One unit is one face of
one capability, with one NFR profile, edition `core`, and repository `soorma-core`. U1 is
a contract unit and has no face (plan Q1 B).
**Sequence**: U1 → U2 → U3 → U4 → U5 → U6 → U7. Each unit is designed and built fully
before the next starts.
**Decisions** (unit-of-work plan, approved 2026-11-02):

| Q | Decision |
|---|---|
| Q1 B | U1 produces the cross-surface contract parts. Each surface unit adds its own operations. The schema is tagged after U7's Code Generation |
| Q2 A | S2 is split into U4 (ID) and U5 (PF) |
| Q3 X | U3 introduces P3 with agent evaluation (data face). U4 builds `evaluateHuman` as P3's control-face extension. P3 stays the one module computing authority (I5) |
| Q4 A | No data-face unit for the human side in M1. ID §9's operations are delegation, which is out of scope. ID is not single-face |
| Approval | Cross-cutting requirements are listed in every unit that touches them. M1-FR-12 is also in U6 |

Components (S, P) refer to [components.md](components.md).

---

## U1 `wire-contract`

| Field | Value |
|---|---|
| Capability | The wire contract's cross-surface parts |
| Face | **none**: a contract unit (Q1 B) |
| NFR profile source | — (governed by I7 and PF §7 *Compatibility Policy*; M1-TECH-02) |
| Edition / repository | core / soorma-core; **licence Apache 2.0** (PF §22) |
| Builds | `contract/envelope.schema.json`, `contract/delivery.schema.json` (named `Delivery`), and the shared conventions: contract versioning, the client contract version, the error model, security schemes, and the pre-release status statement. Also the type-generation pipeline (M1-TECH-02) |
| Operations (from PRD) | None. The surface units add operations |
| M1-FRs | 02 |
| Inherited gaps | GAP-INT-008 (the contract states that bootstrap and renewal carry no envelope); GAP-INT-003 (the pre-release status and the "delivery semantics unspecified" statement) |
| Proves | Nothing alone. Every *done when* item depends on it |

## U2 `org-identity`

| Field | Value |
|---|---|
| Capability | Human principals and the organization sign-in |
| Face | **control** |
| NFR profile source | ID §10 *NFR Profile* @ `prd-identity-v1.0`; M1-NFR-08 |
| Edition / repository | core / soorma-core |
| Builds | S1 `org-gateway`; P10 `org-identity`; P6's human half (K, P); P8 per principal; P9's organization half (`ensureFirstAdmin`); P1's sign-in checks; the S1 operations in `contract/org-gateway.openapi.yaml` |
| Operations (from PRD) | ID §10: authenticate; first authentication; self-service on one's own sign-in and material |
| M1-FRs | 16, 17, 18, 19, 21; also 02, 09, 10, 12, 13 (identity: K, P), 14 |
| Inherited gaps | GAP-INT-001 (resolved by ID; recorded for traceability) |
| Proves | *Done when* 1, steps 2 and 3 of ID §1's trace (partial) |

## U3 `authority-evaluation`

| Field | Value |
|---|---|
| Capability | Authority evaluation (PF FR-018 *evaluation*) and the envelope |
| Face | **data** |
| NFR profile source | PF §9 *NFR Profile* @ `prd-platform-foundations-v1.3` (per-request hot path) |
| Edition / repository | core / soorma-core |
| Builds | P2 `envelope`; P3 `authority` (agent evaluation: intersection, origin, O12, re-broadening); P11 `policy-decision`; `seams/policy-decision` |
| Operations (from PRD) | PF §8b *Evaluation Mechanism*; PF §7b *Envelope Fields*. They have no edge operation of their own |
| M1-FRs | 01, 08 (agent evaluation), 13 (policy half) |
| Inherited gaps | GAP-INT-007 (reject and stamp: origin is never accepted from a draft); GAP-INT-004 (resolved: the re-broadening rule, built as stated) |
| Proves | Nothing at the edge. It is verified at the authority-evaluation level with constructed chains (US-09), and it underpins *done when* 4 and 7 |

## U4 `env-human-access`

| Field | Value |
|---|---|
| Capability | Human access in an environment |
| Face | **control** |
| NFR profile source | ID §10 *NFR Profile* @ `prd-identity-v1.0`: **one profile**. The grant record's durability and attribution (PF §10) are record constraints that agree with it, not a second profile |
| Edition / repository | core / soorma-core |
| Builds | S2 `control-gateway` (human access operations); P3's control-face extension `evaluateHuman`; P1's human-credential checks and the presenter matrix at S2; P4 grants and the accepted-identifier set; P5's human environment credentials (minting, verification, end); P7 `attribution` (introduced here); P9's environment half (first grant). It adds S2's human operations to `contract/control-gateway.openapi.yaml` |
| Operations (from PRD) | ID §10: obtain, renew, end environment credentials; grant to a human. PF §10: *Grant permissions to a human principal*; first grant by configuration (ID FR-004) |
| M1-FRs | 09 (human), 12, 14, 15, 20, 21; also 02, 07, 08 (`evaluateHuman`), 10 (verify-only material) |
| Inherited gaps | **GAP-INT-006** (only plane-declared identifiers accepted, soorma-prd#24); GAP-INT-001, GAP-INT-002 and GAP-INT-005 (resolved: human credentials, the first grant, the `grant:human` ceiling) |
| Proves | *Done when* 1, steps 4 and 5 (partial) |

## U5 `agent-registration`

| Field | Value |
|---|---|
| Capability | Logical agent registration and registration secrets |
| Face | **control** |
| NFR profile source | PF §10 *NFR Profile* @ `prd-platform-foundations-v1.3` (registrations: the highest durability) |
| Edition / repository | core / soorma-core |
| Builds | S2's agent-registration operations; P4 registrations (eight attributes, the ceiling against the held set, the human-only class, declaration ⊆ standing) and secrets (issuer). It adds S2's registration operations to `contract/control-gateway.openapi.yaml` |
| Operations (from PRD) | PF §10: register a logical agent; grant standing permissions; issue a registration secret |
| M1-FRs | 03, 04; also 02, 08 (consumes `evaluateHuman`), 12, 15 (standing sets) |
| Inherited gaps | **GAP-INT-006** (standing sets limited to plane-declared identifiers); GAP-INT-004 and GAP-INT-005 (resolved). Delivery decision: registration and issuance **by an agent** are absent (requirements, *Absent from M1*) |
| Proves | ***Done when* 1** (ID §1 trace, steps 6 to 9) |

## U6 `agent-credentials`

| Field | Value |
|---|---|
| Capability | Agent credentials and the revocation read |
| Face | **data** |
| NFR profile source | PF §9 *NFR Profile* @ `prd-platform-foundations-v1.3`: startup (bootstrap), periodic (renewal), and the per-request revocation read |
| Edition / repository | core / soorma-core |
| Builds | S3 `data-gateway`; P5's agent credentials and the **fail-closed revocation cache**; P6's agent half (the registration secret); P8 per registration; P1's agent-credential checks at S3, including refusing human credentials by kind; attribution for bootstrap and renewal. It adds S3's operations to `contract/data-gateway.openapi.yaml` |
| Operations (from PRD) | PF §9: exchange bootstrap material; renew a credential; read revocation state |
| M1-FRs | 05, 06, 07, 13 (identity: registration secret); also 02, 09, 10, 12 (bootstrap, renewal) |
| Inherited gaps | **GAP-INT-008** (neither bootstrap nor renewal carries an envelope, soorma-prd#27). **GAP-INT-009** (the internal revocation read writes no attribution record) |
| Proves | ***Done when* 2**, by raw calls |

## U7 `event-transport`

| Field | Value |
|---|---|
| Capability | Event publish and subscribe within an environment |
| Face | **data** |
| NFR profile source | PF §9 *NFR Profile* @ `prd-platform-foundations-v1.3` (per request) |
| Edition / repository | core / soorma-core |
| Builds | S4 `event-ingest` (publish; subscribe as SSE delivering `Delivery`); the env fan-out channel; P1's agent obligations O1 to O12 at ingest. It adds S4's operations to `contract/event-ingest.openapi.yaml`, **completing the contract**, and the schema is then tagged |
| Operations (from PRD) | PF §8a: publish to, and subscribe on, an event namespace |
| M1-FRs | 09 (agent), 10, 11; also 01, 02, 07, 08, 12 (publish) |
| Inherited gaps | **GAP-INT-003** (live subscribers only; Awaiting PRD: Event, soorma-prd#13); **GAP-INT-007** (origin stamped at every first hop, soorma-prd#25) |
| Proves | ***Done when* 3, 4, 6, 7**, by raw calls |

---

## Requirement Coverage

| M1-FR | Units |
|---|---|
| 01 | U3, U7 |
| 02 | U1, U2, U4, U5, U6, U7 |
| 03 | U5 |
| 04 | U5 |
| 05 | U6 |
| 06 | U6 |
| 07 | U4, U6, U7 |
| 08 | U3, U4, U5, U7 |
| 09 | U2, U4, U6, U7 |
| 10 | U2, U4, U6, U7 |
| 11 | U7 |
| 12 | U2, U4, U5, U6, U7 |
| 13 | U2, U3, U6 |
| 14 | U2, U4 |
| 15 | U4, U5 |
| 16 to 19 | U2 |
| 20 | U4 |
| 21 | U2, U4 |

Every M1-FR is covered. Each unit's Functional Design and L1 coverage matrix trace every
requirement listed for it.

---

## Code Organization Strategy (greenfield)

**Pattern**: the approved Application Design layout (Q5 X), **not** the default
`{unit-name}/src/` pattern. Units and deployables do not map one to one: U4 and U5 share
`control-gateway`, and U3 is modules only. So a unit is the set of directories it creates
or extends.

```text
soorma-core/
  contract/                Apache-2.0, published (two steps)
    envelope.schema.json        U1
    delivery.schema.json        U1
    conventions/                U1 (versioning, errors, security schemes)
    org-gateway.openapi.yaml    U2
    control-gateway.openapi.yaml  U4, U5
    data-gateway.openapi.yaml   U6
    event-ingest.openapi.yaml   U7
    generated/                  U1 pipeline; regenerated by each unit
  seams/                   Apache-2.0, unpublished in M1
    policy-decision/            U3
    identity-resolution/        U2 (human half), U6 (agent half)
  packages/                FSL; each has src/ and test/
    perimeter/                  U2; extended by U4, U6, U7
    envelope/                   U3
    authority/                  U3; extended by U4 (evaluateHuman)
    policy-decision/            U3
    registry/                   U4 (grants); extended by U5
    credentials/                U4 (human); extended by U6 (agent, cache)
    identity-resolution/        U2 (K, P); extended by U6 (secret)
    attribution/                U4; used by U5, U6, U7
    abuse-bound/                U2; extended by U6
    config/                     U2 (organization); extended by U4
    org-identity/               U2
  services/                FSL; each has src/ and test/
    org-gateway/                U2
    control-gateway/            U4, U5
    data-gateway/               U6
    event-ingest/               U7
  deploy/local/            the local stack (organization level, E, E2)
  e2e/                     raw-call proofs of the done-when items
```

- **Licence files**: `contract/` and `seams/` carry Apache 2.0. `packages/` and
  `services/` carry FSL-1.1-ALv2 (PF §22)
- **Tests**: unit tests in each `packages/*/test` and `services/*/test`. Each unit's
  integration tests are in its services' `test/`. Raw-call *done when* proofs are in
  `e2e/`, added by the unit that makes each item demonstrable (U5: 1; U6: 2; U7: 3, 4, 6,
  7) and run in full at Build and Test
- **`deploy/local/`**: each unit's Infrastructure Design adds its deployables. The whole
  stack (M1-NFR-05) is complete after U7
- **Dependency discipline** (M1-TECH-04): one workspace lockfile, created at U1
- **Never** `aidlc-docs/` for code
