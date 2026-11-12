# Code Summary: U5 `agent-registration`

**Unit**: U5 `agent-registration` (soorma-core#8). Control face, environment level
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Design**: Functional Design, NFR Requirements, NFR Design, and QA enrichment, merged in
soorma-core#20 (`1903711`). Infrastructure Design skipped (NFR Requirements)
**Plan**: `construction/working/agent-registration-code-generation-plan.md` (git-ignored),
approved 2026-11-12T01:02:26Z; decisions D-CG-AR-01 to 24

## Groups

| Group | Commit | Content |
|---|---|---|
| Step 0 | `cbed37e` | The plan's approval |
| 1 | `143f073` | The `evaluateHuman` refactor alone: `evaluateHeld` extracted; U4's tests unchanged |
| 2 | `0a90d67` | P3's `readHumanAuthority`, `checkRegistrationRequest`; P4's secret module and lock key |
| 3 | `5b9ccc2` | Migration `0002`; P4's registrations, secrets, cap, and agent-facts source |
| 4 | `3e9e98f` | The contract (two operations, six codes); the Problem table |
| 5 | `167011c` | S2's two routes, events, panels; the S2 tests (reviewed and accepted by the user) |
| 6 | `b2cc93a`, `a217d34` | Backup and restore; the archive check as a full read (D-CG-AR-20); CI's `TEST_DATABASE_CONTAINER` on the Test step (D-CG-AR-23) |
| 7 | `5819f6b`, `c4bda89` | `e2e/`: *done when* 1 and the backup round trip by raw calls on the stack; CI builds the workspace before the e2e step (D-CG-AR-24) |
| 8 | (this commit) | READMEs, the docs test, TC-AR-046 and 067, this summary, the matrices |

Every group passed the full local gate (every check, every test with `pnpm db:test`, `pnpm
audit`), the image builds and scans for the deployables it touched, and the local stack (init,
up, smoke, `down -v`), and its push run was green before the next group began. Group 6's first
push run failed on the workflow file (D-CG-AR-23), and Group 7's at the e2e step in an unbuilt
checkout (D-CG-AR-24); each was fixed on `dev`, and its run green, before the next group.

## Files

### Created

| Path | What it is |
|---|---|
| `packages/authority/src/registration.ts` | `checkRegistrationRequest`: the human-only class and the declaration within the standing set |
| `packages/registry/src/registration-secret.ts` | The secret's format, digest, parser, constant-time match, and the cap's lock key |
| `packages/registry/src/registrations.ts` | Registrations, secrets under the cap, the agent-facts source |
| `packages/env-store/migrations/0002_registrations.sql` | `registrations`, `registration_secrets`, constraints, privileges |
| `deploy/local/scripts/backup-archive.ts` | The backup file's modes, the archive check (`PGDMP`, then a full read) |
| `deploy/local/scripts/stack-backup.ts`, `stack-restore.ts` | `pnpm stack:backup`, `pnpm stack:restore` |
| `e2e/` (`package.json`, `tsconfig.json`, `support.ts`, `agent-registration.test.ts`) | The raw-call proofs on the stack |
| Tests | `packages/authority/test/held.test.ts`, `registration.test.ts`; `packages/registry/test/registration-secret.test.ts`, `registrations.test.ts`; `packages/env-store/test/restore.test.ts`; `contract/test/control-gateway-registration.test.ts`; `services/control-gateway/test/registration.test.ts`, `registration-structure.test.ts`, `registration-support.ts`; `deploy/test/backup.test.ts` |
| Contract fixtures | `contract/fixtures/0.1.0/control-gateway/{RegistrationRequest,RegistrationSecretRequest,Registration,RegistrationSecret}/` |

### Modified

| Path | Change |
|---|---|
| `packages/authority/src/human.ts`, `index.ts` | `evaluateHeld`; `evaluateHuman` over it (unchanged signature and results); `readHumanAuthority` |
| `packages/registry/src/sql.ts`, `index.ts` | U5's statements and exports |
| `packages/service-kit/src/http/problems.ts` | Six codes in the Problem table |
| `contract/control-gateway.openapi.yaml`, `conventions/components.openapi.yaml`, `conventions/errors.md`, `CHANGELOG.md`, `scripts/checks/sides.ts`, `generated/*` | Two operations; six codes; check order, disclosure; regenerated types |
| `services/control-gateway/src/edge/edge-handlers.ts`, `edge.module.ts`, `contract-validator.ts`, `security-log.ts` | The two routes; four events |
| `services/control-gateway/README.md` | The two operations; backup and restore |
| `deploy/local/compose.yaml`, `secrets-init/env.sh` | The four backup and restore services; `copy backup 999` |
| `deploy/local/scripts/db-test.ts` | Prints `TEST_DATABASE_CONTAINER` |
| `deploy/monitoring/alerts.yaml`, `dashboard.yaml` | U5's events, three rules, two panels |
| `.github/workflows/ci.yml` | `TEST_DATABASE_CONTAINER` on the Test step; the e2e restart and run |
| `.gitignore`, `.dockerignore`, `package.json`, `pnpm-workspace.yaml` | `deploy/local/.backups/`; `stack:backup`, `stack:restore`, `test:e2e`; the `e2e` workspace |

## Where the Rules Are

| Rule | Where |
|---|---|
| One read, one evaluator (D-AR-07) | `packages/authority/src/human.ts`: `evaluateHeld`, `evaluateHuman`, `readHumanAuthority` |
| The sponsor ceiling (BR-SP-03) | `edge-handlers.ts` `registerAgent`: `auth.allows(standing)`, else `exceeds_sponsor_ceiling` with `auth.exceeding`; the snapshot is `auth.snapshot()` from the same read; in the store, `registrations_standing_within_snapshot` |
| Sponsor or Admin (D-AR-01) | `edge-handlers.ts` `issueRegistrationSecret`: `agent:register`, the registration, then `registration.sponsor === issuer \|\| auth.allows(['grant:human', 'human:manage'])` |
| The cap under its lock (NP-AR-03) | `packages/registry/src/registrations.ts` `insertSecretUnderCap`: `pg_advisory_xact_lock`, count, insert, in the operation's transaction |
| The once-only secret (D-AR-16) | `registration-secret.ts` `generateRegistrationSecret` (only the digest stored); the value only in the response body, with `Cache-Control: no-store` |
| The agent facts (D-AR-19) | `registrations.ts` `agentFactsFromStore`: one statement, no snapshot or sponsor |

## Changes to Earlier Units' Tests

Each is recorded as a D-CG-AR decision. None is class 3; `packages/authority/test/human.test.ts`
(U4) is unchanged across U5 (Group 1's gate).

**D-CG-AR-13, class 1** (`packages/env-store/test/store.test.ts`, TC-EHA-068):
```diff
-        expect([...x, ...y].sort()).toEqual(['0001_init']);
+        expect([...x, ...y].sort()).toEqual(['0001_init', '0002_registrations']);
```

**D-CG-AR-14, no assertion** (`tools/test/code-checks.test.ts`): the `node:fs` import list gains
`readdirSync` and `readFileSync`; three new `describe`s follow (TC-AR-028, 047, 071).
```diff
-import { createReadStream, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
+import {
+  createReadStream,
+  mkdirSync,
+  mkdtempSync,
+  readdirSync,
+  readFileSync,
+  rmSync,
+  writeFileSync,
+} from 'node:fs';
```

**D-CG-AR-15, class 1** (`contract/test/control-gateway.test.ts`, TC-EHA-024):
```diff
-  it('defines exactly the four operations, each a POST with its operationId', () => {
+  it('defines exactly the four operations, and the two of U5, each a POST with its operationId', () => {
@@
-      Object.entries(operations)
-        .map(([id, { path }]) => `${id} ${path}`)
-        .sort(),
+      [
+        ...Object.entries(operations).map(([id, { path }]) => `${id} ${path}`),
+        // U5's two (D-CG-AR-15), checked in control-gateway-registration.test.ts
+        'issueRegistrationSecret /registration-secrets',
+        'registerAgent /registrations',
+      ].sort(),
```

**D-CG-AR-16, class 1** (`services/control-gateway/test/isolation.test.ts`, TC-EHA-022):
```diff
-  it("S2's operations are exactly its contract's four: none issues a sign-in", () => {
+  it("S2's operations are exactly its contract's four, and U5's two: none issues a sign-in", () => {
@@
-    expect(paths.sort()).toEqual([...OPERATIONS].sort());
+    expect(paths.sort()).toEqual(
+      // U5's two (D-CG-AR-16): registerAgent and issueRegistrationSecret
+      [...OPERATIONS, '/registration-secrets', '/registrations'].sort(),
+    );
```

**D-CG-AR-17, class 1 and class 2** (`services/control-gateway/test/logs.test.ts`; class 2
confirmed by the user, 2026-11-12):
```diff
+import { registrationFlows } from './registration-support.ts';
@@ TC-EHA-053, 054 beforeAll (class 2: every check scans more lines, secrets, and events)
     secrets = await everyFlow(g, timers);
+    // U5's flows too (D-CG-AR-17): every line and event below now also covers them.
+    secrets.push(...(await registrationFlows(g)));
@@ NFR-EHA-19 (class 1)
-describe("NFR-EHA-19: S2's source emits exactly its ten events", () => {
-  it('each listed event is named in the source, and the list is the ten', () => {
+describe("NFR-EHA-19: S2's source emits exactly its ten events, and U5's four", () => {
+  it('each listed event is named in the source, and the list is the ten and the four', () => {
     expect([...SECURITY_EVENTS].sort()).toEqual(
       [
+        // U5's four (D-CG-AR-17; NFR-AR-18)
+        'registration.created',
+        'registration.refused',
+        'secret.issued',
+        'secret.refused',
         'credential.ended',
```

**D-CG-AR-18, class 1** (`services/control-gateway/test/closure.test.ts`, TC-EHA-044):
```diff
-  it('S2 imports evaluateHuman and holdsAnyGrant from P3, and nothing else that computes authority', () => {
+  it('S2 imports evaluateHuman and holdsAnyGrant from P3, and U5 adds two, and nothing else that computes authority', () => {
@@
-    expect(fromAuthority.sort()).toEqual(['evaluateHuman', 'holdsAnyGrant']);
+    expect(fromAuthority.sort()).toEqual(
+      // U5's two (D-CG-AR-18; D-AR-07, 10)
+      ['checkRegistrationRequest', 'evaluateHuman', 'holdsAnyGrant', 'readHumanAuthority'].sort(),
+    );
```

**D-CG-AR-19, class 1** (`deploy/test/compose-model.test.ts`, TC-EHA-079):
```diff
-      expect(Object.keys(copies).sort()).toEqual(['control-gateway', 'db', 'migrate']);
+      // U5's backup/ (D-CG-AR-19): the migrator password and the CA, for the backup services.
+      expect(Object.keys(copies).sort()).toEqual(['backup', 'control-gateway', 'db', 'migrate']);
```

**D-CG-AR-21, class 2** (the user's addition at Q-CG-AR-1): U4's per-service Compose-model
rules, applied by U5's new `deploy/test/backup.test.ts` to the four backup and restore services
(rendered with `--profile backup`, which U4's test does not use). U4's file is unchanged by this;
the added rules:
```diff
+  it("U4's rule: they list no secret", () => {
+    for (const name of BACKUP) expect(withProfile[name]?.secrets ?? [], name).toEqual([]);
+  });
+  it("U4's rule: only their own level's volume, at their own subpath, read-only", () => {
+    ... exactly one secrets mount: `${level(name)}-secrets`, /run/secrets, read_only, subpath backup
+  });
+  it("U4's rule: no secret-looking value, and no secret-named variable but a _FILE path", () => {
+    ... textFindings over each variable; a secret-named key must end in _FILE
+  });
+  it("U4's rule: networks within their own environment, and nothing published", () => {
+    ... networks exactly [level(name)]; ports []
+  });
```

**Group 8, additions only** (`deploy/test/docs.test.ts`, `deploy/test/monitoring.test.ts`): a new
`describe` each (TC-AR-055; TC-AR-067), and in `docs.test.ts` one header-comment line gains
"and U5's backup and restore section (TC-AR-055)". No existing assertion changed.

## Dependencies

**None added** (TC-AR-068). `git diff 923bc16..HEAD -- DEPENDENCIES.md pnpm-lock.yaml` is empty;
`check:deps` and `pnpm audit` pass at every group. The `e2e` workspace declares no dependency.

## Test Cases

Every TC-AR id from 001 to 072 is named by a test, a stack proof, or (for three) left to Build and
Test:

| Where | Test cases |
|---|---|
| `services/control-gateway/test/registration.test.ts` (in process, db-test, raw requests) | 001 to 007, 009 to 023, 025, 026, 029, 030, 033 to 037, 040 to 043, 051, 054, 062, 063, 066, 069 |
| `packages/registry/test/registrations.test.ts` (the store) | 001, 019, 023, 024, 025, 027, 032, 039, 051, 052, 053, 070, 072 |
| `packages/registry/test/registration-secret.test.ts` | 048, 049, 050, 053 |
| `packages/authority/test/held.test.ts`, `registration.test.ts` | 002, 010 to 012, 029, 030, 038 |
| `contract/test/control-gateway-registration.test.ts` | 022, 045 |
| `services/control-gateway/test/registration-structure.test.ts` | 031, 046 |
| `tools/test/code-checks.test.ts` | 028, 047, 071 |
| `packages/env-store/test/restore.test.ts` (db-test round trip) | 058, 060 |
| `deploy/test/backup.test.ts` | 056, 057, 060 |
| `deploy/test/docs.test.ts`, `monitoring.test.ts` | 055, 067 |
| `e2e/agent-registration.test.ts` (the stack, raw calls) | 008, 043, 044, 056, 059, 060 |
| The gate | 068 (`check:deps`, `pnpm audit`, the register unchanged) |
| **Build and Test (D-CG-AR-06)** | **061** (the residuals in the summary), **064** (p95 of both operations on the running stack, reported), **065** (`pnpm bench:admit` with P4's agent-facts source, reported) |

## Local Run (Group 8)

Every check; every test with `pnpm db:test` (`TEST_DATABASE_URL`, `TEST_DATABASE_CONTAINER`);
`pnpm audit`; S1's and S2's images built and scanned; the local stack (init, up, smoke, `down
-v`); `pnpm test:e2e` on a fresh stack. Figures are in the Group 8 commit message.

## Security Compliance (SECURITY-01 to 15)

| Rule | Status |
|---|---|
| SECURITY-01 | In transit: TLS 1.3 on S2's edge, `verify-full` to the store (S2 and the backup services). **At rest: not applicable in M1, the user's decision**; digests only; the dump 0600, git- and docker-ignored |
| SECURITY-02, 04, 07 | N/A: no new intermediary, HTML, or network |
| SECURITY-03 | Compliant, except the centralized log service (the user's M1 decision): no value, digest, token, or principal identifier logged (TC-AR-036, 066) |
| SECURITY-05 | Compliant: closed schemas, bounds, the 16 KiB body bound, parameterized SQL |
| SECURITY-06 | Compliant: the app role `SELECT`, `INSERT` only on both tables; the backup services hold only the migrator password and the CA |
| SECURITY-08 | Compliant: every operation needs E's credential; function- and object-level checks |
| SECURITY-09 | Compliant: no default credentials; generic Problems |
| SECURITY-10 | Compliant: no new dependency; the pinned image |
| SECURITY-11 | Compliant: the throttle; the cap; misuse cases tested |
| SECURITY-12 | Compliant: no password in any variable or argument; the secret's verifier |
| SECURITY-13 | Compliant: write-once rows, each attributed; checksummed migrations |
| SECURITY-14 | Not applicable in M1 (the user's decision): rules as files |
| SECURITY-15 | Compliant: fail closed; one transaction per operation; the lock released at rollback |

## Invariant Compliance (I1 to I11)

I1 to I10 **Implemented** (invariant-coverage-matrix); I11 N/A. The I8 packaging table re-checked
(TC-AR-046): every capability core-assigned; no read surface, sponsorship policy, quota, rotation,
or retirement in any form; the cap a platform constant.

## L1 Coverage

All 32 applicable rows **Implemented** (l1-coverage-matrix). L1-17 and L1-31 rest on the
GAP-INT-006 work-around (Open, soorma-prd#24). Build and Test moves rows to `Verified`.

## For Build and Test

- TC-AR-061, 064, 065 (D-CG-AR-06)
- The residuals: no registration bound in M1 (NFR-AR-13); a lost volume without a backup loses
  every registration (NFR-AR-11); within E, a taken identifier is learnable by a holder of
  `agent:register`; a registration made by mistake cannot be removed in M1; each active secret is
  a separate way in
- The user's M1 decisions on SECURITY-01 at rest, SECURITY-03's log service, SECURITY-14
