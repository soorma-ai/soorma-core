// SPDX-License-Identifier: FSL-1.1-ALv2
// The agent credential's record (U6 NP-AC-03; D-AC-14, 15; BR-RN-02, 06, 07;
// BR-CR-AC-06), on the test database as S3's role, soorma_env_data:
// TC-AC-050 (a token whose record is missing or names another instance),
// TC-AC-051 (concurrent renewals keep the later expiry), TC-AC-053 (an earlier
// token stays valid until its own exp), TC-AC-023 (the lineage cap, its store
// half). The direct revocation source over the same store: TC-AC-006's P5 half.
import { generateKeyPairSync } from 'node:crypto';
import { connectEnvStore, newRecordId, withTransaction } from '@soorma/env-store';
import { asSecretBytes, type Store } from '@soorma/service-kit';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  directRevocationSource,
  insertAgentCredential,
  lineageTimes,
  loadEnvironmentKeyRing,
  mintAgentCredential,
  readAgentCredential,
  renewAgentCredentialRecord,
  renewedExpiry,
  verifyAgentCredential,
} from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const T0 = new Date('2026-11-12T08:00:00Z');
const MINUTE = 60_000;
const at = (ms: number): Date => new Date(T0.getTime() + ms);

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

/** A registration with one active secret, as the owner; then a lineage at T0, as S3's role. */
async function lineage(): Promise<{ cid: string; agent: string }> {
  const agent = `a-${newRecordId()}`;
  const secret = newRecordId();
  await owner.query(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ('o1', 'p1', 'e', $1, 'h@example.com', '{}', '{}', '{}', true, $2, 'registered')`,
    [agent, T0],
  );
  await owner.query(
    `INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES ($1, 'o1', 'p1', 'e', $2, 'h@example.com', $3, $4, 'active')`,
    [secret, agent, Buffer.alloc(32), T0],
  );
  const cid = newRecordId();
  await withTransaction(data, (tx) =>
    insertAgentCredential(tx, {
      cid,
      environment: E,
      agent,
      instance: 'i-1',
      secret,
      ...lineageTimes(T0),
    }),
  );
  return { cid, agent };
}

describe('TC-AC-050: a token whose record is missing, or names another instance or agent, renews nothing', () => {
  it('no record, another instance, another agent: undefined, nothing written', async () => {
    const { cid, agent } = await lineage();
    const renew = (over: { cid?: string; agent?: string; instance?: string }) =>
      withTransaction(data, (tx) =>
        renewAgentCredentialRecord(tx, {
          cid,
          environment: E,
          agent,
          instance: 'i-1',
          expiresAt: at(25 * MINUTE),
          ...over,
        }),
      );
    expect(await renew({ cid: newRecordId() })).toBeUndefined();
    expect(await renew({ instance: 'i-2' })).toBeUndefined();
    expect(await renew({ agent: 'someone-else' })).toBeUndefined();
    expect((await readAgentCredential(data, cid, E))?.expiresAt).toEqual(at(15 * MINUTE));
  });
});

describe('TC-AC-051: concurrent renewals of one lineage all succeed; the record keeps the later expiry', () => {
  it('two renewals at once, with different expiries', async () => {
    const { cid, agent } = await lineage();
    const renew = (expiresAt: Date) =>
      withTransaction(data, (tx) =>
        renewAgentCredentialRecord(tx, { cid, environment: E, agent, instance: 'i-1', expiresAt }),
      );
    const [a, b] = await Promise.all([renew(at(25 * MINUTE)), renew(at(20 * MINUTE))]);
    expect(a).toBeDefined();
    expect(b).toBeDefined();
    expect((await readAgentCredential(data, cid, E))?.expiresAt).toEqual(at(25 * MINUTE));
  });
});

describe('TC-AC-023 (the store half): the record never expires past its lineage end', () => {
  it('renewal is capped by renewedExpiry, and the store refuses anything later', async () => {
    const { cid, agent } = await lineage();
    const rec = (await readAgentCredential(data, cid, E))!;
    expect(rec.lineageEndsAt).toEqual(at(24 * 60 * MINUTE));
    const capped = renewedExpiry(at(23 * 60 * MINUTE + 58 * MINUTE), rec.lineageEndsAt);
    expect(capped).toEqual(rec.lineageEndsAt);
    await withTransaction(data, (tx) =>
      renewAgentCredentialRecord(tx, {
        cid,
        environment: E,
        agent,
        instance: 'i-1',
        expiresAt: capped,
      }),
    );
    await expect(
      withTransaction(data, (tx) =>
        renewAgentCredentialRecord(tx, {
          cid,
          environment: E,
          agent,
          instance: 'i-1',
          expiresAt: at(24 * 60 * MINUTE + 1000),
        }),
      ),
    ).rejects.toMatchObject({
      name: 'ConflictError',
      constraint: 'agent_credentials_expiry_within_lineage',
    });
  });
});

describe('TC-AC-053: an earlier token of a lineage stays valid until its own exp', () => {
  it('after a renewal, the first token still verifies, and its record is the lineage’s', async () => {
    const { cid, agent } = await lineage();
    const { privateKey } = generateKeyPairSync('ed25519');
    const pem = asSecretBytes(Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })));
    const ring = loadEnvironmentKeyRing({ signing: 'k', verify: [{ name: 'k', pem }] });
    const claims = { environment: E, agent, instance: 'i-1', cid, issuedAt: T0 };
    const first = await mintAgentCredential(
      { ...claims, jti: 'j1', expiresAt: at(15 * MINUTE) },
      ring,
    );
    await withTransaction(data, (tx) =>
      renewAgentCredentialRecord(tx, {
        cid,
        environment: E,
        agent,
        instance: 'i-1',
        expiresAt: at(25 * MINUTE),
      }),
    );
    const v = await verifyAgentCredential(first, ring, E, at(12 * MINUTE));
    expect(v.ok && v.claims.cid).toBe(cid);
    expect(await readAgentCredential(data, cid, E)).toMatchObject({ agent, instance: 'i-1' });
  });
});

describe('TC-AC-006 (the P5 half): the direct source answers over the store, as S3’s role', () => {
  it('not revoked for a live lineage', async () => {
    const { cid, agent } = await lineage();
    expect(await directRevocationSource(data).isRevoked({ environment: E, cid, agent })).toBe(
      'not_revoked',
    );
  });
});
