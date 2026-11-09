// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-OI-049 (logs carry no secret and no human identifier), TC-OI-029 (the
// structure that keeps refusal timing independent of existence), TC-OI-025
// over HTTP, TC-OI-048 at start-up, and TC-OI-061 (no tenant identifier in
// platform code).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { ConfigurationError } from '@soorma/config';
import { FailedAttemptWriter } from '@soorma/abuse-bound';
import {
  ARGON2_PARAMETERS,
  asSecretBytes,
  codeAt,
  stepAt,
  type Argon2Call,
  type Queryable,
} from '@soorma/org-identity';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testDatabase,
  type TestDatabase,
} from '../../../packages/org-identity/test/harness/database.ts';
import {
  CapturingRecorder,
  recordingArgon2id,
  type RecordedAttempt,
} from '../../../packages/org-identity/test/harness/domain.ts';
import { productionHasher, start } from '../src/main.ts';
import { SECURITY_EVENTS, SecurityLog } from '../src/security-log.ts';
import { active, gateway, K, K2, post, registered, type Gateway } from './support.ts';

let db: TestDatabase;
beforeAll(async () => {
  db = await testDatabase();
});
afterAll(async () => {
  await db?.drop();
});

function base32Decode(text: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0;
  let acc = 0;
  const out: number[] = [];
  for (const c of text) {
    acc = (acc << 5) | alphabet.indexOf(c);
    bits += 5;
    if (bits >= 8) {
      out.push((acc >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

describe('TC-OI-049: logs carry no secret and no human identifier', () => {
  let g: Gateway;
  afterAll(async () => {
    await g?.close();
  });

  it('runs every flow with known secrets and identifiers, and finds none in the output', async () => {
    g = await gateway(db);
    const secrets: string[] = [K, K2];
    const { principal, em } = await registered(g);
    secrets.push(em);
    const first = await post(g.edge, '/first-authentication', {
      principal,
      enrollmentMaterial: em,
      newSecret: K,
    });
    secrets.push(first.body.signIn.token as string);
    await post(g.edge, '/sign-ins', { principal, secret: 'wrong-secret-xyz' });
    secrets.push('wrong-secret-xyz');
    await post(g.edge, '/first-authentication', {
      principal,
      enrollmentMaterial: em,
      newSecret: K2,
    });
    const unknown = { organization: 'o1', principal: 'never-registered@example.org' };
    await post(g.edge, '/sign-ins', { principal: unknown, secret: K });
    const begun = await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: { type: 'beginSecondFactor', authenticatorType: 'totp' },
    });
    const seed = begun.body.enrollment.setup.seed as string;
    secrets.push(seed, begun.body.enrollment.setup.otpauthUri as string);
    await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K },
      change: {
        type: 'confirmSecondFactor',
        enrollment: begun.body.enrollment.id as string,
        proof: {
          type: 'totp',
          code: codeAt(asSecretBytes(base32Decode(seed)), stepAt(g.clock.now())),
        },
      },
    });
    g.clock.advance(30);
    const signIn = await post(g.edge, '/sign-ins', {
      principal,
      secret: K,
      secondFactor: {
        type: 'totp',
        code: codeAt(asSecretBytes(base32Decode(seed)), stepAt(g.clock.now())),
      },
    });
    secrets.push(signIn.body.signIn.token as string);
    await post(g.edge, '/sign-ins/current/renewal', undefined, {
      authorization: `Bearer ${signIn.body.signIn.token as string}`,
    });
    await post(g.edge, '/sign-ins/current/end', undefined, {
      authorization: `Bearer ${signIn.body.signIn.token as string}`,
    });
    await post(g.edge, '/material-changes', {
      principal,
      current: { secret: K, secondFactor: { type: 'totp', code: '000000' } },
      change: { type: 'replaceSecret', newSecret: K2 },
    });

    const output = g.log.lines.join('\n');
    expect(g.log.lines.length).toBeGreaterThan(5);
    for (const secret of secrets) expect(output).not.toContain(secret);
    for (const identifier of [principal.principal, unknown.principal, 'example.com', 'example.org'])
      expect(output).not.toContain(identifier);
    for (const line of g.log.events()) {
      if ('event' in line) expect(SECURITY_EVENTS).toContain(line.event);
      if ('pseudonym' in line) expect(line.pseudonym).toMatch(/^hp_[A-Za-z0-9_-]{22}$/);
      expect(
        Object.keys(line).every((k) =>
          [
            'event',
            'requestId',
            'pseudonym',
            'count',
            'code',
            'environment',
            'notice',
            'error',
          ].includes(k),
        ),
      ).toBe(true);
    }
    const names = g.log.events().map((l) => l.event);
    for (const event of ['auth.failed', 'signin.issued', 'signin.ended', 'material.changed'])
      expect(names).toContain(event);
  });

  it('writes one JSON line per event through NestJS ConsoleLogger', () => {
    const chunks: string[] = [];
    const write = process.stdout.write.bind(process.stdout);
    process.stdout.write = (chunk: string | Uint8Array) => {
      chunks.push(String(chunk));
      return true;
    };
    try {
      new SecurityLog().event('auth.failed', 'req-1', { code: 'authentication_failed' });
    } finally {
      process.stdout.write = write;
    }
    const line = JSON.parse(chunks.join('').trim()) as Record<string, unknown>;
    expect(line).toMatchObject({
      level: 'log',
      message: { event: 'auth.failed', requestId: 'req-1', code: 'authentication_failed' },
    });
  });
});

