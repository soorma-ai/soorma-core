// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U5 on the local stack, by raw calls (D-CG-AR-02, 03, 22). One file, in
// order, because H's first authentication happens once per stack and test
// files run in separate workers:
//
//  1. Done when 1 (TC-AR-008; ID §1 trace steps 5 to 9): H self-grants
//     agent:register, event:publish, event:subscribe; registers A and B, each
//     with its own sponsor reference and ceiling snapshot; issues a secret for
//     each
//  2. Every rejection, by raw call (TC-AR-043), and the same credential from
//     inside E's network (TC-AR-044)
//  3. Backup and restore (TC-AR-059, 056, 060 on the real dump; D-CG-AR-03):
//     back up e, empty e's store, restore into it, e-migrate applies nothing,
//     the app role's privileges hold, S2 back up; the registrations survived
//
// Run by `pnpm test:e2e` on a fresh stack (`down -v`, `stack:up`); skipped
// otherwise.
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, readFileSync, statSync, unlinkSync } from 'node:fs';
import { dirname } from 'node:path';
import { describe, expect, it } from 'vitest';
import { ARCHIVE_MAGIC } from '../deploy/local/scripts/backup-archive.ts';
import { backup } from '../deploy/local/scripts/stack-backup.ts';
import { restore } from '../deploy/local/scripts/stack-restore.ts';
import { doneWhenTwo } from './agent-credentials-support.ts';
import {
  code,
  COMPOSE,
  docker,
  E2E,
  environmentCredential,
  firstAuthentication,
  json,
  post,
  PRINCIPAL,
  SECRETS,
} from './support.ts';

const HELD = ['agent:register', 'event:publish', 'event:subscribe', 'grant:human', 'human:manage'];
const A = `a-${Date.now().toString(36)}`;
const B = `b-${Date.now().toString(36)}`;

let K = '';
let credential = '';
/** Done when 1's secrets, kept for done when 2 (U6 TC-AC-093). */
const secrets = new Map<string, string>();

/** psql as the store's superuser, over the container's local socket (peer). */
const sql = (statement: string): string =>
  docker([
    ...COMPOSE,
    'exec',
    '-T',
    'e-db',
    'psql',
    '-U',
    'postgres',
    '-d',
    'soorma_env',
    '-Atc',
    statement,
  ]);

