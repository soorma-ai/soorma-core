// SPDX-License-Identifier: FSL-1.1-ALv2
// P6's agent half (U6 NP-AC-08; D-AC-04, 19, 20): TC-AC-026 (it decides
// identity only), TC-AC-048 (the resolver's half: every rejection is the same
// `{ resolved: false }`), TC-AC-022 (an unsupported material type), with real
// secrets from U5's generator, on the test database as soorma_env_data.
import { connectEnvStore, newRecordId } from '@soorma/env-store';
import { generateRegistrationSecret } from '@soorma/registry';
import type { Store } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createAgentIdentityResolver, type AgentRejection } from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';
import { seedAgentRevocation } from '../../env-store/test/harness/seed.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const E2 = { organization: 'o1', project: 'p1', environment: 'e2' };
const T0 = new Date('2026-11-12T08:00:00Z');

let db: TestEnvDatabase;
let data: Store;
let owner: Awaited<ReturnType<TestEnvDatabase['migrator']>>;

beforeAll(async () => {
  db = await testEnvDatabase();
  data = connectEnvStore({
    ...db.settings,
    user: 'soorma_env_data',
    password: db.info.dataPassword,
  });
  owner = await db.migrator();
});
afterAll(async () => {
  await data?.close();
  await owner?.end();
  await db?.drop();
});

/** A registration in an environment, with one secret of the given state; returns its value. */
async function registered(env: typeof E, agent: string): Promise<{ value: string; id: string }> {
  await owner.query(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ($1, $2, $3, $4, 'h@example.com', '{}', '{}', '{}', true, $5, 'registered')`,
    [env.organization, env.project, env.environment, agent, T0],
  );
  const s = generateRegistrationSecret();
  await owner.query(
    `INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES ($1, $2, $3, $4, $5, 'h@example.com', $6, $7, 'active')`,
    [s.id, env.organization, env.project, env.environment, agent, s.digest, T0],
  );
  return { value: s.value, id: s.id };
}

function resolver() {
  const reasons: AgentRejection[] = [];
  return {
    reasons,
    r: createAgentIdentityResolver({ store: data, onRejected: (x) => reasons.push(x) }),
  };
}

describe('TC-AC-026: the agent half resolves identity, and decides nothing else', () => {
  it('a valid secret resolves to its registration and secret id', async () => {
    const agent = `a-${newRecordId()}`;
    const s = await registered(E, agent);
    const { r } = resolver();
    expect(await r.resolve('registrationSecret', { environment: E, agent }, s.value)).toEqual({
      resolved: true,
      registration: { environment: E, agent },
      secretId: s.id,
    });
  });

  it('a revoked agent still resolves: revocation is core’s, decided after the seam', async () => {
    const agent = `a-${newRecordId()}`;
    const s = await registered(E, agent);
    await seedAgentRevocation(owner, ['o1', 'p1', 'e'], agent, T0);
    const { r } = resolver();
    expect(
      (await r.resolve('registrationSecret', { environment: E, agent }, s.value)).resolved,
    ).toBe(true);
  });
});

describe('TC-AC-048 (the resolver half), TC-AC-022: every rejection is the same, with its reason told only to onRejected', () => {
  it('each cause gives { resolved: false } and its own reason', async () => {
    const agent = `a-${newRecordId()}`;
    const other = `b-${newRecordId()}`;
    const s = await registered(E, agent);
    const o = await registered(E, other);
    const e2 = await registered(E2, agent);
    await owner.query(`UPDATE registration_secrets SET digest = $1 WHERE id = $2`, [
      Buffer.alloc(32, 1),
      o.id,
    ]);
    const wrong = `${s.value.slice(0, -43)}${'A'.repeat(43)}`;
    const cases: [string, string, AgentRejection][] = [
      [agent, 'soorma_em_' + 'x'.repeat(40), 'unsupported_material'],
      [agent, 'no-prefix-at-all', 'unsupported_material'],
      [agent, 'soorma_rs_short.value', 'malformed_secret'],
      [`nobody-${newRecordId()}`, s.value, 'unknown_registration'],
      [agent, o.value, 'unknown_secret'],
      [agent, e2.value, 'unknown_secret'],
      [agent, wrong, 'secret_mismatch'],
    ];
    for (const [who, value, reason] of cases) {
      const { r, reasons } = resolver();
      expect(
        await r.resolve('registrationSecret', { environment: E, agent: who }, value),
        reason,
      ).toEqual({
        resolved: false,
      });
      expect(reasons, reason).toEqual([reason]);
    }
  });
});