describe('TC-OI-029: refusal timing does not reveal whether a principal exists (structure)', () => {
  it('one Argon2id call with the real parameters each; the record is queued, never awaited', async () => {
    const calls: Argon2Call[] = [];
    const argon2id = recordingArgon2id(calls);
    // The Failed Attempt queue's write never resolves; the response must not wait for it.
    const stuck: Queryable = { query: () => new Promise(() => undefined) };
    const writer = new FailedAttemptWriter(stuck, { batchSize: 1 });
    class Forwarding extends CapturingRecorder {
      override record(attempt: RecordedAttempt): void {
        super.record(attempt);
        writer.record(attempt);
      }
    }
    const failures = new Forwarding();
    const g = await gateway(db, { argon2id, failures, realHashing: true }); // real parameters, passed to the double
    try {
      const { principal } = await active(g);
      const real = {
        memory: ARGON2_PARAMETERS.memory,
        passes: ARGON2_PARAMETERS.passes,
        parallelism: ARGON2_PARAMETERS.parallelism,
        tagLength: ARGON2_PARAMETERS.tagLength,
      };
      const unknown = { organization: 'o1', principal: 'nobody@example.com' };
      const cases = [
        () => post(g.edge, '/sign-ins', { principal, secret: 'wrong secret' }),
        () => post(g.edge, '/sign-ins', { principal: unknown, secret: 'wrong secret' }),
        () =>
          post(g.edge, '/first-authentication', {
            principal: unknown,
            enrollmentMaterial: 'soorma_em_x',
            newSecret: K,
          }),
      ];
      const bodies: unknown[] = [];
      const queued: number[] = [];
      for (const call of cases) {
        calls.length = 0;
        const before = failures.records.length;
        const r = await call();
        expect(r.status).toBe(403);
        expect(calls).toHaveLength(1);
        expect(calls[0]).toMatchObject(real);
        queued.push(failures.records.length - before);
        const { instance: _instance, ...rest } = r.body as Record<string, unknown>;
        void _instance;
        bodies.push(rest);
      }
      expect(queued).toEqual([1, 0, 0]);
      expect(bodies[1]).toEqual(bodies[0]);
      expect(bodies[2]).toEqual(bodies[0]);
    } finally {
      await g.close();
    }
  });
});

describe('TC-OI-025 over HTTP: material of a class core does not accept', () => {
  it('is malformed_request: the closed bodies have no field for it', async () => {
    const g = await gateway(db);
    try {
      const { principal } = await active(g);
      const r = await post(g.edge, '/sign-ins', {
        principal,
        secret: K,
        external: { issuer: 'https://idp.example', assertion: 'x' },
      });
      expect(r.status).toBe(400);
      expect(r.body.code).toBe('malformed_request');
      expect(r.body.errors).toContainEqual({ pointer: '/external', detail: expect.any(String) });
    } finally {
      await g.close();
    }
  });
});

describe('NFR-OI-11: S1 hashes with the real parameters', () => {
  it('wires Argon2id at 64 MiB, 3 passes, parallelism 1, never a test profile', () => {
    expect(productionHasher({ budgetMiB: 512 }).parameters).toBe(ARGON2_PARAMETERS);
    expect(ARGON2_PARAMETERS).toEqual({
      memory: 65536,
      passes: 3,
      parallelism: 1,
      tagLength: 32,
      saltLength: 16,
    });
  });
});

describe('TC-OI-048 at start-up: a configuration error stops S1 before it serves anything', () => {
  it('refuses a missing or invalid tenancy.yaml', async () => {
    await expect(start({ configPath: '/nonexistent/tenancy.yaml' })).rejects.toThrow(
      ConfigurationError,
    );
  });
});

describe('TC-OI-061: no tenant identifier is hard-coded in platform code', () => {
  it('finds none of the local stack’s identifiers in any package or service source', () => {
    const root = resolve(import.meta.dirname, '../../..');
    const files: string[] = [];
    const walk = (dir: string): void => {
      for (const name of readdirSync(dir)) {
        const full = join(dir, name);
        if (statSync(full).isDirectory()) walk(full);
        else if (name.endsWith('.ts')) files.push(full);
      }
    };
    for (const base of ['packages', 'services', 'seams'])
      for (const pkg of readdirSync(join(root, base))) {
        const src = join(root, base, pkg, 'src');
        try {
          walk(src);
        } catch {
          // a package without src
        }
      }
    expect(files.length).toBeGreaterThan(10);
    const tenant = /['"`](o1|p1|e2|h@example\.com)['"`]|@example\.(com|org)/;
    const offenders = files.filter((f) => tenant.test(readFileSync(f, 'utf8')));
    expect(offenders).toEqual([]);
  });
});
