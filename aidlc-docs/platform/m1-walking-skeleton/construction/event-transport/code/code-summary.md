# Code Summary: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). Data face, environment level: S4 `event-ingest`
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Design**: Functional Design, NFR Requirements, NFR Design, Infrastructure Design, and QA
enrichment, merged in soorma-core#24 (`37ec632`)
**Plan**: `construction/working/event-transport-code-generation-plan.md` (git-ignored), Steps 0
to 34; decisions D-CG-ET-01 to 34

## Groups

| Group | Commit | Content |
|---|---|---|
| Step 0 | `0df0754` | The plan's approval |
| 1 | `1719b3c` | `packages/jcs`: raw JSON numbers (`parseRawNumbers`), `canonicalize`'s source mode; the default mode refuses a raw value (D-CG-ET-16) |
| 2 | `7f62058` | `packages/authority`: the Body Form on `admit`; `payload_too_large` in P2's codes; the seal ring's loader re-exported |
| 3 | `cde6b98` | P5's verify-only key ring; service-kit's route body limits |
| 4 | `f5c129f` | P7 closed both ways; migrations `0005`, `0006`; S4's role `soorma_env_ingest`; P4's sponsor read |
| 5 | `e161a9f` | P9: `loadEventIngest`, S4's part, the shared-secret and role refusals |
| 6 | `218a8df` | The contract: `event-ingest.openapi.yaml`, the conventions, the CHANGELOG |
| 7 | `f76380a` | S4, its tests, its image and CI checks; `parseRawNumbers` made iterative (D-CG-ET-28); the frame's payload in JCS (D-CG-ET-29); reviewed by the user |
| 8 | `aed1ba0` | The local stack; smoke §12; `stack:outage` Case 4; the alert rules; the memory measurement |
| 9 | `19101e7` | `e2e/`: *done when* 3, 4, 6, 7 chained from done when 2; U7's stack proofs |
| 10 | (this commit) | The README and its docs test, this summary, the matrices |

Every group passed the full local gate (every check, every test with `pnpm db:test`, `pnpm audit`),
the image builds, secret scans, and installed-packages checks for the deployables it touched (from
Group 7, S4's self-check run in its image), and the local stack (init, up, smoke, `stack:outage`,
`test:e2e` on a fresh stack, `down -v`); its push run was green before the next group began.

**Stops for the user**: before Group 1 (NP-ET-05's premise: a `JSON.rawJSON` value passes the
default mode as a plain object, D-CG-ET-16); before Group 2 (U3's exhaustive codes test, the
import rule, the manifest: D-CG-ET-18 to 20); twice before Group 4 (P7's reverse rule against
U4's, U5's, and U6's tests: D-CG-ET-23, 24); twice in Group 7 (the reviver overflows past about
2,000 levels, D-CG-ET-28; `JSON.stringify` recurses once a raw value is present, and a
same-millisecond supersede could keep the older stream, D-CG-ET-29, 30); and the planned review
after Group 7 (approved).

## Where the Rules Are