// A file's tests run in order (Vitest's default), which this file relies on.
describe.skipIf(!E2E)('U5 agent-registration on the local stack', () => {
  it('TC-AR-008: done when 1, two agents each with its own sponsor and snapshot', async () => {
    K = await firstAuthentication();
    credential = await environmentCredential(K);
    const granted = await post('/grants', credential, {
      target: PRINCIPAL,
      permissions: ['agent:register', 'event:publish', 'event:subscribe'],
    });
    expect(granted.status).toBe(200);

    const a = await post('/registrations', credential, {
      agent: A,
      standingPermissions: ['event:publish'],
      autonomyDeclared: true,
    });
    const b = await post('/registrations', credential, {
      agent: B,
      standingPermissions: ['event:subscribe'],
      autonomyDeclared: true,
    });
    expect([a.status, b.status]).toEqual([200, 200]);
    expect(a.protocol).toBe('TLSv1.3');
    for (const [r, agent, standing] of [
      [a, A, 'event:publish'],
      [b, B, 'event:subscribe'],
    ] as const)
      expect(json(r)).toMatchObject({
        agent,
        environment: { organization: 'o1', project: 'p1', environment: 'e' },
        sponsor: PRINCIPAL,
        ceilingSnapshot: HELD,
        standingPermissions: [standing],
        reBroadeningDeclaration: [],
        autonomyDeclared: true,
        state: 'registered',
      });
    for (const agent of [A, B]) {
      const s = await post('/registration-secrets', credential, { registration: agent });
      expect(s.status, agent).toBe(200);
      expect((json(s) as { secret: string }).secret).toMatch(/^soorma_rs_/);
      secrets.set(agent, (json(s) as { secret: string }).secret);
    }
    expect(sql(`SELECT count(*) FROM registrations WHERE agent IN ('${A}', '${B}')`)).toBe('2');
    expect(
      sql(
        `SELECT count(*) FROM attribution_records WHERE operation = 'registerAgent' AND principal = 'h@example.com' AND target_id IN ('${A}', '${B}')`,
      ),
    ).toBe('2');
  });

  // U6 (TC-AC-093; D-AC-31): done when 2 chains from done when 1's real
  // registrations and secrets. The calls are U6's (agent-credentials-support.ts).
  it('TC-AC-093: done when 2, an instance of A and one of B bootstrap and renew', async () => {
    const proof = await doneWhenTwo([
      { agent: A, secret: secrets.get(A) ?? '', instance: 'a-1' },
      { agent: B, secret: secrets.get(B) ?? '', instance: 'b-1' },
    ]);
    for (const [i, agent] of [A, B].entries()) {
      for (const r of [proof.bootstraps[i]!, proof.renewals[i]!]) {
        expect(r.status, r.body).toBe(200);
        expect(r.protocol).toBe('TLSv1.3');
        expect(json(r)).toMatchObject({
          agent,
          environment: { organization: 'o1', project: 'p1', environment: 'e' },
          instance: i === 0 ? 'a-1' : 'b-1',
        });
      }
    }
    expect(proof.credentialRecords).toBe(2);
    expect(proof.attribution).toHaveLength(4);
    for (const record of proof.attribution)
      expect(record).toMatchObject({ actor: 'agent', sponsor: PRINCIPAL.principal, noChain: true });
    expect(proof.attribution.map((r) => `${r.registration}:${r.operation}`).sort()).toEqual(
      [
        `${A}:exchangeBootstrap`,
        `${A}:renewAgentCredential`,
        `${B}:exchangeBootstrap`,
        `${B}:renewAgentCredential`,
      ].sort(),
    );
  });

  it('TC-AR-043: every rejection holds for a raw call to the stack', async () => {
    const reg = (body: unknown) => post('/registrations', credential, body);
    const cases: [Promise<import('./support.ts').Reply>, number, string][] = [
      [reg({ agent: 'x1', standingPermissions: ['agent:retire'] }), 403, 'exceeds_sponsor_ceiling'],
      [reg({ agent: 'x2', standingPermissions: ['grant:human'] }), 400, 'human_only_permission'],
      [
        reg({
          agent: 'x3',
          standingPermissions: ['event:publish'],
          reBroadeningDeclaration: ['event:subscribe'],
        }),
        400,
        'declaration_outside_standing',
      ],
      [reg({ agent: 'x4', standingPermissions: ['invoice:approve'] }), 400, 'unknown_permission'],
      [reg({ agent: A, standingPermissions: ['event:publish'] }), 409, 'registration_exists'],
      [
        post('/registration-secrets', credential, { registration: 'nobody' }),
        400,
        'unknown_registration',
      ],
      [
        post('/registrations', `soorma_ac_${'A'.repeat(40)}`, {
          agent: 'x5',
          standingPermissions: [],
        }),
        401,
        'credential_refused',
      ],
      [
        post('/registrations', `soorma_ec_${'A'.repeat(40)}`, {
          agent: 'x6',
          standingPermissions: [],
        }),
        401,
        'credential_refused',
      ],
    ];
    for (const [pending, status, expected] of cases) {
      const r = await pending;
      expect([r.status, code(r)]).toEqual([status, expected]);
    }
  });

  it('TC-AR-044: the same credential from inside network e registers with the same sponsor', () => {
    const ca = readFileSync(`${SECRETS}/stack-ca.pem`, 'utf8');
    const inside = (
      token: string,
      agent: string,
    ): { status: number; sponsor?: unknown; code?: unknown } => {
      const r = spawnSync(
        'docker',
        [
          'run',
          '--rm',
          '-i',
          '--network',
          'soorma-local_e',
          '--read-only',
          '--cap-drop',
          'ALL',
          '--security-opt',
          'no-new-privileges:true',
          '--entrypoint',
          '/nodejs/bin/node',
          'soorma/control-gateway:local',
          '-e',
          `const {ca,token,body}=JSON.parse(require('fs').readFileSync(0,'utf8'));
const r=require('https').request({host:'control-gateway.e.soorma.internal',port:8443,path:'/registrations',method:'POST',ca,
headers:{'soorma-contract-version':'0.1.0','content-type':'application/json',...(token?{authorization:'Bearer '+token}:{})}},
(res)=>{let b='';res.on('data',(c)=>b+=c);res.on('end',()=>{let j={};try{j=JSON.parse(b)}catch{}console.log(JSON.stringify({status:res.statusCode,sponsor:j.sponsor,code:j.code}))})});
r.on('error',(e)=>console.log(JSON.stringify({status:0,code:e.code})));r.end(JSON.stringify(body));`,
        ],
        {
          input: JSON.stringify({ ca, token, body: { agent, standingPermissions: [] } }),
          encoding: 'utf8',
        },
      );
      return JSON.parse(r.stdout.trim()) as { status: number; sponsor?: unknown };
    };
    const fromInside = inside(credential, `inside-${Date.now().toString(36)}`);
    expect(fromInside).toMatchObject({ status: 200, sponsor: PRINCIPAL });
    expect(inside('', `none-${Date.now().toString(36)}`)).toMatchObject({
      status: 401,
      code: 'credential_refused',
    });
  });

  it('TC-AR-059, 056, 060: back up e, empty its store, restore, and the registrations survive', async () => {
    const before = sql(
      "SELECT (SELECT count(*) FROM registrations)||','||(SELECT count(*) FROM registration_secrets)||','||(SELECT count(*) FROM attribution_records)||','||(SELECT count(*) FROM schema_migrations)",
    );
    const file = await backup('e');
    try {
      // TC-AR-056, 060 on the real dump.
      expect(statSync(file).mode & 0o777).toBe(0o600);
      expect(statSync(dirname(file)).mode & 0o777).toBe(0o700);
      expect(readFileSync(file).subarray(0, 5).equals(ARCHIVE_MAGIC)).toBe(true);
      expect(
        execFileSync('git', ['check-ignore', file], { encoding: 'utf8' }).trim().length,
      ).toBeGreaterThan(0);

      // Empty e's store: remove its volume, and start the store alone.
      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-data-gateway', 'e-db']);
      docker([...COMPOSE, 'rm', '-f', 'e-control-gateway', 'e-data-gateway', 'e-db', 'e-migrate']);
      docker(['volume', 'rm', 'soorma-local_e-db-data']);
      docker([...COMPOSE, 'up', '-d', '--wait', 'e-db']);
      expect(sql("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")).toBe('0');

      expect(await restore('e', file)).toBe(0);
      // A non-empty database is refused.
      expect(await restore('e', file)).toBe(3);

      // e-migrate applies nothing; the rows are equal.
      docker([...COMPOSE, 'up', 'e-migrate']);
      expect(docker([...COMPOSE, 'ps', '-a', '--format', '{{.ExitCode}}', 'e-migrate'])).toBe('0');
      expect(
        sql(
          "SELECT (SELECT count(*) FROM registrations)||','||(SELECT count(*) FROM registration_secrets)||','||(SELECT count(*) FROM attribution_records)||','||(SELECT count(*) FROM schema_migrations)",
        ),
      ).toBe(before);

      // The app role's privileges hold on the restored store.
      for (const statement of [
        "UPDATE registrations SET sponsor = 'x'",
        'DELETE FROM registration_secrets',
        'DELETE FROM grants',
      ])
        expect(() => sql(`SET ROLE soorma_env_app; ${statement}`), statement).toThrow(
          /permission denied/,
        );

      // S2 back; a new credential from a new sign-in; the registrations survived.
      docker([...COMPOSE, 'up', '-d', '--wait', 'e-control-gateway', 'e-data-gateway']);
      const fresh = await environmentCredential(K);
      expect((await post('/registration-secrets', fresh, { registration: A })).status).toBe(200);
      const again = await post('/registrations', fresh, { agent: B, standingPermissions: [] });
      expect([again.status, code(again)]).toEqual([409, 'registration_exists']);
    } finally {
      if (existsSync(file)) unlinkSync(file);
    }
    expect(existsSync(file)).toBe(false);
  });
});
