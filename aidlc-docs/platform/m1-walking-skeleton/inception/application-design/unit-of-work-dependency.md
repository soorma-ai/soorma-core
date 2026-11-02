# Unit Dependencies: soorma-core M1

## Dependency Matrix

A row depends on a column: it needs something the column builds.

| | U1 contract | U2 org-identity | U3 authority | U4 env-human-access | U5 agent-registration | U6 agent-credentials | U7 event-transport |
|---|---|---|---|---|---|---|---|
| **U1** | — | | | | | | |
| **U2** | ✓ conventions | — | | | | | |
| **U3** | ✓ envelope schema | | — | | | | |
| **U4** | ✓ | ✓ verify-only material; principal lookup | ✓ P3 (extends it) | — | | | |
| **U5** | ✓ | | ✓ | ✓ `evaluateHuman`; grants and held set; attribution; human credential checks | — | | |
| **U6** | ✓ | | | ✓ P5 primitives (extends them); attribution | ✓ registrations; secrets | — | |
| **U7** | ✓ (completes it) | | ✓ envelope; `evaluateAgent`; origin | ✓ attribution | ✓ registrations (autonomy, standing set) | ✓ agent credentials; revocation read | — |

**No cycles.** The sequence U1 → U2 → U3 → U4 → U5 → U6 → U7 is a topological order.
U2 and U3 are independent of each other; the plan keeps U2 first to follow the journey.

**No data-face unit depends on U2 at runtime.** U6 and U7 never call the organization level
(M1-NFR-08). U4, a control-face unit, is the only one that does.

---

## Shared Contracts Between Faces (Step 2.5, rule 2)

| Capability | Control unit | Data unit | Contract they share |
|---|---|---|---|
| Permission model (PF FR-018) | U4 (grants), U5 (standing sets) | U3 (evaluation) | The grant and registration records (principal, environment, permission set, *granted-by*); the plane-declared identifier set (GAP-INT-006); the `seams/policy-decision` interface (containment only) |
| Credentials and revocation | U4 (human environment credentials: issue, renew, end) | U6 (agent credentials; the per-request revocation read) | **Revocation state** (keyed by credential reference, per environment); **per-environment minting material** (P5), never shared across environments; the credential claim set (subject, environment, kind, expiry) |
| Revocation initiation | **Absent** (PF FR-011 deferred) | U6 reads | Revocation state. Agent revocation is seeded by a test-only path, not compiled into the product |
| Identity resolution (PF §12 v1.3) | U2 (K, P at the organization level) | U6 (the registration secret) | The `seams/identity-resolution` interface: material type to agent registration reference, human principal reference, or rejection |
| Human identity across levels | U2 (organization level) | — (no human data face in M1) | **Verify-only sign-in material** and `principalExists`, consumed by U4 only |

---

## Integration Checkpoints

| After | Demonstrable | How |
|---|---|---|
| U2 | A configured first Admin activates and signs in | Integration tests in `services/org-gateway` |
| U4 | H holds an E credential and self-grants | Integration across S1 and S2 |
| **U5** | ***Done when* 1** | `e2e/` raw calls: two registrations, each with a sponsor and a snapshot |
| **U6** | ***Done when* 2** | `e2e/` raw calls: bootstrap and renewal |
| **U7** | ***Done when* 3, 4, 6, 7** | `e2e/` raw calls with E and E2. **The schema is then tagged** on `main` for soorma-sdk's Construction (execution plan, two-step publication) |

---

## Gap Assignment (Step 2.4)

| Gap | Units | Status |
|---|---|---|
| GAP-INT-001 | U2, U4 | Resolved, answered elsewhere |
| GAP-INT-002 | U4 | Resolved, answered elsewhere |
| GAP-INT-003 | **U7**, U1 | Awaiting PRD: Event; worked around |
| GAP-INT-004 | U3, U5 | Resolved, PRD amended |
| GAP-INT-005 | U5, U4 | Resolved, PRD amended |
| GAP-INT-006 | **U4, U5** | Open, soorma-prd#24; worked around |
| GAP-INT-007 | **U3, U7** | Open, soorma-prd#25; worked around |
| GAP-INT-008 | **U6, U1** | Open, soorma-prd#27; worked around |
| *Unclassified*: attribution for the revocation read | U6 | Classification question pending |
