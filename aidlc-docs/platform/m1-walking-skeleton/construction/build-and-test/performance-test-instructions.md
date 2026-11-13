# Performance Test Instructions

Every latency figure in M1 is **reported, not gated** (each unit's NFR Requirements), except
TC-OI-059, whose test asserts its targets. Timing gates flake on shared runners (U2's TC-OI-062),
so CI runs none of these; they run here, on the reference workstation (Intel Core i9-9980HK,
macOS 14.7, Docker 29.5.3), and the figures go in the summary.

## What is measured, and where

| Case | Measures | Where | Command |
|---|---|---|---|
| TC-OI-059 | S1: `authenticate`, `renewSignIn`, `endSignIn` | the running stack | `pnpm test:perf` |
| TC-OI-062 | S1: refusal timing, known vs unknown principal | in process, real Argon2id, test clock | `pnpm test:perf` |
| TC-EHA-070 | S2: issuance, renewal, ending, `grantToHuman` | **the running stack**, real S1 and TLS | `pnpm test:perf:stack` |
| TC-AR-064 | S2: `registerAgent`, `issueRegistrationSecret` | the running stack | `pnpm test:perf:stack` |
| TC-AC-067 | S3: `exchangeBootstrap`, `renewAgentCredential` | the running stack | `pnpm test:perf:stack` |
| TC-ET-036 | S4: opening a stream, publish, publish to delivery | the running stack | `pnpm test:perf:stack` |
| TC-AE-040 | U3: `admit`, steps 5 to 10, maximum-size forwarding draft, warm cache | in process | `pnpm bench:admit` |
| TC-AR-065 | U3's `admit` with P4's agent-facts source over a store, warm and cold; the statement alone | in process, test store | `pnpm test:perf:agent-facts` |
| TC-AC-066 | U6: the revocation cache's hit | in process | `pnpm bench:revocation` |

**Added at this stage** (report-only; they assert no time; `pnpm test` and CI skip them):
`e2e/perf/stack-latency.test.ts` (`test:perf:stack`), because U4's TC-EHA-070 harness ran in
process with a stub S1 and no TLS, and nothing measured S2's U5 operations, S3, or S4 on the stack;
and `packages/registry/test/perf/admit-store.test.ts` (`test:perf:agent-facts`), because
`bench:admit` uses U3's in-memory facts source. TC-AR-065 is a timed loop under `vitest run`, not
`vitest bench`: bench mode runs the global setups twice, and the second run re-passwords the
cluster-wide test roles after the first run's passwords were handed to the workers, so the store
refuses the connection.

## Run

```bash
# 1. The stack measurements, on a fresh stack. H's first authentication happens in the harness
#    if the file does not exist; K is written to it, mode 0600, and never printed.
docker compose -f deploy/local/compose.yaml down -v && pnpm stack:up
SOORMA_PERF_SECRET_FILE=<a path outside the repository> pnpm test:perf:stack

# 2. S1, with the same K file (TC-OI-059), and TC-OI-062 over the test database
pnpm db:test
SOORMA_PERF_PRINCIPAL=h@example.com SOORMA_PERF_SECRET_FILE=<the same path> \
  TEST_DATABASE_URL=… pnpm test:perf

# 3. In process
pnpm bench:admit
pnpm bench:revocation
TEST_DATABASE_URL=… pnpm test:perf:agent-facts

# 4. Delete the K file, and stop the stack
rm <the path>; docker compose -f deploy/local/compose.yaml down -v
```

Each call in the stack harness opens a new TLS 1.3 connection, as a raw client without connection
reuse does, so every figure includes the handshake. Requests are sequential: these are latencies,
not throughput.

## Results (2026-11-13)

### On the running stack

| Case | Operation | Samples | p50 ms | **p95 ms** | max ms | Target (p95) |
|---|---|---|---|---|---|---|
| TC-OI-059 | `authenticate` (Argon2id, 64 MiB) | 100 | | **334** | | 500 (gated: pass) |
| TC-OI-059 | `renewSignIn` | 100 | | **20** | | 200 (gated: pass) |
| TC-OI-059 | `endSignIn` | 100 | | **17** | | 200 (gated: pass) |
| TC-EHA-070 | issuance | 500 | 13.1 | **19.6** | 28.8 | 300 |
| TC-EHA-070 | renewal | 500 | 13.1 | **19.7** | 46.6 | 300 |
| TC-EHA-070 | ending | 500 | 9.9 | **15.8** | 22.6 | 200 |
| TC-EHA-070 | `grantToHuman` | 500 | 13.3 | **19.3** | 48.8 | 200 |
| TC-AR-064 | `registerAgent` | 200 | 11.0 | **16.4** | 46.7 | none (reported) |
| TC-AR-064 | `issueRegistrationSecret` | 200 | 12.2 | **20.8** | 39.2 | none (reported) |
| TC-AC-067 | `exchangeBootstrap` | 200 | 14.6 | **23.9** | 60.5 | 200 |
| TC-AC-067 | `renewAgentCredential` | 200 | 12.6 | **19.8** | 35.2 | 200 |
| TC-ET-036 | opening a stream (to the response head) | 200 | 9.2 | **18.4** | 42.7 | 200 |
| TC-ET-036 | publish (to the 202) | 200 | 10.0 | **16.3** | 21.0 | 200 |
| TC-ET-036 | publish to delivery (request start to the Delivery read) | 200 | 10.2 | **16.6** | 21.2 | 250 |

Every figure is within its target: `authenticate` at 334 of 500 ms, and every other operation by
a factor of eight or more. `grantToHuman` re-grants H
(M1 has one principal), which BR-GR-06 allows and records, so each sample is the full path with
its write. U2's code summary recorded Argon2id at about 710 ms late in its session on this machine,
which put NFR-OI-19 at risk; in this run `authenticate` is 334 ms at p95.

### TC-OI-062: refusal timing (reported, never a gate)

| | Known principal (wrong K) | Unknown principal |
|---|---|---|
| Median | 175.8 ms | 175.5 ms |
| p95 | 231.3 ms | 232.2 ms |

200 samples each; medians differ by 0.36 ms; Mann-Whitney z = -0.23, p = 0.82. No timing
difference is detectable, so BR-RF-03 holds as measured.

### In process

| Case | Figure | p50 ms | **p99 ms** | Samples | Target |
|---|---|---|---|---|---|
| TC-AE-040 | `admit`, steps 5 to 10, warm | 0.256 | **0.593** | 7,024 | p99 ≤ 2 ms (NFR-AE-07) |
| TC-AR-065 | `admit` with P4's source, warm | 0.240 | **0.595** | 5,000 | p99 ≤ 2 ms |
| TC-AR-065 | `admit` with P4's source, cold (P4's read on every admit) | 1.239 | **2.598** | 5,000 | NFR-AE-07 excludes term reads; reported |
| TC-AR-065 | P4's agent-facts statement alone, 32 agents | 0.872 | **2.051** | 5,000 | one statement (NFR-AR-16); reported |
| TC-AC-066 | the revocation cache's hit | 0.0006 | **0.0013** | 2,858,221 | p99 ≤ 0.1 ms (NFR-AC-16) |

TC-AR-065: with P4's real source behind U3's cache, the warm path matches TC-AE-040, as it should,
since no read is timed. A cache miss adds P4's one statement for the chain's agents, about 1 ms at
p50 and 2 ms at p99 against the local test database. That cost is paid once per agent per
propagation bound (60 s), not per request. NFR-AE-07's 2 ms target excludes term reads, so the cold
figure is reported against nothing.

## What is not measured in M1

- **PF §9's *Throughput* row, for S4**: not demonstrated in M1. Exactly one S4 runs per
  environment, with the fan-out channel in process (U7 NFR Requirements Q3). Carried to the first
  hosted deployment, with the distributed channel.
- **Load and stress**: M1 is a local stack. The bounds that protect it (S1's abuse bound, S2's
  throttle, S3's bootstrap bound, S4's stream cap and step-1 limits) are each tested functionally
  in the unit suite.
