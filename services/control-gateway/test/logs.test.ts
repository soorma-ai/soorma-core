// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's logs (NFR-EHA-18, 19; NP-EHA-12): no token, key, or principal
// identifier in any line; a human named only by E's own pseudonym; and every
// one of the ten security events emitted by its flow.
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { Semaphore, type Timers } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import { SECURITY_EVENTS } from '../src/security-log.ts';
import { registrationFlows } from './registration-support.ts';
import { credentialFor, gateway, grant, post, unique, type Gateway } from './support.ts';

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

class ManualTimers implements Timers {
  private next = 0;
  readonly pending = new Map<number, () => void>();
  set(callback: () => void): unknown {
    const id = this.next++;
    this.pending.set(id, callback);
    return id;
  }
  clear(handle: unknown): void {
    this.pending.delete(handle as number);
  }
  fire(): void {
    const due = [...this.pending.values()];
    this.pending.clear();
    for (const c of due) c();
  }
}

async function everyFlow(g: Gateway, timers: ManualTimers): Promise<string[]> {
  const secrets: string[] = [g.admin];
  const admin = await credentialFor(g, g.admin);
  secrets.push(admin.credential, admin.sid);
  const j = unique();
  secrets.push(j);
  g.stub.principals.add(j);
  await grant(g, admin.credential, j, ['agent:register']); // grant.made
  const jc = await credentialFor(g, j); // credential.issued
  secrets.push(jc.credential, jc.sid);
  await grant(g, jc.credential, g.admin, ['agent:register']); // grant.denied
  await post(g.edge, '/environment-credentials/current/renewal', { credential: jc.credential }); // renewed
  await post(g.edge, '/environment-credentials/current/end', { credential: jc.credential }); // ended
  await post(g.edge, '/environment-credentials/current/end', { credential: jc.credential }); // refused
  const unknown = 'nobody-known@example.com';
  secrets.push(unknown);
  await grant(g, admin.credential, unknown, ['agent:register']);
  const s = await g.stub.signIn(unique());
  secrets.push(s.token);
  await post(g.edge, '/environment-credentials', { credential: s.token }); // refused: no grant
  g.stub.down = true;
  await post(g.edge, '/environment-credentials/current/renewal', { credential: admin.credential }); // orglevel
  g.stub.down = false;
  const su = await db.superuser();
  try {
    await su.query('REVOKE SELECT ON credentials FROM soorma_env_app');
    await post(g.edge, '/environment-credentials/current/end', { credential: admin.credential }); // store
  } finally {
    await su.query('GRANT SELECT ON credentials TO soorma_env_app');
    await su.end();
  }
  // throttle.refused: the one permit held by a request waiting at S1.
  let open!: () => void;
  g.stub.hold = new Promise((r) => (open = r));
  const held = post(g.edge, '/environment-credentials/current/renewal', {
    credential: admin.credential,
  });
  for (let i = 0; i < 200 && g.stub.count('signInStatus') === 0; i++)
    await new Promise((r) => setTimeout(r, 5));
  const second = post(g.edge, '/environment-credentials', {});
  for (let i = 0; i < 200 && timers.pending.size === 0; i++)
    await new Promise((r) => setTimeout(r, 5));
  timers.fire();
  await second;
  g.stub.hold = undefined;
  open();
  await held;
  return secrets;
}

describe('TC-EHA-053, 054: logs carry no secret, and every event is emitted', () => {
  let g: Gateway;
  let secrets: string[];
  beforeAll(async () => {
    const timers = new ManualTimers();
    const requests = new Semaphore({
      permits: 1,
      waitMs: 1000,
      reason: 'requests',
      retryAfterSeconds: 5,
      timers,
    });
    g = await gateway(db, { requests });
    secrets = await everyFlow(g, timers);
    // U5's flows too (D-CG-AR-17): every line and event below now also covers them.
    secrets.push(...(await registrationFlows(g)));
  });
  afterAll(async () => {
    await g?.close();
  });

  it('no token, sign-in id, or principal identifier appears in any line, whole or in part', () => {
    const all = g.log.lines.join('\n');
    for (const secret of secrets) {
      expect(all, secret.slice(0, 12)).not.toContain(secret);
      if (secret.length > 40) expect(all).not.toContain(secret.slice(10, 40));
    }
    expect(all).not.toMatch(/soorma_(si|ec)_/);
    expect(all).not.toMatch(/@example\.com/);
  });

  it('every event naming a human carries an hp_ pseudonym', () => {
    for (const e of g.log.events())
      if ('pseudonym' in e) expect(e.pseudonym).toMatch(/^hp_[A-Za-z0-9_-]{22}$/);
  });

  it('each of the ten events was emitted by its flow', () => {
    const emitted = new Set(g.log.events().map((e) => e.event));
    for (const event of SECURITY_EVENTS) expect(emitted, event).toContain(event);
  });
});

describe("NFR-EHA-19: S2's source emits exactly its ten events, and U5's four", () => {
  it('each listed event is named in the source, and the list is the ten and the four', () => {
    expect([...SECURITY_EVENTS].sort()).toEqual(
      [
        // U5's four (D-CG-AR-17; NFR-AR-18)
        'registration.created',
        'registration.refused',
        'secret.issued',
        'secret.refused',
        'credential.ended',
        'credential.issued',
        'credential.refused',
        'credential.renewed',
        'first_grant.applied',
        'grant.denied',
        'grant.made',
        'orglevel.unavailable',
        'store.unavailable',
        'throttle.refused',
      ].sort(),
    );
    const dir = join(import.meta.dirname, '../src');
    const files = readdirSync(dir, { recursive: true, encoding: 'utf8' }).filter(
      (f) => f.endsWith('.ts') && f !== 'security-log.ts',
    );
    const source = files.map((f) => readFileSync(join(dir, f), 'utf8')).join('\n');
    for (const event of SECURITY_EVENTS) expect(source, event).toContain(`'${event}'`);
  });
});
