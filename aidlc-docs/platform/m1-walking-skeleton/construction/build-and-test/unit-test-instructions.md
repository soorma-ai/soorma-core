# Unit Test Execution

The unit and in-process integration tests of all seven units run in one Vitest suite. The
database tests run against a throwaway PostgreSQL 18 container.

## Run

```bash
pnpm db:test     # starts soorma-db-test; prints TEST_DATABASE_URL and TEST_DATABASE_CONTAINER
TEST_DATABASE_URL=… TEST_DATABASE_CONTAINER=soorma-db-test pnpm test
pnpm db:test:stop
```

Without `TEST_DATABASE_URL` the database tests refuse to run (they do not skip silently). `pnpm db:test`
refuses if `soorma-db-test` is already running: stop it first, so a run starts from fresh roles and
a fresh template.

## Result (2026-11-13)

| | |
|---|---|
| Test files | 130 passed, 7 skipped (137) |
| Tests | **1707 passed, 0 failed**, 30 skipped |
| Duration | 51 s |

The 30 skipped tests are exactly the suites that need a running stack or a perf flag, each run
separately at this stage:

| Skipped in `pnpm test` | Tests | Run by |
|---|---|---|
| `e2e/agent-registration.test.ts` | 9 | `pnpm test:e2e` (integration-test-instructions.md) |
| `e2e/agent-credentials.test.ts` | 5 | `pnpm test:e2e` |
| `e2e/event-transport.test.ts` | 13 | `pnpm test:e2e` |
| `services/org-gateway/test/perf/latency.test.ts` (TC-OI-059) | 1 | `pnpm test:perf` (performance-test-instructions.md) |
| `services/org-gateway/test/perf/timing.test.ts` (TC-OI-062) | 1 | `pnpm test:perf` |
| `services/control-gateway/test/perf/latency.test.ts` (TC-EHA-070, in process) | 1 | `pnpm test:perf:s2` |

This stage adds two more report-only files, skipped the same way: `e2e/perf/stack-latency.test.ts`
(`pnpm test:perf:stack`) and `packages/registry/test/perf/admit-store.test.ts`
(`pnpm test:perf:agent-facts`).

Per-unit counts are in each unit's `code/code-summary.md`. The test case ids each test names are
traced to the L1 and invariant matrices in `l1-conformance-test-instructions.md` and
`invariant-conformance-test-instructions.md`.

## If a test fails

1. Read the failing test's output; the test names carry their TC id.
2. Fix the code, not the assertion. **A change to what an earlier unit's test asserts needs the
   user's approval** (the standing rules: class 1, an item the design adds; class 2, strictly
   stronger; anything else stops for the user).
3. Re-run the whole suite with a fresh `pnpm db:test`.