| Rule | Where |
|---|---|
| The check order | `services/event-ingest/src/edge/edge-handlers.ts`: `present` (steps 2 to 4 through P1's `checkAgentRequest`), `parse`, `admit` (steps 5 to 10, once), the cap, `deliveryFrame`, `record`, then the hand-off or the stream; step 1 by Fastify's route limits (`settings.ts` `ROUTE_BODY_LIMITS`), logged by the `onResponse` hook in `apps.ts` |
| One bound | `runtime.ts` `assembleRuntime`: `PROPAGATION_BOUND_MS` imported from `@soorma/credentials` is the `ttl` of P5's revocation cache and U3's facts cache; the factories are injectable (TC-ET-030) |
| Payload numbers as written | `packages/jcs/src/raw-json.ts` `parseRawNumbers` (one iterative parser, D-CG-ET-28); the bound by `canonicalize(value, { numbers: 'source' })` (`measurePayload`); the frame's payload is that same text (D-CG-ET-29); `raw-json-check.ts`, run first by `start()` |
| The stream | `src/stream/stream.ts`: the serial chain, `admissible` (expiry, then P5's cache) before each write and on each sweep, the buffer, the heartbeat, one `end`, the grace |
| Superseding | `src/stream/registry.ts` `register` and `receive`, with the reply (D-CG-ET-31, enforcing BR-FO-05/07); `runtime.ts` `orderKey` (D-CG-ET-30) |
| The record and `hop` | `edge-handlers.ts` `record`: the sponsor in the same transaction, then P7; `hop` the chain's last index exactly when load-bearing |
| P7 closed both ways | `packages/attribution/src/record.ts` `checkRecord`; `0005_attribution_envelope_bearing.sql` |
| S4's role | `deploy/local/db/env-roles.sql`; grants in `0006` only; `tenancy.yaml`'s `eventIngest.database` |
| The published values | `contract/conventions/envelope.md` *The Delivery*, *The stream*; `src/settings.ts`; tied by TC-ET-053 and the README's docs test (TC-ET-087) |

## Files

Created and modified files are in the commits above (`git diff --stat 37ec632`). New workspace:
`services/event-ingest` (FSL-1.1-ALv2). New contract surface: `contract/event-ingest.openapi.yaml`.
New migrations: `0005`, `0006`. No new external dependency: S4's NestJS, Fastify,
reflect-metadata, and rxjs are S3's, at S3's versions; `pnpm audit` is clean.

## S4's Memory (D-ID-ET-17; D-CG-ET-33; TC-ET-088)

Recorded beside `mem_limit: 512m`, on a fresh local stack, cgroup v2 figures for `e-event-ingest`:

| Point | Memory |
|---|---|
| Idle | 67.6 MiB (79.1 MiB peak since start) |
| 256 streams open, nothing published | 88.5 MiB |
| 15 maximum Deliveries to each of 256 stalled streams (each about 0.99 MiB unread) | 309.3 MiB |
| Then three waves of 64 concurrent 256 KiB publishes | **peak 396.9 MiB** (`memory.peak`), **77.5 % of the limit**, under the 460 MiB stop |

The subscribers ran on network `soorma-local_e` so the port proxy could not drain them; no
stream overflowed; every publish answered 202. The limit is unchanged.

## Changes to Earlier Units' Tests and Scripts

Every change to a U1 to U6 test, harness, or script since `37ec632`, with its class (the standing
rules: 1, required by the approved design, items added; 2, strictly stronger; 3, anything else,
each approved by the user before it was made). The CI workflow gained steps only (S4's image,
scan, installed packages, no migrations, the self-check in the image: class 2).

### U3 `packages/authority/test/admission.test.ts` (TC-AE-031)

**Class 1, the user's single approved exception** (D-CG-ET-18): `payload_too_large` joined P2's codes.

```diff
+    'payload_too_large',
```

### U5 `services/control-gateway/test/registration.test.ts`

**Class 3, approved** (FD Q7 A): the constructed record's operation, exactly.

```diff
-        operation: 'constructedAgentOperation',
+        operation: 'exchangeBootstrap',
```

### U6 `packages/attribution/test/envelope-free.test.ts`

**Class 3, approved** (D-CG-ET-23 (1)), exactly.

```diff
-  it('other agent operations are unaffected, with or without an envelope (U7 decides)', () => {
+  it('other agent operations carry an envelope (U7 D-ET-07, the reverse rule)', () => {
-    expect(() => checkRecord(record('constructedAgentOperation'))).not.toThrow();
+    expect(() => checkRecord(record('constructedAgentOperation'))).toThrow(AttributionRecordError);
```

### U4 `packages/attribution/test/record.test.ts` (TC-EHA-047, the writer half)

**Class 3, approved** (D-CG-ET-24 (5)); Prettier wrapped it.

```diff
-    ['an agent actor without a sponsor', base({ ...agent, sponsor: '' })],
+    [
+      'an agent actor without a sponsor',
+      base({ ...agent, sponsor: '' }, { operation: 'exchangeBootstrap' }),
+    ],
```

### U4 `packages/env-store/test/store.test.ts`

TC-EHA-068's list: **class 1**. TC-EHA-047's store half: **class 3, approved** (D-CG-ET-23 (2)); every refusal kept its constraint name.

```diff
+          '0005_attribution_envelope_bearing',
+          '0006_event_ingest_role',
-      await insert(app, agent);
+      await insert(app, { ...agent, operation: 'exchangeBootstrap' });
```

### U6 `packages/env-store/test/agent-credentials.test.ts`

TC-AC-076's list: **class 1**; its title: **class 3, approved, title only** (the user, at the first Group 7 stop). TC-AC-036's store half: **class 3, approved** (D-CG-ET-24 (4)).

```diff
-  it('the store has applied all four, in order', async () => {
+  it('the store has applied every migration, in order', async () => {
+        '0005_attribution_envelope_bearing',
+        '0006_event_ingest_role',
-  it('accepts both operations as an agent with no envelope, and leaves other operations alone', async () => {
+  it('accepts both operations as an agent with no envelope; another agent operation carries one (U7 D-ET-07)', async () => {
-    await owner.query(P7.insertRecord, row('constructedAgentOperation', 'agent', null));
+    await expect(
+      owner.query(P7.insertRecord, row('constructedAgentOperation', 'agent', null)),
+    ).rejects.toMatchObject({
+      code: '23514',
+      constraint: 'attribution_envelope_bearing_operations',
+    });
```

### U4/U6 env-store test harness: the ingest role

**Class 1, with evidence**: `ENV_INGEST`, its password, an `ingest()` client added; U4's, U5's, and U6's store and privilege tests pass unedited.

```diff
-import { ENV_APP, ENV_DATA, ENV_MIGRATOR, runEnvRolesSql } from './roles.ts';
+import { ENV_APP, ENV_DATA, ENV_INGEST, ENV_MIGRATOR, runEnvRolesSql } from './roles.ts';
+  /** A client as S4's role, soorma_env_ingest (U7 D-ID-ET-04). */
+  ingest(): Promise<pg.Client>;
+    ingest: () => client(ENV_INGEST, info.ingestPassword),
-//      the data role's: D-ID-AC-07)
+//      the data role's: D-ID-AC-07; since U7, the ingest role's: D-ID-ET-04)
+  ENV_INGEST,
+  /** S4's role's password for this run (U7). */
+  ingestPassword: string;
+  const ingestPassword = randomBytes(24).toString('base64url');
+      await t.query(`ALTER ROLE ${ENV_INGEST} PASSWORD ${t.escapeLiteral(ingestPassword)}`);
+    ingestPassword,
+/** S4's own role (U7 D-ID-ET-04): added beside the three; their uses are unchanged. */
+export const ENV_INGEST = 'soorma_env_ingest';
```

### U4 `deploy/test/compose-model.test.ts`

**Class 1**: items added only (D-ID-ET-14). Its title "published: 127.0.0.1:8441 to 8445 only" is now stale; flagged, not changed.

```diff
+                'event-ingest',
+          `${env}-db-ingest-password`,
+          `${env}-event-ingest-tls`,
+          `${env}-agent-verify-key-1`,
+          `${env}-seal-key-1`,
+        'event-ingest',
+        [`${env}-event-ingest`, ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT']],
-      for (const r of ['db', 'migrate', 'control-gateway', 'data-gateway']) {
+      for (const r of ['db', 'migrate', 'control-gateway', 'data-gateway', 'event-ingest']) {
+          `${env}-event-ingest`,
+        'e-event-ingest 127.0.0.1:8446->8443',
+        'e2-event-ingest 127.0.0.1:8447->8443',
```

### U6 `deploy/test/data-gateway.test.ts`

**Class 3, approved** (D-CG-ET-23 (3), with the user's two checks), confirmed against the rendered model; the per-environment reading of "no service other than {env}-secrets-init" is D-CG-ET-34 (4).

```diff
-    '%s: agent signing keys only in data-gateway/; verify halves listed and copied nowhere (until U7)',
+    '%s: agent signing keys only in data-gateway/; verify halves only in event-ingest/ (U7)',
-          expect(n, dir).not.toMatch(/-agent-verify-key-/);
+          if (/-agent-verify-key-/.test(n)) expect(dir, n).toBe('event-ingest');
+          // U7 (the user's): every verify-key name in this environment's copies is its own.
+          if (/-agent-verify-key-/.test(n)) expect(n.startsWith(`${env}-`), n).toBe(true);
-      const listed = run([...compose, 'config', '--format', 'json']);
-      expect(listed).not.toMatch(/agent-verify-key/);
+      const listed = JSON.parse(run([...compose, 'config', '--format', 'json'])) as {
+        services: Record<string, { secrets?: { source: string }[] }>;
+      };
+      const verifyKeys = (name: string): string[] =>
+        (listed.services[name]?.secrets ?? [])
+          .map((x) => x.source)
+          .filter((x) => /agent-verify-key/.test(x));
+      expect(verifyKeys(`${env}-secrets-init`)).toEqual([`${env}-agent-verify-key-1`]);
+      // U7 (the user's): no service other than {env}-secrets-init lists any of
+      // this environment's verify keys; another environment's copier lists only
+      // its own environment's; every other service lists none.
+      for (const name of Object.keys(listed.services)) {
+        if (name === `${env}-secrets-init`) continue;
+        const other = ENVIRONMENTS.find((o) => o !== env && name === `${o}-secrets-init`);
+        if (other)
+          for (const k of verifyKeys(name))
+            expect(k.startsWith(`${other}-`), `${name} ${k}`).toBe(true);
+        else expect(verifyKeys(name), name).toEqual([]);
+      }
```

### U4 `deploy/test/monitoring.test.ts`

**Class 1**: S4's events joined to the union; S4's overlap pinned. Its title naming S1's to S3's events is now stale; flagged, not changed.

```diff
+import { SECURITY_EVENTS as S4_EVENTS } from '../../services/event-ingest/src/security-log.ts';
-const all: string[] = [...new Set([...union, ...S3_EVENTS])];
+const all: string[] = [...new Set([...union, ...S3_EVENTS, ...S4_EVENTS])];
+    // U7: S4 shares exactly store.unavailable and throttle.refused with S1 to S3.
+    expect(S4_EVENTS.filter((e) => [...union, ...S3_EVENTS].includes(e)).sort()).toEqual(
+      ['store.unavailable', 'throttle.refused'].sort(),
+    );
```

### U3 `packages/config/test/tenancy.test.ts`

**Class 3, approved at plan approval, title only.**

```diff
-  it("the U2 stack's tenancy.yaml still validates, with no sealKeys", () => {
+  it("the stack's tenancy.yaml still validates", () => {
```

### U1 contract tooling (`scripts/checks/sides.ts`, `scripts/validator.ts`, `scripts/generate-types.ts`)

**Class 1**: the fourth surface added; no U1 test edited.

```diff
+  'event-ingest.openapi.yaml#/components/schemas/PublishRequest',
+  'event-ingest.openapi.yaml#/components/schemas/SubscribeRequest',
+  'event-ingest.openapi.yaml#/components/schemas/StreamEnd',
+  'event-ingest.openapi.yaml#/components/schemas/StreamEndCode',
+  {
+    document: resolve(contractRoot, 'event-ingest.openapi.yaml'),
+    output: resolve(contractRoot, 'generated/event-ingest.ts'),
+    source: 'contract/event-ingest.openapi.yaml',
+  },
-export const SURFACES = ['org-gateway', 'control-gateway', 'data-gateway'] as const;
+export const SURFACES = ['org-gateway', 'control-gateway', 'data-gateway', 'event-ingest'] as const;
```

### U5/U6 `e2e/agent-registration.test.ts`

**Class 1**: the backup round trip's three lists gain `e-event-ingest` (TC-ET-086; Prettier wrapped
two calls); TC-AC-093 keeps each instance's credential in a `Map` beside `secrets`, one line inside
its loop, no assertion changed (D-CG-ET-12). *Done when* 3, 4, 6, 7 are new tests added after
TC-AC-093 (TC-ET-001 to 004, 006, 007); the header comment and the imports gained their lines. The
lines changed in U5's and U6's existing code:

```diff
-import { doneWhenTwo } from './agent-credentials-support.ts';
+/** Done when 2's agent credentials, kept for done when 3, 4, 6, 7 (U7 D-CG-ET-12). */
+const credentials = new Map<string, string>();
+      credentials.set(agent, (json(proof.renewals[i]!) as { credential: string }).credential);
-      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-data-gateway', 'e-db']);
-      docker([...COMPOSE, 'rm', '-f', 'e-control-gateway', 'e-data-gateway', 'e-db', 'e-migrate']);
+      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-data-gateway', 'e-event-ingest', 'e-db']);
+      docker([
+        ...COMPOSE,
+        'rm',
+        '-f',
+        'e-control-gateway',
+        'e-data-gateway',
+        'e-event-ingest',
+        'e-db',
+        'e-migrate',
+      ]);
-      docker([...COMPOSE, 'up', '-d', '--wait', 'e-control-gateway', 'e-data-gateway']);
+      docker([
+        ...COMPOSE,
+        'up',
+        '-d',
+        '--wait',
+        'e-control-gateway',
+        'e-data-gateway',
+        'e-event-ingest',
+      ]);
```

### U6 `deploy/local/scripts/stack-client.ts`

**Class 1, with evidence** (D-CG-ET-13): `registeredAgent` gains an optional parameter whose
default sends exactly the old body; `Reply` gains `headers`. Smoke §11, `stack:outage` Case 3, and
S3's tests pass unchanged. S4's helpers (`EVENT_INGEST`, `draft`, `publishAt`, `subscribeAt`) are
new. The lines changed in existing code:

```diff
+import type { IncomingHttpHeaders } from 'node:http';
+  headers: IncomingHttpHeaders;
+            headers: res.headers,
+  // U7 (D-CG-ET-13): the registration's further fields. Omitted, the body is
+  // exactly as before, { agent, standingPermissions: [] }, byte for byte.
+  registration: { standingPermissions?: string[]; autonomyDeclared?: boolean } = {},
-    body: { agent, standingPermissions: [] },
+    body: { agent, standingPermissions: [], ...registration },
```

Smoke §12 and `stack:outage` Case 4 are additions; every existing check and case is unchanged
(the outage script's header sentence naming the services it leaves running gained S4).

## Test Cases

Every TC-ET id from 001 to 093 is named by a test, a stack proof, or Build and Test:

| Where | Test cases |
|---|---|
| `services/event-ingest/test/flows.test.ts` (in process, db-test) | 026, 034, 037, 049, 052 (the whole publish path), 058, 071, 072, 076, 079, 080, 092 |
| `services/event-ingest/test/refusals.test.ts` | 006 (in process), 007 to 013, 019, 021, 024, 025, 027, 044, 050, 051, 052, 073, 090 |
| `services/event-ingest/test/streams.test.ts`, `stream-buffer.test.ts` | 016, 017, 029, 039, 048, 054, 060, 062, 063, 064; 056, 057 |
| `services/event-ingest/test/revocation.test.ts`, `edge.test.ts`, `composition.test.ts` | 014, 028, 031, 032, 035, 066; 055, 059, 061, 067, 068; 030, 033, 043, 047, 053 (S4's half), 075, 083 (the manifest half), 091 |
| `packages/jcs`, `authority`, `credentials`, `service-kit`, `attribution`, `env-store`, `config` tests | 074, 093 (and D-CG-ET-28's parser); 077; 078; 070; 042; 081, 082; 089 |
| `contract/test/event-ingest.test.ts` | 024, 038, 045, 053 |
| `deploy/test/` | 065, 069, 084, 087 |
| The stack: `smoke.ts` §12, `s1-outage.ts` Case 4, CI's image checks | 085, 067 (TLS 1.2 refused); 022; 083 (the image), 075 (the self-check in the image) |
| `e2e/` (the stack, raw calls) | **001, 002, 003, 004, 006, 007 (done when 3, 4, 6, 7)**; 005, 009, 014, 015, 017, 018, 020, 023, 028, 031, 037, 039, 040, 041, 048, 071, 072, 090; 086 (U5's backup round trip with S4) |
| Code Generation, recorded | 046 (the I8 re-check, below), 088 (S4's memory, above) |
| **Build and Test** | **036** (S4's p95 on the running stack, reported) |

## Security Compliance (SECURITY-01 to 15)

| Rule | Status |
|---|---|
| SECURITY-01 | In transit: TLS 1.3 at S4's edge, streams included, `verify-full` to the store (TC-ET-067). At rest: nothing of an event is stored (TC-ET-037) |
| SECURITY-02, 04 | N/A: no new intermediary or HTML |
| SECURITY-03 | Compliant, except the centralized log service (the user's M1 decision): S4 names agents, instances, and its environment, never a token, seal, envelope, payload, trace value, or human (TC-ET-068) |
| SECURITY-05 | Compliant: closed bodies; the route limits; the payload bound; the envelope bound; parameterized SQL; any nesting the limits admit parsed and serialized without recursion |
| SECURITY-06 | Compliant: S4's own role (`INSERT` on records, and only the reads it needs); its own five secrets; the verify half only, never a signing key |
| SECURITY-07 | Compliant: loopback edges; S4 on its own environment network only |
| SECURITY-08 | Compliant: every check at S4 from the raw request; a header claiming prior validation ignored (TC-ET-021) |
| SECURITY-09 | Compliant: no default credential; generic Problems; the bound and the limits not configurable |
| SECURITY-10 | Compliant: the image pinned; secret scan and installed-packages check; the self-check in the image |
| SECURITY-11 | Compliant: the throttle, the open-stream cap, the send buffer |
| SECURITY-12 | Compliant: mounted secrets only; a seal key, verify key, or password shared across parts refused (D-ID-ET-19) |
| SECURITY-13 | Compliant: each publish and subscribe attributed before it takes effect; checksummed migrations |
| SECURITY-14 | Not applicable in M1 (the user's decision): S4's alert rules as files |
| SECURITY-15 | Compliant: fail closed on the store, unreadable revocation, a frame that cannot be built (before any record), and a runtime without `JSON.rawJSON` |

## Invariant Compliance (I1 to I11)

I1 to I10 **Implemented** (invariant-coverage-matrix); I11 N/A. The I8 packaging table re-checked
(TC-ET-046): every capability core-assigned; no topic administration, durability, redelivery, or
acknowledgement code; S4's image holds no seeding path, test fixture, or migration of soorma's
own, and exactly the closure its installed-packages check allows.

## L1 Coverage

All 36 applicable rows **Implemented** (l1-coverage-matrix). L1-26 rests on GAP-ET-001 (Open,
soorma-prd#31), L1-30 on GAP-INT-003, L1-08 on GAP-INT-007, L1-10 on GAP-AE-001. Build and Test
moves rows to `Verified`.

## For Build and Test

- TC-ET-036: S4's p95 on the running stack, reported
- GAP-ET-001's residual (Open, soorma-prd#31): E's store is S4's availability floor for new
  publishes and subscribes
- The residuals of business-rules §17: the connection's close after revocation lags deliveries
  by up to R; a stream's authority fixed at open; live only; no topics; deep pretty-printed bodies
  can exceed the step-1 limits; PF §9's *Throughput* row not demonstrated for S4 in M1 (one S4 per
  environment). Cross-instance superseding is tested in process only. **After M1, not a Build
  and Test obligation**: clock skew between several S4 instances can let an older stream win a
  supersede (business-rules §17, §18)
- **For soorma-sdk** (the user's, D-CG-ET-28): S4 delivers payloads nested far deeper than common
  receiving parsers handle (Python's `json` at about 1,000 levels, a TypeScript reviver at about
  3,000); and object members arrive in RFC 8785 order (D-CG-ET-29)
- The contract tag `contract-v0.1.0`, on `main`, after this unit's code PR merges, with the
  user's go-ahead (D-ET-33)
