# Build and Test Summary: M1 Walking Skeleton (soorma-core)

**Run**: 2026-11-13, on `dev` at `4119ac0` (U1 to U7 merged; U7's code as `c1e3d7f` on `main`;
`contract-v0.1.0` tagged on it), plus this stage's two measurement harnesses.
**Inputs**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`; the slice brief
`soorma-prd/backlog/m1-walking-skeleton.md` @ `0aad84a` (unchanged on soorma-prd `main`).

## Build Status

| | |
|---|---|
| Build tool | pnpm 12.18.0, TypeScript 6.0.3, Node 26.13.0; Docker 29.5.3, Compose 5.1.4 |
| Build | **Success** (`pnpm run build`, 18 s) |
| Static checks | **Pass**: deps and register, workflows, lint, format, code (SQL, comparisons, injection), secrets, breached list, generated types, contract; `pnpm audit` no known vulnerabilities |
| Images | **Pass**: S1 to S4 built; each secret-scanned and its installed packages checked; S3 and S4 ship no migrations; S4's `JSON.rawJSON` self-check |
| Artifacts | each package's `dist/`; the four images `soorma/*:local`; CI's CycloneDX SBOM |

Details: `build-instructions.md`.

## Test Execution Summary

| Suite | Result | Details |
|---|---|---|
| Unit and in-process integration (`pnpm test`, with the test database) | **1707 passed, 0 failed**; 30 skipped, all of them stack or perf suites run below | `unit-test-instructions.md` |
| Stack smoke test | **Pass**, 106 checks | `integration-test-instructions.md` |
| The organization level stopped (`stack:outage`) | **One failed run, then four passing** (40 of 40 each). Run 1 failed 30 of 40 at a 403 on first authentication; cause established: this session's `down -v` did not run (zsh exit 127, output discarded), so the script met a stack whose first authentication the smoke test had spent, and S1 refused the repeat as designed (U2 D-OI-02). Reproduced on purpose; run 1's exact sequence then passed three times. Not a defect; CI not exposed | `integration-test-instructions.md`, *Runs* |
| E2E proofs on a fresh stack (`test:e2e`) | **27 of 27 passed** | `e2e-test-instructions.md` |
| Performance | **All within target** (reported; TC-OI-059 gated and passed) | `performance-test-instructions.md` |
| Contract | **Pass**; `contract-v0.1.0` peels to `c1e3d7f` | `contract-test-instructions.md` |
| Security | **Pass**; no blocking finding | `security-test-instructions.md` |

### Performance (p95 on the running stack, TLS 1.3, a new connection per request)

| Case | Operation | p95 | Target |
|---|---|---|---|
| TC-OI-059 | S1 `authenticate` / renew / end | 334 / 20 / 17 ms | 500 / 200 / 200 |
| TC-EHA-070 | S2 issue / renew / end / `grantToHuman` (real S1) | 19.6 / 19.7 / 15.8 / 19.3 ms | 300 / 300 / 200 / 200 |
| TC-AR-064 | S2 `registerAgent` / `issueRegistrationSecret` | 16.4 / 20.8 ms | none (reported) |
| TC-AC-067 | S3 bootstrap / renewal | 23.9 / 19.8 ms | 200 / 200 |
| **TC-ET-036** | **S4 open / publish / publish to delivery** | **18.4 / 16.3 / 16.6 ms** | **200 / 200 / 250** |

In process (p99): TC-AE-040 `admit` 0.593 ms (target 2 ms); **TC-AR-065** `admit` with P4's
source 0.595 ms warm, 2.598 ms cold with P4's read (the statement alone 2.051 ms; NFR-AE-07 excludes
term reads); TC-AC-066 revocation cache hit 0.0013 ms (target 0.1 ms). TC-OI-062: known and unknown
principals' refusal medians differ by 0.36 ms, p = 0.82.

### L1 Domain Conformance

| | |
|---|---|
| Applicable L1 rows (seven units) | **237** |
| Passed | **237** |
| Failed | 0 |
| Unverified | 0 |
| Status | **Pass**; every row `Verified` in its matrix |

Evidence per row: `l1-conformance-test-instructions.md`.

### Invariant Conformance (soorma Platform Invariants)

| | |
|---|---|
| Applicable rows, I1 to I10 × seven units | **70 passed**, 0 failed, 0 unverified |
| I11 | N/A in every unit (Construction selects technology) |
| I8 packaging table, checked as a set | **Pass**: nothing commercial, enabled or stubbed; nothing unassigned; every bound a security bound |
| I2 across the harness surface | **Pass**: each of PF §11's six harness operations enforced at a perimeter, shown by raw call |
| Status | **Pass** |

One correction: U7's I4 row still read `Covered`, a cell missed at Code Generation; it is
`Verified` now with the rest. Evidence: `invariant-conformance-test-instructions.md`.

### Open Obligations (from `aidlc-state.md`)

| | Count | |
|---|---|---|
| Deferred questions targeting this initiative, still open | **0** | none |
| Deferred questions targeting other initiatives | 0 | |
| **PRD specification gaps, `Open`** | **6** | each waits on an amendment to an approved PRD (PF or ID) |
| **PRD specification gaps, `Awaiting PRD`** | **1** | Event plane (no PRD yet) |
| Resolved | 5 | GAP-INT-001, 002, 004, 005; GAP-EHA-001 |

**Every `Open` and `Awaiting PRD` gap records what was deliberately left unbuilt or how it was
worked around**, so none blocks completion of this initiative. Each still blocks the behaviour it
names from being final, and each may change the build when its PRD answers (re-intake).

| Gap | Status | Issue | Built in M1 instead (work-around) |
|---|---|---|---|
| GAP-INT-003 | **Awaiting PRD: Event** | soorma-prd#13 | Live subscribers only. No durability, ordering, redelivery, or acknowledgement, and no topics; the contract states the semantics are unspecified |
| GAP-INT-006 | Open | soorma-prd#24 | Grants and standing sets accept the plane-declared permission identifiers only; tenant-defined identifiers not built |
| GAP-INT-007 | Open | soorma-prd#25 | Origin never accepted from a draft; stamped by the platform at every first hop (reject and stamp) |
| GAP-INT-008 | Open | soorma-prd#27 | Neither bootstrap nor renewal carries an envelope |
| GAP-INT-009 | Open | soorma-prd#28 | The internal revocation read writes no attribution record |
| GAP-AE-001 | Open | soorma-prd#30 | A non-declaring agent forwarding an autonomous envelope is denied (O12) |
| GAP-ET-001 | Open | soorma-prd#31 | Attribution recorded synchronously in E's store, failing closed: **E's store is S4's availability floor** for new publishes and subscribes. During a store outage the caches answer for up to 60 s, open streams stay open, and a malformed or foreign credential is still refused exactly, but no new publish or subscribe proceeds |

### Slice Brief: soorma-core's *Proves* Items

The brief assigns soorma-core *done when* 1, 4, 6, 7, and 2 and 3 **with raw calls and no SDK**.
All six pass, on a fresh stack, in one journey where each step uses the real agents, secrets, and
credentials of the step before (`e2e/agent-registration.test.ts`).

| *Done when* item | Proved by | Result | Evidence |
|---|---|---|---|
| 1. Two logical agents registered in one environment, each with its own sponsor reference and ceiling snapshot | TC-AR-008 | **Pass** | A and B registered in E by H, each `sponsor: h@example.com` and `ceilingSnapshot` H's held set; two `registerAgent` attribution records |
| 2. Each agent instance bootstraps and receives a short-lived credential (raw calls) | TC-AC-093 | **Pass** | An instance of A and one of B bootstrap at E's S3 with the issued secrets and renew; each 200 |
| 3. A publishes; B, subscribed in the same environment, receives it (raw calls) | TC-ET-001 | **Pass** | B's stream (TLS 1.3, `text/event-stream`) carries A's Delivery; publish 202 with no body |
| 4. The envelope B receives carries scope, origin, and an actor chain appended by the perimeter, not by A | TC-ET-002, 003, 004 | **Pass** | Scope E, `originMode: autonomous`, `actorChain: [{ agent: A, instance: a-1 }]` stamped by S4 from a draft carrying none; the publish's record carries the same origin |
| 6. The same publish with a credential from another environment is denied | TC-ET-006 | **Pass** | E2's credential at E, and E's at E2: 401 `credential_refused`; nothing delivered |
| 7. A draft in which the agent sets a platform-stamped field is rejected | TC-ET-007 | **Pass** | Each stamped field in turn: 400 `stamped_field_set`, its pointer naming the field; nothing delivered |

*Done when* 5 (a trace emitted) is soorma-sdk's; soorma-core carries `traceContext` unchanged on
the envelope (TC-ET-002). 2, 3, and 5 through the SDK are soorma-sdk's *Proves*. AI-DLC does not
edit the brief: moving it to `Done` is a human's, once soorma-sdk reports its items.

### Additional Tests

| | |
|---|---|
| Contract tests | Pass |
| Security tests | Pass |
| E2E tests | Pass (27 of 27) |

## Accepted Residuals (stated, not hidden)

**U2 `org-identity`** (NFR Requirements §4): the allowance exhaustion (Q2); the
unknown-identifier flood, which saturates hashing and returns 503 to every caller; the K or K + P
compromise.

**U4 `env-human-access`**: an environment credential stays usable for up to 15 minutes after the
sign-in ends at S1 (ending the credential is its own logout); the Admin self-grant, recorded; the
organization-level outage (issuance, renewal, and `grantToHuman` unavailable; shown by
`stack:outage`); one principal flooding a single S2 instance.

**U5 `agent-registration`** (TC-AR-061):
- No registration bound in M1 (NFR-AR-13)
- A lost volume without a backup loses every registration (NFR-AR-11)
- Within E, a taken identifier is learnable by a holder of `agent:register`
- A registration made by mistake cannot be removed in M1
- Each active secret is a separate way in

**U6 `agent-credentials`**: the lockout (an outsider who knows an agent's identifier can stop its
new instances from bootstrapping while an attack lasts and for at most 60 s after; running
instances renew unaffected); no revocation writer in M1 (PF FR-011 deferred; revocation is seeded
by tests only, never in an image); at S3 a revocation is refused at the next renewal, and the 60 s
bound applies at S4; two of bootstrap's reasons are defensive until deregistration and secret
revocation exist.

**U7 `event-transport`** (business-rules §17): GAP-ET-001's (above); a connection's close after
revocation lags deliveries by up to R (1 s); a stream's authority is fixed at open (bounded by the
credential's lifetime); live only; every subscriber in E receives everything published in E (no
topics); deep pretty-printed bodies can exceed S4's step-1 limits; **PF §9's *Throughput* row is
not demonstrated for S4 in M1** (one S4 per environment, the channel in process). **Cross-instance
superseding** is tested in process only, since the stack runs one S4 per environment; a lost
`supersede` would leave two streams of one lineage for at most the credential's lifetime.

**The user's M1 security decisions**: SECURITY-01 at rest, SECURITY-03's centralized log service,
and SECURITY-14 are not applicable in M1 (a local stack, no hosted deployment).

**Carried to the first hosted deployment**: per-principal and per-source limits on S1 and S2;
per-agent publish and stream limits on S4; the bootstrap lockout's mitigation; replication,
point-in-time recovery, off-host encrypted backups; registration bounds; a multi-instance channel,
which exercises cross-instance superseding and PF §9's *Throughput* row; the clock-skew supersede
risk with several S4 instances; the centralized log service, log integrity and retention, and
alert evaluation.

**Carried to later slices**: the unit that first changes a standing set, a declaration, or autonomy,
or suspends or retires an agent, accounts for U3's term cache and for open streams (NFR-AE-16);
the slice that builds ID FR-026 classifies its replacement rule against ID §3's Admin.

## The Handover to soorma-sdk

Written: `soorma-sdk-handover.md`. It pins `contract-v0.1.0` and collects what an SDK must do:
the bodies `{ draft, payload }` and `{ draft }`; publish `202` with no body; the stream's
`delivery` and `end` events and the open set of end codes; renew, then subscribe again before
`exp`; no resumption; live only; scheduling renewal from `expiresAt`; payload numbers as written and
members in RFC 8785 order; compact JSON. It also carries **the known risk**: S4 delivers payloads
nested about 32,000 levels deep, while Python's `json` fails at about 1,000 and a TypeScript
reviver at about 3,000. soorma-sdk has no initiative or issues yet; the handover is this document,
on soorma-core at the commit that records it.

## Changes Made at This Stage

- **Two report-only harnesses** (they assert no time; `pnpm test`, `test:e2e`, and CI skip them):
  `e2e/perf/stack-latency.test.ts` (`pnpm test:perf:stack`: TC-EHA-070 on the stack, TC-AR-064,
  TC-AC-067, TC-ET-036) and `packages/registry/test/perf/admit-store.test.ts`
  (`pnpm test:perf:agent-facts`: TC-AR-065); two scripts in the root `package.json`
- **No earlier unit's test changed.** No assertion, helper, or harness file was edited
- The 14 matrices: every applicable row `Implemented` → `Verified`, and U7's I4 `Covered` →
  `Verified`, with a note citing this stage's evidence
- **Found, not changed**: `vitest bench` runs the global setups twice, and the second run
  re-passwords the cluster-wide test roles, so a bench over the test database cannot connect. No
  existing bench uses the database; TC-AR-065 is a timed `vitest run` test instead

## GitHub Issues #3 to #10

#4 (U1) and #5 (U2) are already closed. **Each of the others can close**, and none is closed by
this stage: closing is the user's.

| Issue | Can close? | Why |
|---|---|---|
| #6 U3 `authority-evaluation` | **Yes** | Code merged (#17). Every acceptance criterion proven: a stamped field refused, never overwritten (TC-ET-007, U3's tests); a non-declaring agent denied (TC-ET-009); the re-broadening table; one evaluator (I5). L1 38 and I1 to I10 `Verified`. Its gaps (GAP-INT-007, GAP-AE-001) stay open on soorma-prd, worked around, as #4's did when it closed |
| #7 U4 `env-human-access` | **Yes** | Code merged (#19). Every item carried to Build and Test is done: p95 on the stack with the real S1 and TLS (TC-EHA-070); §11's outage cases (40 checks); the rotation tests (TC-EHA-062, 063); the Compose-model, privilege, and docs tests; the residuals and SECURITY decisions above. L1 33 and I1 to I10 `Verified` |
| #8 U5 `agent-registration` | **Yes** | Code merged (#21). TC-AR-061 (the residuals, above), TC-AR-064 and TC-AR-065 (measured) done; *done when* 1 passes by raw calls. L1 32 and I1 to I10 `Verified` |
| #9 U6 `agent-credentials` | **Yes** | Code merged (#23). TC-AC-066 and 067 measured; the residuals and SECURITY decisions above; *done when* 2 passes by raw calls. L1 34 and I1 to I10 `Verified` |
| #10 U7 `event-transport` | **Yes** | Code merged (#25); `contract-v0.1.0` tagged. TC-ET-036 measured; §17's residuals above; the handover written; *done when* 3, 4, 6, 7 pass by raw calls. L1 36 and I1 to I10 `Verified` |
| #3 epic | **Yes, once #6 to #10 close** | Its five acceptance criteria are proven: the first Admin's journey to two registered agents (TC-AR-008); bootstrap and renewal by plain HTTP (TC-AC-093); the event delivered with stamped scope, origin, and chain (TC-ET-001 to 004); both refusals (TC-ET-006, 007); the contract at a pinnable tag (`contract-v0.1.0`) |

**Recommended timing**: close them after this stage's PR (`dev` → `main`) merges, so the evidence
each closing comment cites is on `main`. The brief's own `Done` waits on soorma-sdk's *Proves*.

## Overall Status

| | |
|---|---|
| Build | **Success** |
| All tests | **Pass**, with one failed outage run in the record (run 1: this session's own setup, cause established, reproduced; see the outage row) |
| L1 and invariant conformance | **Pass** (237 and 70 rows `Verified`) |
| Open obligations | 0 deferred questions; specification gaps: **6 `Open`, 1 `Awaiting PRD`**, each worked around and recorded |
| Ready for Operations | **Yes**. Operations is a placeholder in this workflow; the first hosted deployment carries the items listed above |
