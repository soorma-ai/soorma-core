# Code Summary: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7, tracking #3). **Built against**: ID @
`prd-identity-v1.0`; PF @ `prd-platform-foundations-v1.3`. **Plan**:
`construction/working/env-human-access-code-generation-plan.md` (git-ignored; Steps 0 to 31,
decisions D-CG-EHA-01 to 31, recorded here).

U4 gives each environment its own control face, **S2 `services/control-gateway`**. S2 turns a
human's organization sign-in from S1 into an **environment credential** for its own environment
only, and records the **grants** that give a human permissions there, each with an attribution
record in the same transaction. It is built on the organization-neutral runtime that U4 moved out
of U2 into `@soorma/service-kit`, and on four new packages: `env-store`, P4 `registry`, P5
`credentials`, and P7 `attribution`. The local stack gains two environments, `e` and `e2`, each
with its own store, migration run, secrets, network, and S2.

| Group | Commit | What | Push run |
|---|---|---|---|
| 1 | `6b679e0` | The pure move into `packages/service-kit` (NP-EHA-15) | 42980867192 |
| — | `d2db9e0` | `roles.sql` serialized (D-CG-EHA-15) | 42982443327 |
| 2 | `1297d8d` | The generalisations (semaphore, security log, contract validator, HTTP plumbing; sign-in leeway, `unknownKey`, the status callback, the key source) | 42985132072 |
| 3 | `cb3deea` | S1: A7 `signInStatus`, and `publicKeys` per internal caller with `kid` uniqueness | 42986611248 |
| 4 | `a50f8fc` | The contract, `env-store`, P4, P5, P7; P3 `evaluateHuman`; P9; P1 for S2 | 42990083535 |
| 5 | `fcc4d3d` | S2 and its image | 42993721083 |
| 6 | `7e00606` | E and E2 on the local stack; the S1-stopped demonstration; monitoring; the Compose-model test; CI | 43061755886 |
| 7 | `4c6bb1d` | READMEs and the operations notes; the docs test | 43063186098 |
| 8 | this commit | The six test cases without a test (D-CG-EHA-31); this summary; the matrices; the §2.1 fix | The PR's checks |

---

## Files

### Created

| Where | What |
|---|---|
| `packages/service-kit/` | The shared runtime: root entry (clock, `Store` and the migration runner, secret types and `secretEqual`, canonical JSON, thumbprints, pseudonyms, the signed internal request, `verifySignIn`, the Problem table, `Semaphore`) and `/http` (`createAdapter`, `ProblemFilter`, `ContractValidator`, health, `SecurityLog`). Nine files arrive by `git mv` (below) |
| `packages/env-store/` | `migrations/0001_init.sql` (credentials, grants, attribution records; CHECKs; the partial unique index; column-level privileges); `connectEnvStore`, `withTransaction`, `migrate`, `ENV_MIGRATION_LOCK_KEY`; its test harness |
| `packages/registry/` (P4) | `ACCEPTED_PERMISSIONS` (the nine), grants, the first grant, the human `GrantSource` |
| `packages/credentials/` (P5) | E's key ring, the `soorma_ec_` token, the credential record (O3; conditional renew and end) |
| `packages/attribution/` (P7) | The attribution record, checked before SQL (BR-AT-05) |
| `packages/authority/src/human.ts` (P3) | `evaluateHuman`, `holdsAnyGrant` |
| `services/control-gateway/` (S2) | `main.ts`, `migrate.ts`, `healthcheck.ts`, `settings.ts`, `runtime.ts`, `apps.ts`, `edge/`, `org-level.ts` (the S1 caller), `verify-keys.ts`, `throttle.ts`, `first-grant.ts`, `security-log.ts`, `contract-validator.ts`; `Dockerfile` (no `@soorma/org-identity`); README |
| `contract/control-gateway.openapi.yaml` | Four operations; `GrantRequest`, `EnvironmentCredentialResponse`, `Grant`; fixtures; generated types |
| `deploy/local/` | `db/env-roles.sql`, `db/env-pg_hba.conf`, `db/init/10-soorma-env-roles.sh`, `secrets-init/env.sh`, `scripts/s1-outage.ts`, `scripts/stack-client.ts` |
| `deploy/test/` | `compose-model.test.ts`, `monitoring.test.ts`, `docs.test.ts` |
| READMEs | `service-kit`, `env-store`, `registry`, `credentials`, `attribution`, `control-gateway` |

