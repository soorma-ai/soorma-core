# Integration Test Instructions

How the seven units work together, on the local stack: S1 `org-gateway` (the organization
level), and per environment (`e`, `e2`) S2 `control-gateway`, S3 `data-gateway`, S4 `event-ingest`,
each with its own store and network. Every run below uses a **fresh stack**: H's first
authentication happens once per stack, from the handover file.

## Set up

```bash
pnpm install --frozen-lockfile && pnpm run build     # the e2e tests import the built workspace
# the four images, as in build-instructions.md, step 5
pnpm stack:init      # generates every secret into deploy/local/.secrets/ (never overwrites one)
```

A fresh stack, before each scenario:

```bash
docker compose -f deploy/local/compose.yaml down -v
pnpm stack:up
```

`down -v` matters: without it the next scenario meets a stack whose first authentication is spent,
and its set-up fails with 403 (seen once in this run, from a shell that did not run the `down`; the
re-run on fresh volumes passed).

## Scenarios

### 1. The smoke test: every deployable, both environments (`pnpm stack:smoke`)

S1 to S4 healthy over TLS 1.3; each store's roles and privileges; the first Admin's journey to
a credential; a real round trip per environment at S4 (the Delivery's scope and seal); E's agent
credential refused at E2's S4; each service connected as its own database role; the logs carry no
identifier and no secret.

**Result: Pass, 106 checks.**

### 2. The organization level stopped (`pnpm stack:outage`; U4 Infrastructure Design §11; TC-EHA-084, 085; TC-AC-017; U7's case 4)

| Case | What it shows | Checks |
|---|---|---|
| Set-up | first authentication, a sign-in, credentials for E and E2, one ended | 4 |
| 1 | S1 stops while E's S2 holds the verify keys: issuance, renewal, and `grantToHuman` 503 with `Retry-After: 5`; ending still works; refusals unchanged; recovery when S1 answers | 10 |
| 2 | E's S2 starts while S1 is stopped: healthy; issuance 503 (no verify keys); a credential issued before passes O1 to O4; recovery on the next fetch | 7 |
| 3 | S3 serves bootstrap and renewal with S1 stopped, running and restarted | 8 |
| 4 | S4 serves publish, subscribe, and delivery with S1 stopped, running and restarted | 11 |

**Result: Pass, 40 checks.** This is U4's accepted residual, the organization-level outage
(D-EHA-23), shown on the stack: during it, issuance, renewal, and `grantToHuman` are unavailable,
while ending and the data face are unaffected.

### 3. The e2e proofs and the cross-unit journeys (`pnpm test:e2e`)

One ordered journey through U4 to U7 by raw HTTPS calls (`e2e/agent-registration.test.ts`), then
U6's and U7's own files. Detailed in `e2e-test-instructions.md`.

**Result: Pass, 27 of 27 tests, 3 files** (119 s).

| Unit pair | Shown by |
|---|---|
| U2 → U4 (sign-in to environment credential) | TC-AR-008's set-up; smoke; outage case 1 |
| U4 → U5 (`evaluateHuman`, the ceiling snapshot) | TC-AR-008, TC-AR-043 |
| U5 → U6 (the registration secret's one definition) | TC-AC-093 |
| U6 → U7 (agent credential, revocation within B) | TC-ET-014, 017, 028, 031 (61 s, the bound) |
| U3 inside U7 (admission, stamping, the seal) | TC-ET-002 to 007, 090, 005 |
| U1 everywhere (the contract and Problems) | TC-ET-040, TC-AR-043 (each refusal a Problem) |
| Backup and restore (U5) with U6's and U7's services stopped by name | TC-AR-059, 056, 060 |

### 4. In-process integration (part of `pnpm test`)

The unit suite also runs each gateway's real edge over a real test store: the flows in
`services/*/test/`, the rotation tests TC-EHA-062 and 063 (NFR-EHA-08a, with S2's refresh clock
controlled: they need a test clock, so they run in process), the Compose-model tests (TC-EHA-079),
the privilege tests (TC-EHA-080 and each unit's), and the docs tests (TC-EHA-081). All passed.

## Cleanup

```bash
docker compose -f deploy/local/compose.yaml down -v
```
