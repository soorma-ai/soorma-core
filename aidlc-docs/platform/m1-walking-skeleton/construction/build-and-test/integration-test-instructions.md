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

`down -v` matters: H's enrollment material is single use, so a scenario that starts on a stack an
earlier scenario used fails its set-up with a 403 at first authentication. Check the `down -v`'s exit
code: in this stage's first run it failed silently and the outage scenario failed (*Runs*, below).

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

**Result: one failed run (run 1), then four passing runs of 40 of 40 checks (runs 2, 5, 6, 7)** (the runs are below). This is
U4's accepted residual, the organization-level outage
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

## Runs, Including the Failed One

Every stack run of this stage, in order, on 2026-11-13. A failed run stays in the record.

| # | Sequence | Smoke | Outage | e2e |
|---|---|---|---|---|
| 1 | `down -v`, init, up, smoke, `down -v`, up, outage | Pass, 106 | **FAIL: 30 of 40 failed; exit 1** | — |
| 2 | `down -v`, up, outage | — | Pass, 40 of 40 | — |
| 3 | `down -v`, up, `test:e2e` | — | — | Pass, 27 of 27 |
| 4 | `down -v`, up, `test:perf:stack`, then `test:perf` (performance-test-instructions.md) | — | — | — (both passed) |
| 5 to 7 | Run 1's sequence exactly, three times, every step's output and exit code captured, the stack's volumes recorded around each `down -v` | Pass, each | **Pass, 40 of 40, each** | — |
| 8 | `down -v`, up, smoke, outage, **with no `down -v` between smoke and outage** (deliberate) | Pass | **FAIL: 30 of 40, the same 30 as run 1** | — |

**Run 1's failure.** The outage script's first step, H's first authentication, was refused with 403.
Every later failure followed from it: no sign-in, no credentials, no agents. The script's checks
that need none of these passed (10).

**Cause: established.** The outage script ran on a stack the smoke test had already used, because
neither `down -v` in run 1 ran:

- This session ran run 1 in zsh as `C="docker compose -f deploy/local/compose.yaml"; $C down -v
  > /dev/null 2>&1`. zsh does not split an unquoted parameter into words, so it looked for one
  command named `docker compose -f deploy/local/compose.yaml`: exit 127, *no such file or
  directory*, with the output discarded and the exit code not checked. Shown afterwards with a
  harmless subcommand (`$C version` exits 127; `${=C} version` prints 5.1.4)
- The smoke test had made H's first authentication, so H was `active`. U2's D-OI-02: a
  `firstAuthenticate` on an `active` principal fails with `authentication_failed`, which D-OI-13
  makes a 403. S1 logged it as `auth.failed` with `authentication_failed`, and on its restarts in
  the script, `config.enrollment_ignored` (H already active)
- Run 8 reproduces it on purpose: on a stack the smoke test used, the outage script fails the same
  30 checks, in the same order, starting with the same 403
- Runs 5 to 7 reproduce run 1's sequence exactly with working `down -v`s. Each `down -v` exited 0,
  and every volume the stack's containers mounted (nine) was gone after it. Each outage run passed
  40 of 40, with the first authentication at 200

So the 403 is S1 correctly refusing a repeat first authentication, not a defect, and not a
specification gap. **CI is not exposed**: its `down -v` steps are plain `run:` lines, which fail
the job on a non-zero exit, and each starts from a stack the step before stopped.

Run 1's full output was overwritten by run 2, written to the same log path. It survives as printed
in this stage's session, and its check list matches run 8's check for check. Runs 5 to 8 each wrote
to their own directory.

## Cleanup

```bash
docker compose -f deploy/local/compose.yaml down -v
```
