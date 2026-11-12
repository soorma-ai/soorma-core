// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-069's key half (D-AC-03; Infrastructure Design §11): rotating E's
// agent key keeps every token the old key signed verifying until its own
// expiry, while new tokens are signed with the new key; once the old key is
// removed from `keys.verify`, its tokens are refused.
import { generateKeyPairSync } from 'node:crypto';
import { loadEnvironmentKeyRing } from '@soorma/credentials';
import { asSecretBytes } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  testEnvDatabase,
  type TestEnvDatabase,
} from '../../../packages/env-store/test/harness/database.ts';
import {
  agentId,
  bootstrap,
  decoded,
  gateway,
  MINUTE,
  problem,
  registered,
  renew,
  TestClock,
  type Gateway,
} from './support.ts';

const pem = () =>
  asSecretBytes(
    Buffer.from(generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' })),
  );

let db: TestEnvDatabase;
const open: Gateway[] = [];
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  for (const g of open) await g.close();
  await db?.drop();
});

describe('TC-AC-069: a key rotation keeps old tokens verifying until their expiry', () => {
  it('the three steps: add, switch, then remove after the lifetime', async () => {
    const k1 = pem();
    const k2 = pem();
    const clock = new TestClock();
    const at = async (keys: { name: string; pem: typeof k1 }[], signing: string) => {
      const g = await gateway(db, {
        clock,
        ring: loadEnvironmentKeyRing({ signing, verify: keys }),
      });
      open.push(g);
      return g;
    };
    // Before: k1 alone.
    const before = await at([{ name: 'k1', pem: k1 }], 'k1');
    const agent = agentId();
    const secret = await registered(before, agent);
    const old = (await bootstrap(before, agent, secret.value)).body.credential as string;
    // Step 1: k2 added to verify; k1 still signs.
    const step1 = await at(
      [
        { name: 'k1', pem: k1 },
        { name: 'k2', pem: k2 },
      ],
      'k1',
    );
    expect((await renew(step1, old)).status).toBe(200);
    // Step 2: k2 signs. The old token still renews; the new token is k2's.
    const step2 = await at(
      [
        { name: 'k1', pem: k1 },
        { name: 'k2', pem: k2 },
      ],
      'k2',
    );
    clock.advance(5 * MINUTE);
    const renewed = await renew(step2, old);
    expect(renewed.status).toBe(200);
    expect(decoded(renewed.body.credential as string).header.kid).not.toBe(decoded(old).header.kid);
    // Step 3, too early: k1 removed while its token is unexpired would refuse it.
    const step3 = await at([{ name: 'k2', pem: k2 }], 'k2');
    expect(problem(await renew(step3, old))).toEqual({ status: 401, code: 'credential_refused' });
    // And the token k2 signed renews there.
    expect((await renew(step3, renewed.body.credential as string)).status).toBe(200);
  });
});