**The move (Group 1, `git mv`)**:

| From | To |
|---|---|
| `packages/org-identity/src/clock.ts` | `packages/service-kit/src/clock.ts` |
| `packages/org-identity/src/crypto/canonical.ts` | `packages/service-kit/src/crypto/canonical.ts` |
| `packages/org-identity/src/crypto/internal-request.ts` | `packages/service-kit/src/crypto/internal-request.ts` |
| `packages/org-identity/src/crypto/pseudonym.ts` | `packages/service-kit/src/crypto/pseudonym.ts` |
| `packages/org-identity/src/crypto/secret-types.ts` | `packages/service-kit/src/crypto/secret-types.ts` |
| `packages/org-identity/src/errors.ts` | `packages/service-kit/src/errors.ts` |
| `packages/org-identity/src/store/store.ts` | `packages/service-kit/src/store/store.ts` (D-CG-EHA-01) |
| `packages/perimeter/src/problems.ts` | `packages/service-kit/src/http/problems.ts` |
| `services/org-gateway/src/health.ts` | `packages/service-kit/src/http/health.ts` |

Split rather than moved whole: sign-in verification (`sign-in-token.ts` keeps `mintSignIn`;
`service-kit/src/crypto/sign-in-verify.ts`), keys (`key-ring.ts` keeps `KeyRing`;
`service-kit/src/crypto/keys.ts`), SQL (`service-kit/src/sql.ts` holds the runner's), and the
migration runner (`org-identity/src/store/migrations.ts` stays as a wrapper passing U2's
directory and lock key).

### Modified

- **S1** (`services/org-gateway`): imports from `service-kit`; A7 (`signInStatus` answers
  `{ status: 'live', expiresAt }`, `ended`, or `unknown`); the status callback and key source;
  README `## Operations`.
- **P10, P8, P6, P1, P9** (`org-identity`, `abuse-bound`, `identity-resolution`, `perimeter`,
  `config`): imports; P10's `KeyRing` loads `publicKeys` with the four refusals; P1's
  `SignInPerimeter` takes a key source, an optional refetch, and the A7 status callback; P1
  adds `presentedEnvironmentCredential`; P9 adds `controlGateway`, `loadEnvironmentMigrator`,
  and `listSecrets`'s environments.
- **The contract**: `unknown_permission` and `unknown_principal` (`ProblemCode`, `errors.md`,
  `CHANGELOG.md`: compatible, the code set is open).
- **The stack**: `compose.yaml`, `tenancy.yaml`, `org.sh`, `roles.sql` (serialized),
  `stack-init.ts`, `stack-certs.ts`, `smoke.ts`; `deploy/monitoring/*.yaml`.
- **CI**: builds and scans S2's image; runs the S1-stopped demonstration on a fresh stack.
- `DEPENDENCIES.md` (the U4 workspaces in existing rows), `package.json` (`stack:outage`,
  `test:perf:s2`), the root README.

---

## Decisions as Built

| ID | Decision |
|---|---|
| D-CG-EHA-01 | `Store`, `Queryable`, `ConflictError` moved with the pool; logical-components §2.1 corrected in place |
| D-CG-EHA-02 | P1 keeps re-exporting the Problem documents, so U2's and U3's imports are unchanged |
| D-CG-EHA-03 | `service-kit` has two entry points; the root is framework-free |
| D-CG-EHA-04 | Packaging as U2's and U3's (source condition; `tsconfig.build.json`) |
| D-CG-EHA-05 | Groups 1 and 2 changed U2 tests only at import lines and changed call sites |
| D-CG-EHA-06 | S1's status callback answers from its own record; S1's acceptance stays O3 |
| D-CG-EHA-07 | The environment store's test harness: a migrated template per run, a clone per test file, as the app role |
| D-CG-EHA-08 | The dependency-closure check: `@soorma/org-identity` is not in S2's production closure |
| D-CG-EHA-09 | The request semaphore on Fastify's `onRequest`, released once in `onResponse` or `onRequestAbort` |
| D-CG-EHA-10 | Latency is measured and reported, never a gate. *Corrected at approval (the user's, 2026-11-11)*: the plan said `test:perf:s2` runs against the running stack; it runs in process with a stub S1. The figures are in-process only, and the stack measurement is carried to Build and Test |
| D-CG-EHA-11 | Test titles name their TC ids |
| D-CG-EHA-12 | Commit cadence and the pre-commit gate (the stack run in Groups 1, 2, 3, 5, 6; each push run green) |
| D-CG-EHA-13 | S1's health check keeps working through the move |
| D-CG-EHA-14 | `verifySignIn` and `verifyInternalRequest` take structural key sources (no cycle) |
| D-CG-EHA-15 | `roles.sql` and `env-roles.sql` serialize concurrent runs with transaction advisory locks |
| D-CG-EHA-16 | `unknownKey` is an intended interface change (the user's A) |
| D-CG-EHA-17 | The monitoring test splits (the user's decision) |
| D-CG-EHA-18 | `ProblemFilter` takes `{ retryAfterSeconds?, onUnavailable? }`; S1 passes neither |
| D-CG-EHA-19 | `sign_in_expiring`: a capped expiry at or before now is `credential_refused` |
| D-CG-EHA-20 | S2 and `{env}-migrate` read `SOORMA_PROJECT` and `SOORMA_ENVIRONMENT` |
| D-CG-EHA-21 | No grant in E at issuance logs `credential.refused` (`no_grant_in_environment`) |
| D-CG-EHA-22 | `if (!token)` on a `SecretText` |
| D-CG-EHA-23 | One set of non-secret environment variables (the user's decision); Infrastructure Design §3 and shared-infrastructure.md corrected in place |
| D-CG-EHA-24 | `stack-client.ts`; the S1-stopped demonstration on a fresh stack (`pnpm stack:outage`) |
| D-CG-EHA-25 | `ajv` and `yaml` join `@soorma/deploy` at their pinned versions (not new: stop condition 4) |
| D-CG-EHA-26 | `listSecrets` names each environment's caller key |
| D-CG-EHA-27 | CI's image job renamed; no required status check is affected |
| D-CG-EHA-28 | Two U2 smoke-test assertion changes (the user's A) |
| D-CG-EHA-29 | The user's standing approval for additive U2 assertion changes |
| D-CG-EHA-30 | `pnpm test:perf:s2` passes `--silent=false`, so the report line prints |
| D-CG-EHA-31 | Six specified test cases had no test at Group 7 (TC-EHA-022, 031, 050, 051, 067, 069). Group 8 adds them: `services/control-gateway/test/isolation.test.ts` (022, 031, 050, 051); smoke section 10 (050 and 067 on the stack, through a new `dockerWithInput` helper that passes secrets on stdin; `docker` is unchanged); a new `describe` in `tools/test/code-checks.test.ts` (069; no existing test changed); the TC-EHA-022 label on the Compose-model test |

---

## Changes to U2 Assertions

Every change to an assertion in a U2 test or script, with the design item it implements. Import
lines and call sites whose signature changed (D-CG-EHA-05) are not listed.

**D-CG-EHA-16** (the user's A; NFR Design commit 2, *`verifySignIn`: unknown `kid`*):
`packages/org-identity/test/crypto.test.ts` (TC-OI-044).

```diff
-    ['an unknown kid', { kid: 'unknown' }, {}],
     ['no sid', {}, { sid: undefined }],
@@
+  it('answers unknownKey for a token with an unknown kid (U4 D-CG-EHA-16)', async () => {
+    const token = await forged({ kid: 'unknown' }, {});
+    expect((await verifySignIn(token, keys, 'o1', now)).status).toBe('unknownKey');
+  });
@@
     const removed = KeyRing.fromConfiguration(material({ signingKey: next.privatePem }));
-    expect((await verifySignIn(token, removed, 'o1', now)).status).toBe('invalid');
+    expect((await verifySignIn(token, removed, 'o1', now)).status).toBe('unknownKey');
```

**Group 3, A7** (approved in the plan; U2 amendment A7, Functional Design §17):
`packages/org-identity/test/domain.test.ts` and `services/org-gateway/test/internal.test.ts`.

```diff
-    expect(await d.identity.signInStatus(s.sid)).toBe('live');
-    expect(await d.identity.signInStatus('no-such-id')).toBe('unknown');
+    expect(await d.identity.signInStatus(s.sid)).toEqual({
+      status: 'live',
+      expiresAt: s.expiresAt,
+    });
+    expect(await d.identity.signInStatus('no-such-id')).toEqual({ status: 'unknown' });
```

```diff
-  it('signInStatus answers live, ended, or unknown, and nothing else', async () => {
+  it('signInStatus answers live with its expiry, ended, or unknown, and nothing else (A7)', async () => {
@@
-    expect((await internalGet(g, `/sign-ins/${sid}/status`)).body).toEqual({ status: 'live' });
+    const live = (await internalGet(g, `/sign-ins/${sid}/status`)).body as {
+      status: string;
+      expiresAt: string;
+    };
+    expect(Object.keys(live).sort()).toEqual(['expiresAt', 'status']);
+    expect(live.status).toBe('live');
+    expect(Math.floor(Date.parse(live.expiresAt) / 1000)).toBe(exp);
```

**D-CG-EHA-17** (the user's decision; Infrastructure Design §9):
`services/org-gateway/test/monitoring.test.ts`. The whole-file checks move to
`deploy/test/monitoring.test.ts` (TC-EHA-087), where `events` must equal the union of S1's and
S2's events. Line 75 (S1's source emits each event) is unchanged.

```diff
-  it('list exactly the events the log helper accepts', () => {
-    expect([...alerts.events].sort()).toEqual([...SECURITY_EVENTS].sort());
-  });
-
-  it('name only listed events, in every rule and panel', () => {
-    for (const rule of alerts.rules) expect(SECURITY_EVENTS).toContain(rule.event);
-    for (const panel of dashboard.panels)
-      for (const event of panel.events) expect(SECURITY_EVENTS).toContain(event);
+  // The whole-file checks (the events list against every service's, and every
+  // rule and panel against that list) are deploy/test/monitoring.test.ts's
+  // (U4 D-CG-EHA-17; TC-EHA-087).
+  it("list every one of S1's events", () => {
+    for (const event of SECURITY_EVENTS) expect(alerts.events).toContain(event);
   });
```

**D-CG-EHA-28** (the user's A): `deploy/local/scripts/smoke.ts`.

(1) Infrastructure Design §3: org-gateway holds each environment's caller **public** key.

```diff
   const expectedGateway = [
+    // Each environment's caller PUBLIC key (U4 Infrastructure Design §3).
+    'e-caller-public-key',
+    'e2-caller-public-key',
     'org-counter-secret',
```

(2) NFR-EHA-18 (no identifier or secret in any log): the leak check reads more logs, and scans
for the new sections' tokens.

```diff
-  const logs = docker([...COMPOSE, 'logs', '--no-color', 'org-gateway', 'org-migrate']);
-  const leaked = [PRINCIPAL.principal, material, K, token].filter(
+  const logs = docker([
+    ...COMPOSE,
+    'logs',
+    '--no-color',
+    'org-gateway',
+    'org-migrate',
+    'e-control-gateway',
+    'e2-control-gateway',
+    'e-migrate',
+    'e2-migrate',
+  ]);
+  const leaked = [PRINCIPAL.principal, material, K, token, ...secrets].filter(
```

The helpers `smoke.ts` used moved to `stack-client.ts` with their behaviour unchanged: `call`
keeps port 8441 by default and only adds `retryAfter` to its reply. After D-CG-EHA-28, no
further U2 assertion changed. D-CG-EHA-31 adds a test to `tools/test/code-checks.test.ts`
without changing an existing one.

---

## Dependencies

**No new dependency** (stop condition 4). Registered dependencies join U4's workspaces at their
pinned versions: `pg` (`env-store`), the NestJS and Fastify set (`control-gateway`), and `ajv`
and `yaml` (`deploy`, test-only; D-CG-EHA-25). `DEPENDENCIES.md` names each workspace;
`pnpm check:deps` passes.

---

## Test Cases

1050 tests pass in CI's configuration (75 files), with 3 gated performance cases. Every TC-EHA
id, 001 to 091, is named by a test or a stack check.

| Test file or script | Test cases (TC-EHA-) |
|---|---|
| `services/control-gateway/test/flows.test.ts` | 001 to 021, 025 to 029, 032 to 034, 038, 039, 041, 042, 049, 052, 055, 071, 074, 077, 091 |
| `services/control-gateway/test/failures.test.ts` | 023, 035, 037, 043, 048, 057, 064, 066 |
| `services/control-gateway/test/isolation.test.ts` | 022, 031, 050, 051 |
| `services/control-gateway/test/throttle.test.ts`, `packages/service-kit/test/semaphore.test.ts` | 058, 059, 060 |
| `services/control-gateway/test/org-level.test.ts` | 023, 043, 060 |
| `services/control-gateway/test/verify-keys.test.ts` | 061, 062, 063 |
| `services/control-gateway/test/logs.test.ts` | 053, 054 |
| `services/control-gateway/test/closure.test.ts` | 044, 078 |
| `packages/credentials/test/token.test.ts`, `records.test.ts` | 002, 010, 014, 030, 036, 045, 056, 072, 073, 075 |
| `packages/registry/test/registry.test.ts` | 005, 006, 013, 027, 035, 038, 040, 076 |
| `packages/attribution/test/record.test.ts` | 046, 047 |
| `packages/env-store/test/store.test.ts` (and its harness) | 035, 047, 068, 080 |
| `packages/authority/test/human.test.ts` | 008, 011, 012 |
| `packages/perimeter/test/environment-presenter.test.ts`, `environment-sign-in.test.ts`; `packages/service-kit/test/sign-in-verify.test.ts` | 009, 015, 016, 032 to 034, 057, 064, 065 |
| `packages/config/test/control-gateway.test.ts`, `internal-callers.test.ts`; `packages/org-identity/test/internal-callers.test.ts` | 036, 082, 083 |
| `packages/org-identity/test/sign-in-status.test.ts` | 090 |
| `contract/test/control-gateway.test.ts` | 024 |
| `deploy/test/compose-model.test.ts` | 022, 079, 089 |
| `deploy/test/monitoring.test.ts`, `services/org-gateway/test/monitoring.test.ts` | 087 |
| `deploy/test/docs.test.ts` | 081 |
| `tools/test/code-checks.test.ts` | 069 |
| `pnpm stack:smoke` (CI's stack job) | 050, 067, 086 |
| `pnpm stack:outage` (CI's stack job, on a fresh stack) | 084, 085 |
| CI's S2 image secret scan | 088 |
| `services/control-gateway/test/perf/` (`pnpm test:perf:s2`, reported only) | 070 |

---

## Local Run (Step 28, 2026-11-11)

Node 26.13.0, pnpm 12.18.0, Docker Desktop; Intel Core i9-9980HK.

| Command | Result |
|---|---|
| `pnpm install --frozen-lockfile`; `build`; `lint`; `format:check` | Pass |
| `check:deps`, `check:code`, `check:generated`, `check:contract`, `check:secrets`, `check:workflows` | Pass |
| `pnpm audit --audit-level moderate` | No finding |
| `pnpm test` with `TEST_DATABASE_URL` (`pnpm db:test`) | 1050 passed, 3 skipped (the gated performance cases) |
| S1 and S2 images: build, and `check:secrets --image` | Pass, both |
| `stack:init`, `stack:up`, `stack:smoke`, `down -v` | 52 checks pass |
| `stack:up` (fresh), `stack:outage`, `down -v` | Both cases pass; case 2 recovers within the 30-second on-demand limit (22 s) |

**Latency, in process only** (TC-EHA-070; reported, not a gate). `SOORMA_PERF=1 pnpm
test:perf:s2` drives S2's real edge **in process** (Fastify `inject`, no socket, no TLS) over a
test environment store, with a **stub S1** in the same process; 500 runs per operation after 20
warm-up issuances; three runs.

| Operation | p95, run 1 | Run 2 | Run 3 | Target (on the stack) |
|---|---|---|---|---|
| Issuance | 4.9 ms | 5.1 ms | 5.0 ms | 300 ms |
| Renewal | 5.2 ms | 4.8 ms | 5.1 ms | 300 ms |
| Ending | 4.7 ms | 4.9 ms | 4.8 ms | 200 ms |
| `grantToHuman` | 5.8 ms | 5.8 ms | 5.8 ms | 200 ms |

*Correction at approval (the user's, 2026-11-11)*: NFR-EHA-15 and D-CG-EHA-10 call for the
figures **on the local stack**. These are not that measurement: they leave out the client's TLS
1.3 connection to S2, S2's signed calls over TLS to the real S1 (`signInStatus`,
`principalExists`), and the store over TLS. They show S2's own processing only, and do not
discharge NFR-EHA-15. **Build and Test measures p95 on the running stack**, with the real S1 and
TLS, against 300 ms (issuance, renewal) and 200 ms (ending, `grantToHuman`).

### For Build and Test

- **p95 latency on the running stack** (NFR-EHA-15; TC-EHA-070), with the real S1 and TLS,
  against 300 ms (issuance, renewal) and 200 ms (ending, `grantToHuman`); reported, not a gate.
  The Code Generation figures are in process only (above).
- §11's two cases on the stack (scripted: `pnpm stack:outage`); the rotation test (NFR-EHA-08a)
  as an integration run; the Compose-model, privilege, and docs tests.
- The accepted residuals: the post-logout credential, at most 15 minutes (NFR-EHA-02); the
  Admin self-grant (recorded); the organization-level outage (D-EHA-23); the instance flood
  (Q2).
- The user's SECURITY decisions: SECURITY-14 (rules as files, nothing evaluates them),
  SECURITY-03's centralized log service, SECURITY-01 at rest.

---

## Security Compliance (SECURITY-01 to 15)

| Rule | Status | As built |
|---|---|---|
| SECURITY-01 | **In transit: compliant. At rest: not applicable in M1, by the user's decision** | TLS 1.3 on S2's edge and to S1 (local CA only, server name checked); the store over TLS, `verify-full` |
| SECURITY-02 | N/A in M1 | No load balancer or gateway in the local stack |
| SECURITY-03 | **Compliant, except the centralized log service: not applicable in M1, by the user's decision** | JSON logs, ten fixed events, `hp_` pseudonyms under E's own key; TC-EHA-053 and the smoke test find no identifier or secret |
| SECURITY-04 | N/A | No HTML |
| SECURITY-05 | Compliant | Every request body validated against the contract, refused `malformed_request` with pointers; a 16 KiB body limit; S1's answers checked to their exact shapes, at most 64 KiB |
| SECURITY-06 | Compliant | The app role's column-level `UPDATE`, no `DELETE`; S2 holds no migrator password; each service mounts only its own secrets |
| SECURITY-07 | Compliant | Loopback-only edges; stores unpublished; no network spans environments (TC-EHA-089; smoke section 10) |
| SECURITY-08 | Compliant | Every operation authenticated by an environment credential or (issuance) a sign-in; authority by `evaluateHuman` |
| SECURITY-09 | Compliant | Distroless, non-root, read-only, all capabilities dropped; images pinned by digest |
| SECURITY-10 | Compliant | No new dependency; exact versions; frozen lockfile |
| SECURITY-11 | Compliant, with the user's accepted residual | 64 requests and 8 S1 calls in flight, then 503 with `Retry-After: 5`; per-principal and per-source limits carried to the first hosted deployment |
| SECURITY-12 | Compliant | 15-minute credentials capped at the sign-in; no leeway on `exp`; ending is its own logout; secrets as mounted files only; rotation documented for each key |
| SECURITY-13 | Compliant | Checksummed migrations; images by digest; the secret check over both images |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Five S2 rules and ten panels as files, validated (TC-EHA-087) |
| SECURITY-15 | Compliant | S2 starts and serves without S1, failing closed per operation (TC-EHA-084, 085) |

## Invariant Compliance (I1 to I11)

I1 to I10 `Implemented`; I11 `N/A` (Construction selects technology). See
`functional-design/invariant-coverage-matrix.md`, *Code Generation*.

## L1 Coverage

33 applicable rows `Implemented`, 20 `N/A`, 0 `Missing`. See
`functional-design/l1-coverage-matrix.md`, *Code Generation*.
