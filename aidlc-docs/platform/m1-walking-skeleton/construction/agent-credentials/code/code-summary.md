# Code Summary: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level: S3 `data-gateway`
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Design**: Functional Design, NFR Requirements, NFR Design, Infrastructure Design, and QA
enrichment, merged in soorma-core#22 (`1c3fd7d`)
**Plan**: `construction/working/agent-credentials-code-generation-plan.md` (git-ignored), Steps 0
to 38; decisions D-CG-AC-01 to 36

## Groups

| Group | Commit | Content |
|---|---|---|
| Step 0 | `8e7c779` | The plan's approval |
| 1 | `13de3cd` | P8's generic core (`SlotBound`, `slotOfKey`, `BatchWriter`), U2's API, tests, and vectors unchanged |
| 2 | `05a3909` | S3's workspace and closure test; P8's manifest fix; the image checks (`image-packages`; the agent and registration-secret patterns) |
| 3 | `5db3eaf` | Migrations `0003`, `0004`; S3's role `soorma_env_data` and its grants; the statements; P7's envelope-free operations; the privilege tests running the real statements |
| 4 | `7320d75` | P5's agent kind: the lifetimes, the token, the lineage records, the direct revocation source, and the fail-closed cache |
| 5 | `474e301` | The seam's agent half; P6's agent half (`agent-identity`); P8's agent bound and attempt writer; P1's `checkAgentRequest` |
| 6 | `4b9aa91` | The contract: `data-gateway.openapi.yaml`, `authentication_failed` widened, the instance sentence, *Revocation and Lifetimes* |
| 7 | `bf07765` | S3: configuration, the two operations, the image and its CI checks, S3's tests (reviewed by the user) |
| Fix | `0d3ad19` | The user's review: revocation names its granularity in the security log (D-CG-AC-31) |
| 8 | `78410e9` | The local stack; smoke, outage Case 3; the alert rules; the earlier-unit test changes approved for them |
| 9 | `4a2dad9` | `e2e/`: *done when* 2 chained from done when 1; U6's stack proofs |
| 10 | (this commit) | The README, the docs and review tests, the rotation test, this summary, the matrices |

Every group passed the full local gate (every check, every test with `pnpm db:test`, `pnpm audit`),
the image builds, secret scans, and installed-packages checks for the deployables it touched, and
the local stack where a runtime changed (init, up, smoke, `down -v`; from Group 8 also
`stack:outage` and `test:e2e` on a fresh stack), and its push run was green before the next group
began. Stops: after Group 7 for the review of S3's code (approved, with the fix); twice in Group 8
for class-3 changes (both approved by the user, then applied).

## Where the Rules Are

| Rule | Where |
|---|---|
| Bootstrap's check order and its one refusal | `services/data-gateway/src/edge/edge-handlers.ts`, `exchangeBootstrap` (no credential header, contract version, schema, the bound, P6, one transaction) and `refuseBootstrap` (settle, record, log, `authentication_failed`) |
| The single secret-record read | `packages/agent-identity/src/sql.ts` `secretForBootstrap`, run once by `resolver.ts`; the compare always runs, against a zero digest when no record exists |
| The bound | `packages/abuse-bound/src/agent-bound.ts` (`agentSlotKey`, `AGENT_BOOTSTRAP_LIMITS`, `AgentBound`) over `slot-bound.ts`; admitted before any material is parsed |
| Renewal's binding and expiry cap | the record matched to the token's agent and instance, and the UPDATE's `WHERE` (`packages/credentials/src/sql.ts` `renewAgentCredential`); `renewedExpiry` (now + L, never past the lineage end); the store's CHECK |
| The direct revocation read | `SQL.revoked` (both granularities as two columns) through `directRevocationSource`: at renewal through P1 and again inside the transaction (D-CG-AC-24); at bootstrap inside the transaction; `agent_revoked` takes precedence (D-CG-AC-31) |
| The agent key ring | `dataGateway.keys` in `packages/config`; loaded in `services/data-gateway/src/main.ts`; signs in `mintAgentCredential`, verifies in `verifyAgentCredential` |
| S3's role | `deploy/local/db/env-roles.sql`; grants in `0003` only; `tenancy.yaml`'s `dataGateway.database` |
| The fail-closed cache (for S4, U7) | `packages/credentials/src/revocation.ts` `createRevocationCache` |
| The published bounds | `packages/credentials/src/lifetimes.ts`; `contract/conventions/credentials.md` *Revocation and Lifetimes*; tied by TC-AC-038 |

## Files

Created and modified files are in the commits above (`git diff --stat 1c3fd7d`). New
workspaces: `packages/agent-identity` (FSL-1.1-ALv2) and `services/data-gateway` (FSL-1.1-ALv2).
New contract surface: `contract/data-gateway.openapi.yaml`. New migrations: `0003`, `0004`.

