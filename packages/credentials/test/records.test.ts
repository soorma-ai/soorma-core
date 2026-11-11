// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P5's records over a real environment store, as the app role: O3 (NP-EHA-01
// step 9), and the conditional renewal and end (NP-EHA-09).
import { newRecordId, withTransaction } from '@soorma/env-store';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  checkCredentialRecord,
  endCredential,
  insertCredential,
  readCredential,
  renewCredential,
  type CredentialClaims,
} from '../src/index.ts';
import { testEnvDatabase, type TestEnvDatabase } from '../../env-store/test/harness/database.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const E2 = { organization: 'o1', project: 'p1', environment: 'e2' };
const now = new Date('2026-11-11T12:00:00Z');
const later = new Date('2026-11-11T12:15:00Z');

let db: TestEnvDatabase;
beforeAll(async () => {
  db = await testEnvDatabase();
});
afterAll(async () => {
  await db?.drop();
});

async function live(environment = E, principal = 'h@example.com'): Promise<string> {
  const id = newRecordId();
  await withTransaction(db.store, (tx) =>
    insertCredential(tx, {
      id,
      environment,
      principal,
      issuedFrom: 'a'.repeat(32),
      issuedAt: now,
      expiresAt: later,
    }),
  );
  return id;
}

const claimsFor = (cid: string, over: Partial<CredentialClaims> = {}): CredentialClaims => ({
  environment: E,
  principal: 'h@example.com',
  cid,
  jti: newRecordId(),
  issuedAt: now,
  expiresAt: later,
  ...over,
});

describe('TC-EHA-014 (P5): O3 reads the record, uncached', () => {
  it('passes a live record naming the token subject', async () => {
    const id = await live();
    const r = await checkCredentialRecord(db.store, claimsFor(id));
    expect(r.ok).toBe(true);
  });

  it('refuses no record, another subject, an ended record, and a record of another environment', async () => {
    expect(await checkCredentialRecord(db.store, claimsFor(newRecordId()))).toEqual({
      ok: false,
      reason: 'no_record',
    });
    const id = await live();
    expect(
      await checkCredentialRecord(db.store, claimsFor(id, { principal: 'j@example.com' })),
    ).toEqual({ ok: false, reason: 'record_mismatch' });
    await withTransaction(db.store, (tx) =>
      endCredential(tx, { id, environment: E, endedAt: now }),
    );
    expect(await checkCredentialRecord(db.store, claimsFor(id))).toEqual({
      ok: false,
      reason: 'credential_ended',
    });
    const other = await live(E2);
    expect(await checkCredentialRecord(db.store, claimsFor(other))).toEqual({
      ok: false,
      reason: 'no_record',
    });
  });
});

describe('TC-EHA-030: renewal racing an end, and two concurrent ends, each commit exactly one outcome', () => {
  it('renew against end, 50 times: never renewed after the end won', async () => {
    for (let i = 0; i < 50; i++) {
      const id = await live();
      const renewed = new Date(later.getTime() + 60_000);
      const [r, e] = await Promise.all([
        withTransaction(db.store, (tx) =>
          renewCredential(tx, { id, environment: E, expiresAt: renewed }),
        ),
        withTransaction(db.store, (tx) => endCredential(tx, { id, environment: E, endedAt: now })),
      ]);
      expect(e).toBe(true); // the end always lands: the renewal leaves the row live
      const record = await readCredential(db.store, id, E);
      expect(record?.state).toBe('ended');
      if (r) expect(record?.expiresAt).toEqual(renewed);
    }
  });

  it('two concurrent ends, 50 times: exactly one succeeds', async () => {
    for (let i = 0; i < 50; i++) {
      const id = await live();
      const results = await Promise.all([
        withTransaction(db.store, (tx) => endCredential(tx, { id, environment: E, endedAt: now })),
        withTransaction(db.store, (tx) => endCredential(tx, { id, environment: E, endedAt: now })),
      ]);
      expect(results.filter(Boolean)).toHaveLength(1);
    }
  });

  it('a renewal after the end is refused (zero rows)', async () => {
    const id = await live();
    await withTransaction(db.store, (tx) =>
      endCredential(tx, { id, environment: E, endedAt: now }),
    );
    expect(
      await withTransaction(db.store, (tx) =>
        renewCredential(tx, { id, environment: E, expiresAt: later }),
      ),
    ).toBe(false);
  });
});