## Changes to Earlier Units' Tests

Every change to a U1 to U5 test, with its class and its before/after diff from `1c3fd7d`. The
CI workflow gained steps only (S1's positive control, S2's and S3's installed-packages checks,
S3's image, scan, and no-migrations check: class 2, scans more). `tools/checks/secrets.ts` gained
two patterns (class 2) and shares its tar reader with the new check; U2's tests are unchanged.

### U4 `packages/env-store/test/store.test.ts` (TC-EHA-068)

**Class**: 1, required by the approved design. The migration list gains `0003` and `0004`; nothing removed or reworded (D-CG-AC-18).

```diff
diff --git a/packages/env-store/test/store.test.ts b/packages/env-store/test/store.test.ts
index 22ab77f..f3c6ede 100644
--- a/packages/env-store/test/store.test.ts
+++ b/packages/env-store/test/store.test.ts
@@ -113,7 +113,12 @@ describe('TC-EHA-068: environment migrations are locked, checksummed, and run as
       const b = await fresh.migrator();
       try {
         const [x, y] = await Promise.all([migrate(a), migrate(b)]);
-        expect([...x, ...y].sort()).toEqual(['0001_init', '0002_registrations']);
+        expect([...x, ...y].sort()).toEqual([
+          '0001_init',
+          '0002_registrations',
+          '0003_agent_credentials',
+          '0004_attribution_envelope_free',
+        ]);
       } finally {
         await a.end();
         await b.end();
```

### U4 env-store test harness: the data role

**Class**: 1, with evidence (the user's Step 12 note). An export, a password, and a connection added; existing constants, connections, and `checkEnvRoleAttributes` unchanged. Evidence: main's exact `store.test.ts` against the new harness passed 26 of 27 (only TC-EHA-068's list, item above, differs); `restore.test.ts` and every other U4 and U5 store and privilege test pass with their files unedited (D-CG-AC-17).

```diff
diff --git a/packages/env-store/test/harness/database.ts b/packages/env-store/test/harness/database.ts
index 4a9f8e5..37a8d3e 100644
--- a/packages/env-store/test/harness/database.ts
+++ b/packages/env-store/test/harness/database.ts
@@ -12,7 +12,7 @@ import type { Store } from '@soorma/service-kit';
 import { connect } from '../../../org-identity/test/harness/global-setup.ts';
 import { connectEnvStore } from '../../src/index.ts';
 import type { EnvDatabaseInfo } from './global-setup.ts';
-import { ENV_APP, ENV_MIGRATOR, runEnvRolesSql } from './roles.ts';
+import { ENV_APP, ENV_DATA, ENV_MIGRATOR, runEnvRolesSql } from './roles.ts';
 
 export interface TestEnvDatabase {
   name: string;
@@ -27,6 +27,8 @@ export interface TestEnvDatabase {
   app(): Promise<pg.Client>;
   /** A client as the migrator role. */
   migrator(): Promise<pg.Client>;
+  /** A client as S3's role, soorma_env_data (U6 D-ID-AC-07). */
+  data(): Promise<pg.Client>;
   drop(): Promise<void>;
 }
 
@@ -97,6 +99,7 @@ export async function testEnvDatabase(options: { empty?: boolean } = {}): Promis
     superuser: () => client(),
     app: () => client(ENV_APP, info.appPassword),
     migrator: () => client(ENV_MIGRATOR, info.migratorPassword),
+    data: () => client(ENV_DATA, info.dataPassword),
     async drop() {
       await store.close();
       const a = connect(info.url, adminDb);
diff --git a/packages/env-store/test/harness/global-setup.ts b/packages/env-store/test/harness/global-setup.ts
index 57aa9af..3758c4d 100644
--- a/packages/env-store/test/harness/global-setup.ts
+++ b/packages/env-store/test/harness/global-setup.ts
@@ -5,7 +5,8 @@
 // superuser (TEST_DATABASE_URL), once per test run:
 //   1. creates an environment template database
 //   2. runs env-roles.sql against it, and checks the roles' attributes
-//   3. sets both environment roles' passwords for this run
+//   3. sets both environment roles' passwords for this run (and, since U6,
+//      the data role's: D-ID-AC-07)
 //   4. migrates the template as soorma_env_migrator, with the real runner
 // Each test file then clones its own database (database.ts) and connects as
 // soorma_env_app, so tests exercise the real privileges (TC-EHA-080). Without
@@ -15,7 +16,13 @@ import { randomBytes } from 'node:crypto';
 import type { TestProject } from 'vitest/node';
 import { connect } from '../../../org-identity/test/harness/global-setup.ts';
 import { migrate } from '../../src/index.ts';
-import { checkEnvRoleAttributes, ENV_APP, ENV_MIGRATOR, runEnvRolesSql } from './roles.ts';
+import {
+  checkEnvRoleAttributes,
+  ENV_APP,
+  ENV_DATA,
+  ENV_MIGRATOR,
+  runEnvRolesSql,
+} from './roles.ts';
 
 export interface EnvDatabaseInfo {
   /** The superuser URL. */
@@ -23,6 +30,8 @@ export interface EnvDatabaseInfo {
   template: string;
   appPassword: string;
   migratorPassword: string;
+  /** S3's role's password for this run (U6). */
+  dataPassword: string;
 }
 
 declare module 'vitest' {
@@ -40,6 +49,7 @@ export default async function setup(project: TestProject): Promise<(() => Promis
   const template = `soorma_env_template_${randomBytes(6).toString('hex')}`;
   const appPassword = randomBytes(24).toString('base64url');
   const migratorPassword = randomBytes(24).toString('base64url');
+  const dataPassword = randomBytes(24).toString('base64url');
   const adminDb = new URL(url).pathname.slice(1) || 'postgres';
   const admin = connect(url, adminDb);
   await admin.connect();
@@ -52,6 +62,7 @@ export default async function setup(project: TestProject): Promise<(() => Promis
       await checkEnvRoleAttributes(t);
       await t.query(`ALTER ROLE ${ENV_MIGRATOR} PASSWORD ${t.escapeLiteral(migratorPassword)}`);
       await t.query(`ALTER ROLE ${ENV_APP} PASSWORD ${t.escapeLiteral(appPassword)}`);
+      await t.query(`ALTER ROLE ${ENV_DATA} PASSWORD ${t.escapeLiteral(dataPassword)}`);
     } finally {
       await t.end();
     }
@@ -65,7 +76,13 @@ export default async function setup(project: TestProject): Promise<(() => Promis
   } finally {
     await admin.end();
   }
-  project.provide('soormaEnvDatabase', { url, template, appPassword, migratorPassword });
+  project.provide('soormaEnvDatabase', {
+    url,
+    template,
+    appPassword,
+    migratorPassword,
+    dataPassword,
+  });
   return async () => {
     const a = connect(url, adminDb);
     await a.connect();
diff --git a/packages/env-store/test/harness/roles.ts b/packages/env-store/test/harness/roles.ts
index b7ba81a..2932478 100644
--- a/packages/env-store/test/harness/roles.ts
+++ b/packages/env-store/test/harness/roles.ts
@@ -13,6 +13,8 @@ export const ENV_ROLES_SQL = resolve(
 );
 export const ENV_MIGRATOR = 'soorma_env_migrator';
 export const ENV_APP = 'soorma_env_app';
+/** S3's own role (U6 D-ID-AC-07): added beside the two; their uses are unchanged. */
+export const ENV_DATA = 'soorma_env_data';
 
 /** Runs env-roles.sql in the connected database, with the database name bound as the parameter. */
 export async function runEnvRolesSql(client: pg.ClientBase, database: string): Promise<void> {
```

### U4 `deploy/test/compose-model.test.ts`

**Class**: 2 (every profile), 1 (list items), and the two title corrections the user allowed. Group 3 added `{env}-db-data-password` to the copier list (D-CG-AC-19). Group 8 renders the model with every profile (scans more, every assertion unchanged), adds items to its lists only, and corrects two stale titles, titles only (D-CG-AC-32).

```diff
diff --git a/deploy/test/compose-model.test.ts b/deploy/test/compose-model.test.ts
index a27d1b3..4c41167 100644
--- a/deploy/test/compose-model.test.ts
+++ b/deploy/test/compose-model.test.ts
@@ -42,12 +42,15 @@ interface Model {
   networks: Record<string, unknown>;
 }
 
+const compose = ['compose', '-f', join(local, 'compose.yaml')];
+const run = (args: string[]): string =>
+  execFileSync('docker', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
+/** Every profile the stack lists (U6 D-ID-AC-13): the model holds every service. */
+const profiles = run([...compose, 'config', '--profiles'])
+  .split('\n')
+  .filter((p) => p.length > 0);
 const model = JSON.parse(
-  execFileSync(
-    'docker',
-    ['compose', '-f', join(local, 'compose.yaml'), 'config', '--format', 'json'],
-    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
-  ),
+  run([...compose, ...profiles.flatMap((p) => ['--profile', p]), 'config', '--format', 'json']),
 ) as Model;
 const services = model.services;
 const ENVIRONMENTS = ['e', 'e2'] as const;
@@ -75,13 +78,21 @@ function envCopies(env: string): Record<string, string[]> {
 }
 
 describe('TC-EHA-079: secrets are mounted files only, and never cross a level', () => {
-  it('the model has the twelve services, and only the copiers list secrets', () => {
+  it('the model has every service, under every profile, and only the copiers list secrets', () => {
     expect(Object.keys(services).sort()).toEqual(
       ['org', ...ENVIRONMENTS]
         .flatMap((l) =>
           l === 'org'
             ? ['org-db', 'org-gateway', 'org-migrate', 'org-secrets-init']
-            : ['control-gateway', 'db', 'migrate', 'secrets-init'].map((r) => `${l}-${r}`),
+            : [
+                'backup',
+                'control-gateway',
+                'data-gateway',
+                'db',
+                'migrate',
+                'restore',
+                'secrets-init',
+              ].map((r) => `${l}-${r}`),
         )
         .sort(),
     );
@@ -117,11 +128,15 @@ describe('TC-EHA-079: secrets are mounted files only, and never cross a level',
           `${env}-caller-key`,
           `${env}-control-gateway-tls`,
           `${env}-db-app-password`,
+          `${env}-db-data-password`,
           `${env}-db-migrator-password`,
           `${env}-db-superuser-password`,
           `${env}-db-tls`,
           `${env}-log-pseudonym-key`,
           `${env}-signing-key-1`,
+          `${env}-data-gateway-tls`,
+          `${env}-agent-signing-key-1`,
+          `${env}-bootstrap-counter-secret`,
         ].sort(),
       );
       for (const n of names) expect(n === 'stack-ca-cert' || n.startsWith(`${env}-`), n).toBe(true);
@@ -151,7 +166,14 @@ describe('TC-EHA-079: secrets are mounted files only, and never cross a level',
     for (const env of ENVIRONMENTS) {
       const copies = envCopies(env);
       // U5's backup/ (D-CG-AR-19): the migrator password and the CA, for the backup services.
-      expect(Object.keys(copies).sort()).toEqual(['backup', 'control-gateway', 'db', 'migrate']);
+      expect(Object.keys(copies).sort()).toEqual([
+        'backup',
+        'control-gateway',
+        'data-gateway',
+        'db',
+        'migrate',
+        'restore',
+      ]);
       expect(copies['control-gateway']).not.toContain(`${env}-db-migrator-password`);
       expect(copies.migrate?.sort()).toEqual([`${env}-db-migrator-password`, 'stack-ca-cert']);
       for (const n of Object.values(copies).flat())
@@ -173,6 +195,9 @@ describe('TC-EHA-079 / D-CG-EHA-23: the only environment variables are non-secre
         [`${env}-migrate`, ['SOORMA_ENVIRONMENT', 'SOORMA_PROJECT']],
         [`${env}-control-gateway`, ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT']],
         [`${env}-secrets-init`, []],
+        [`${env}-data-gateway`, ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT']],
+        [`${env}-backup`, ['PGPASSFILE']],
+        [`${env}-restore`, ['PGPASSFILE']],
       ]),
     ),
   };
@@ -204,7 +229,7 @@ describe('TC-EHA-079 / D-CG-EHA-23: the only environment variables are non-secre
 
   it('each environment service names its own environment and project', () => {
     for (const env of ENVIRONMENTS)
-      for (const r of ['db', 'migrate', 'control-gateway']) {
+      for (const r of ['db', 'migrate', 'control-gateway', 'data-gateway']) {
         const vars = services[`${env}-${r}`]?.environment ?? {};
         expect(vars.SOORMA_ENVIRONMENT, `${env}-${r}`).toBe(env);
         if (r !== 'db') expect(vars.SOORMA_PROJECT, `${env}-${r}`).toBe('p1');
@@ -248,7 +273,14 @@ describe('TC-EHA-089: no network spans two environments; only the edges are publ
     expect(members('org')).toEqual(['org-db', 'org-gateway', 'org-migrate']);
     for (const env of ENVIRONMENTS) {
       expect(members(env)).toEqual(
-        [`${env}-control-gateway`, `${env}-db`, `${env}-migrate`].sort(),
+        [
+          `${env}-control-gateway`,
+          `${env}-db`,
+          `${env}-migrate`,
+          `${env}-data-gateway`,
+          `${env}-backup`,
+          `${env}-restore`,
+        ].sort(),
       );
       expect(members(`org-internal-${env}`)).toEqual(
         [`${env}-control-gateway`, 'org-gateway'].sort(),
@@ -277,7 +309,7 @@ describe('TC-EHA-089: no network spans two environments; only the edges are publ
       if (role(name) === 'secrets-init') expect(services[name]?.network_mode, name).toBe('none');
   });
 
-  it('published: 127.0.0.1:8441, 8442 and 8443 only, each an edge; no store port', () => {
+  it('published: 127.0.0.1:8441 to 8445 only, each an edge; no store port', () => {
     const published = Object.entries(services).flatMap(([name, s]) =>
       (s.ports ?? []).map(
         (p) => `${name} ${p.host_ip ?? '0.0.0.0'}:${p.published ?? ''}->${p.target}`,
@@ -288,6 +320,8 @@ describe('TC-EHA-089: no network spans two environments; only the edges are publ
         'e-control-gateway 127.0.0.1:8442->8443',
         'e2-control-gateway 127.0.0.1:8443->8443',
         'org-gateway 127.0.0.1:8441->8443',
+        'e-data-gateway 127.0.0.1:8444->8443',
+        'e2-data-gateway 127.0.0.1:8445->8443',
       ].sort(),
     );
   });
```

### U5 `deploy/test/backup.test.ts`

**Class**: 3, approved by the user (Q5 A), exactly as worded. The restore services' expected subpath (D-ID-AC-14).

```diff
diff --git a/deploy/test/backup.test.ts b/deploy/test/backup.test.ts
index e44032d..7eac078 100644
--- a/deploy/test/backup.test.ts
+++ b/deploy/test/backup.test.ts
@@ -101,7 +101,7 @@ describe('TC-AR-057: the backup and restore services', () => {
         source: `${level(name)}-secrets`,
         target: '/run/secrets',
         read_only: true,
-        volume: { subpath: 'backup' },
+        volume: { subpath: name.endsWith('-restore') ? 'restore' : 'backup' },
       });
       // U5: and no other mount at all; the pgpass file is on a tmpfs.
       expect(withProfile[name]?.volumes, name).toHaveLength(1);
```

### U5 `e2e/agent-registration.test.ts`

**Class**: 1 (Group 8: services added to the round trip's lists) and the user's decision (Group 9: TC-AC-093 added after TC-AR-008). No U5 assertion or helper changes. TC-AR-008 did not keep the secret values, so one line inside its loop keeps the value it already reads, for TC-AC-093 (D-CG-AC-36).

```diff
diff --git a/e2e/agent-registration.test.ts b/e2e/agent-registration.test.ts
index 48a6f08..4c714fd 100644
--- a/e2e/agent-registration.test.ts
+++ b/e2e/agent-registration.test.ts
@@ -23,6 +23,7 @@ import { describe, expect, it } from 'vitest';
 import { ARCHIVE_MAGIC } from '../deploy/local/scripts/backup-archive.ts';
 import { backup } from '../deploy/local/scripts/stack-backup.ts';
 import { restore } from '../deploy/local/scripts/stack-restore.ts';
+import { doneWhenTwo } from './agent-credentials-support.ts';
 import {
   code,
   COMPOSE,
@@ -42,6 +43,8 @@ const B = `b-${Date.now().toString(36)}`;
 
 let K = '';
 let credential = '';
+/** Done when 1's secrets, kept for done when 2 (U6 TC-AC-093). */
+const secrets = new Map<string, string>();
 
 /** psql as the store's superuser, over the container's local socket (peer). */
 const sql = (statement: string): string =>
@@ -100,6 +103,7 @@ describe.skipIf(!E2E)('U5 agent-registration on the local stack', () => {
       const s = await post('/registration-secrets', credential, { registration: agent });
       expect(s.status, agent).toBe(200);
       expect((json(s) as { secret: string }).secret).toMatch(/^soorma_rs_/);
+      secrets.set(agent, (json(s) as { secret: string }).secret);
     }
     expect(sql(`SELECT count(*) FROM registrations WHERE agent IN ('${A}', '${B}')`)).toBe('2');
     expect(
@@ -109,6 +113,38 @@ describe.skipIf(!E2E)('U5 agent-registration on the local stack', () => {
     ).toBe('2');
   });
 
+  // U6 (TC-AC-093; D-AC-31): done when 2 chains from done when 1's real
+  // registrations and secrets. The calls are U6's (agent-credentials-support.ts).
+  it('TC-AC-093: done when 2, an instance of A and one of B bootstrap and renew', async () => {
+    const proof = await doneWhenTwo([
+      { agent: A, secret: secrets.get(A) ?? '', instance: 'a-1' },
+      { agent: B, secret: secrets.get(B) ?? '', instance: 'b-1' },
+    ]);
+    for (const [i, agent] of [A, B].entries()) {
+      for (const r of [proof.bootstraps[i]!, proof.renewals[i]!]) {
+        expect(r.status, r.body).toBe(200);
+        expect(r.protocol).toBe('TLSv1.3');
+        expect(json(r)).toMatchObject({
+          agent,
+          environment: { organization: 'o1', project: 'p1', environment: 'e' },
+          instance: i === 0 ? 'a-1' : 'b-1',
+        });
+      }
+    }
+    expect(proof.credentialRecords).toBe(2);
+    expect(proof.attribution).toHaveLength(4);
+    for (const record of proof.attribution)
+      expect(record).toMatchObject({ actor: 'agent', sponsor: PRINCIPAL.principal, noChain: true });
+    expect(proof.attribution.map((r) => `${r.registration}:${r.operation}`).sort()).toEqual(
+      [
+        `${A}:exchangeBootstrap`,
+        `${A}:renewAgentCredential`,
+        `${B}:exchangeBootstrap`,
+        `${B}:renewAgentCredential`,
+      ].sort(),
+    );
+  });
+
   it('TC-AR-043: every rejection holds for a raw call to the stack', async () => {
     const reg = (body: unknown) => post('/registrations', credential, body);
     const cases: [Promise<import('./support.ts').Reply>, number, string][] = [
@@ -212,8 +248,8 @@ r.on('error',(e)=>console.log(JSON.stringify({status:0,code:e.code})));r.end(JSO
       ).toBeGreaterThan(0);
 
       // Empty e's store: remove its volume, and start the store alone.
-      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-db']);
-      docker([...COMPOSE, 'rm', '-f', 'e-control-gateway', 'e-db', 'e-migrate']);
+      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-data-gateway', 'e-db']);
+      docker([...COMPOSE, 'rm', '-f', 'e-control-gateway', 'e-data-gateway', 'e-db', 'e-migrate']);
       docker(['volume', 'rm', 'soorma-local_e-db-data']);
       docker([...COMPOSE, 'up', '-d', '--wait', 'e-db']);
       expect(sql("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")).toBe('0');
@@ -242,7 +278,7 @@ r.on('error',(e)=>console.log(JSON.stringify({status:0,code:e.code})));r.end(JSO
         );
 
       // S2 back; a new credential from a new sign-in; the registrations survived.
-      docker([...COMPOSE, 'up', '-d', '--wait', 'e-control-gateway']);
+      docker([...COMPOSE, 'up', '-d', '--wait', 'e-control-gateway', 'e-data-gateway']);
       const fresh = await environmentCredential(K);
       expect((await post('/registration-secrets', fresh, { registration: A })).status).toBe(200);
       const again = await post('/registrations', fresh, { agent: B, standingPermissions: [] });
```

### U4 `deploy/test/monitoring.test.ts`

**Class**: 3, approved by the user (option A as amended). S1's and S2's disjointness kept exactly; S3's overlap asserted to be NFR-AC-22's four; the expected list the deduplicated union; the header and title name S3 (D-CG-AC-33).

```diff
diff --git a/deploy/test/monitoring.test.ts b/deploy/test/monitoring.test.ts
index e3ae25c..0e939ae 100644
--- a/deploy/test/monitoring.test.ts
+++ b/deploy/test/monitoring.test.ts
@@ -2,10 +2,11 @@
 //
 // The monitoring files as a whole (TC-EHA-087; U4 Infrastructure Design §9;
 // D-CG-EHA-17): both validate against their schemas; `events` is exactly the
-// union of every service's security events (S1's and S2's); every rule and
-// panel names one of them; U4's five rules carry §9's thresholds; and each S2
-// event has a panel grouped by environment. Nothing evaluates them in M1
-// (SECURITY-14, the user's decision).
+// union of every service's security events (S1's, S2's, and, since U6, S3's,
+// each name once); every rule and panel names one of them; U4's five rules
+// carry §9's thresholds; and each S2 event has a panel grouped by environment.
+// S1's and S2's events are disjoint; S3 shares exactly NFR-AC-22's four names
+// with them. Nothing evaluates them in M1 (SECURITY-14, the user's decision).
 import { readFileSync } from 'node:fs';
 import { join, resolve } from 'node:path';
 import { Ajv2020 } from 'ajv/dist/2020.js';
@@ -13,6 +14,7 @@ import { describe, expect, it } from 'vitest';
 import { parse } from 'yaml';
 import { SECURITY_EVENTS as S1_EVENTS } from '../../services/org-gateway/src/security-log.ts';
 import { SECURITY_EVENTS as S2_EVENTS } from '../../services/control-gateway/src/security-log.ts';
+import { SECURITY_EVENTS as S3_EVENTS } from '../../services/data-gateway/src/security-log.ts';
 
 const dir = resolve(import.meta.dirname, '../monitoring');
 const load = (name: string): unknown => parse(readFileSync(join(dir, name), 'utf8')) as unknown;
@@ -36,6 +38,8 @@ interface Dashboard {
 const alerts = load('alerts.yaml') as Alerts;
 const dashboard = load('dashboard.yaml') as Dashboard;
 const union: string[] = [...S1_EVENTS, ...S2_EVENTS];
+/** Every service's events, each name once (U6: S3 shares four of S2's names). */
+const all: string[] = [...new Set([...union, ...S3_EVENTS])];
 
 describe('TC-EHA-087: the monitoring files validate, and name only defined events', () => {
   it('validate against their schemas', () => {
@@ -44,16 +48,19 @@ describe('TC-EHA-087: the monitoring files validate, and name only defined event
     expect(ajv.validate(schema('dashboard.schema.json'), dashboard), ajv.errorsText()).toBe(true);
   });
 
-  it("list exactly the union of S1's and S2's events, each once", () => {
+  it("list exactly the union of S1's, S2's, and S3's events, each once", () => {
     expect(new Set(union).size).toBe(union.length);
+    expect(S3_EVENTS.filter((e) => union.includes(e)).sort()).toEqual(
+      ['credential.issued', 'credential.renewed', 'store.unavailable', 'throttle.refused'].sort(),
+    );
     expect(new Set(alerts.events).size).toBe(alerts.events.length);
-    expect([...alerts.events].sort()).toEqual([...union].sort());
+    expect([...alerts.events].sort()).toEqual([...all].sort());
   });
 
   it('name only listed events, in every rule and panel', () => {
-    for (const rule of alerts.rules) expect(union, rule.id).toContain(rule.event);
+    for (const rule of alerts.rules) expect(all, rule.id).toContain(rule.event);
     for (const panel of dashboard.panels)
-      for (const event of panel.events) expect(union).toContain(event);
+      for (const event of panel.events) expect(all).toContain(event);
   });
 
   it("carry U4's five rules with §9's thresholds", () => {
```

### U2 `services/org-gateway/test/monitoring.test.ts`

**Class**: 3, approved by the user (Decision 1, A). Grouping by agent only on a rule whose event S3 alone emits; every other rule and panel keeps the four groupings (D-CG-AC-35).

```diff
diff --git a/services/org-gateway/test/monitoring.test.ts b/services/org-gateway/test/monitoring.test.ts
index c035917..78210ee 100644
--- a/services/org-gateway/test/monitoring.test.ts
+++ b/services/org-gateway/test/monitoring.test.ts
@@ -7,6 +7,8 @@ import { Ajv2020 } from 'ajv/dist/2020.js';
 import { describe, expect, it } from 'vitest';
 import { parse } from 'yaml';
 import { SECURITY_EVENTS } from '../src/security-log.ts';
+import { SECURITY_EVENTS as S2_EVENTS } from '../../control-gateway/src/security-log.ts';
+import { SECURITY_EVENTS as S3_EVENTS } from '../../data-gateway/src/security-log.ts';
 
 const root = resolve(import.meta.dirname, '../../..');
 const dir = join(root, 'deploy/monitoring');
@@ -54,8 +56,16 @@ describe('the monitoring files', () => {
     expect(rule('auth.failed')).toMatchObject({ groupBy: 'pseudonym' });
     for (const event of ['auth.bound_refused', 'internal.call_refused', 'failed_attempt.dropped'])
       expect(rule(event)?.threshold.count).toBe(1);
+    // U6 (the user's decision): a logical agent is not a human, so only a rule
+    // for an event S3 alone emits may be grouped by agent.
+    const s3Only = (event: string): boolean =>
+      (S3_EVENTS as readonly string[]).includes(event) &&
+      !(SECURITY_EVENTS as readonly string[]).includes(event) &&
+      !(S2_EVENTS as readonly string[]).includes(event);
     const groupings = [
-      ...alerts.rules.map((r) => r.groupBy),
+      ...alerts.rules
+        .filter((r) => !(r.groupBy === 'agent' && s3Only(r.event)))
+        .map((r) => r.groupBy),
       ...dashboard.panels.map((p) => p.groupBy),
     ];
     expect(
```

### Root `package.json` `test:e2e`

**Class**: run order only, approved by the user. `--no-file-parallelism`: files run one at a time; no assertion or helper changes (D-CG-AC-36).

```diff
diff --git a/package.json b/package.json
index 01aa81d..8e66303 100644
--- a/package.json
+++ b/package.json
@@ -14,9 +14,10 @@
     "format:check": "prettier --check .",
     "test": "vitest run",
     "test:perf": "SOORMA_PERF=1 vitest run services/org-gateway/test/perf",
-    "test:e2e": "SOORMA_E2E=1 vitest run e2e --silent=false",
+    "test:e2e": "SOORMA_E2E=1 vitest run e2e --silent=false --no-file-parallelism",
     "test:perf:s2": "SOORMA_PERF=1 vitest run services/control-gateway/test/perf --silent=false",
     "bench:admit": "vitest bench --run --reporter=verbose packages/authority/bench",
+    "bench:revocation": "vitest bench --run --reporter=verbose packages/credentials/bench",
     "generate": "pnpm --filter @soorma/contract run generate",
     "check:generated": "pnpm --filter @soorma/contract run check:generated",
     "check:contract": "pnpm --filter @soorma/contract run check",
```

## Dependencies

No new external dependency (TC-AC-075): S3's NestJS, Fastify, reflect-metadata, and rxjs are
S2's, at S2's versions; `@soorma/jcs` is a workspace package. `pnpm audit` is clean.

## Test Cases

Every TC-AC id from 001 to 093 is named by a test, a stack proof, or Build and Test:

| Where | Test cases |
|---|---|
| `services/data-gateway/test/flows.test.ts` (in process, db-test) | 001 to 006, 011, 016, 019, 024, 027, 028, 031, 032, 035, 051, 053, 055 |
| `services/data-gateway/test/refusals.test.ts` | 007, 008, 009, 012, 013, 014, 018, 022, 025, 029, 030, 037, 042, 043, 048, 050, 061, 064 |
| `services/data-gateway/test/failures.test.ts`, `edge.test.ts`, `rotation.test.ts`, `closure.test.ts` | 010, 052; 063, 071, 072; 069; 040, 083 |
| `packages/credentials/test/` | 006, 015, 023, 034, 038, 050, 051, 053, 054, 055, 056, 065, 068, 078, 082 |
| `packages/agent-identity`, `abuse-bound`, `perimeter`, `attribution`, `env-store` tests | 022, 026, 048; 049, 057 to 060, 062, 081; 012, 039, 085; 036; 033, 036, 049, 076 to 080 |
| `contract/test/data-gateway.test.ts` | 021, 044, 045 |
| `deploy/test/` | 020, 069, 073, 086 to 090 |
| `tools/test/` | 041, 046, 047, 070, 074, 075, 083, 084 |
| The stack: `smoke.ts`, `s1-outage.ts` | 017, 020, 031, 090, 092 |
| `e2e/` (the stack, raw calls) | 004, 005, 009, 013, 025, 028, 091 (U5's round trip with S3), **093 (done when 2)** |
| **Build and Test (D-CG-AC-07)** | **066** (`pnpm bench:revocation`, reported: a cache hit at p99 0.001 ms in Group 4), **067** (p95 of both operations on the running stack, reported) |

## Security Compliance (SECURITY-01 to 15)

| Rule | Status |
|---|---|
| SECURITY-01 | In transit: TLS 1.3 at S3's edge, `verify-full` to the store. **At rest: not applicable in M1, the user's decision**: no token or secret value is stored |
| SECURITY-02, 04 | N/A: no new intermediary or HTML |
| SECURITY-03 | Compliant, except the centralized log service (the user's M1 decision): S3 names agents and instances, never a secret, its id, its digest, a token, or a human (TC-AC-072) |
| SECURITY-05 | Compliant: the closed bootstrap body, the 16 KiB bound, parameterized SQL |
| SECURITY-06 | Compliant: S3's own role with only its statements' privileges and no `DELETE`; its own secrets subdirectory; separate key rings |
| SECURITY-07 | Compliant: loopback edges; S3 on its own environment network only |
| SECURITY-08 | Compliant: every renewal check at S3 from the raw request; bootstrap accepts no credential |
| SECURITY-09 | Compliant: no default credential; generic Problems; B, L, M not configurable |
| SECURITY-10 | Compliant: images pinned; secret scan and installed-packages checks on every image |
| SECURITY-11 | Compliant: the bootstrap bound, the throttle |
| SECURITY-12 | Compliant: mounted secrets only; constant-time compare |
| SECURITY-13 | Compliant: write-once lineage records, each operation attributed; checksummed migrations |
| SECURITY-14 | Not applicable in M1 (the user's decision): S3's alert rules as files |
| SECURITY-15 | Compliant: fail closed on the store and on unreadable revocation; one transaction per operation |

## Invariant Compliance (I1 to I11)

I1 to I10 **Implemented** (invariant-coverage-matrix); I11 N/A. The I8 packaging table re-checked
(TC-AC-046): every capability core-assigned; no revocation initiation, rotation surface, or seeding
path in any image.

## L1 Coverage

All 34 applicable rows **Implemented** (l1-coverage-matrix). L1-27 and L1-29 rest on GAP-INT-008
(Open, soorma-prd#27), L1-28 on GAP-INT-009 (Open, soorma-prd#28). Build and Test moves rows to
`Verified`.

## For Build and Test

- TC-AC-066 and 067 (D-CG-AC-07)
- The residuals: the lockout (an outsider who knows an agent's identifier can stop its new
  instances for an attack's length and at most 60 seconds after; running instances renew), with
  option B's mitigation carried to the first hosted deployment; no revocation writer in M1 (PF
  FR-011 deferred; test-only seeding); at S3 a revocation is refused at the next renewal, and the
  bound B applies at S4 (U7)
- U7's obligations (soorma-core#10): S4's edges from 8446, the agent verify halves, its own role,
  the revocation cache with `PROPAGATION_BOUND_MS`, the cache's three answers
- The user's M1 decisions on SECURITY-01 at rest, SECURITY-03's log service, SECURITY-14
