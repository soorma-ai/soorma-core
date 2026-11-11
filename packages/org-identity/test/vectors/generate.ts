// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U3's guard on U2's canonical JSON (U3 NFR Design NP-03, step 1). Run ONCE,
// against U2's own canonicalJson, before U3 replaces its body with a wrapper
// over @soorma/jcs. It writes the literal outputs of the current code:
//
//   canonical-vectors.json  referenceJson's UTF-8 bytes; each reference's log
//                           pseudonym under a fixed key; its attempt slot under
//                           a fixed counter secret; the seed associated data's
//                           bytes for (reference, record id) pairs
//   seed-fixture.json       a seed encrypted by the current encryptSeed
//
// It is never run again: it refuses to overwrite either file. The committed
// files, not this script, are the reference; canonical-vectors.test.ts checks
// the code against them, unchanged, after the swap.
//
// The slot is computed here by P8's documented formula (abuse-bound.ts,
// slotOf: HMAC-SHA-256 over referenceJson, the last four bytes big-endian,
// mod 2^20), because P8 imports P10's index, whose NestJS decorators Node's
// type stripping cannot run. The test asserts the committed slots with the
// real slotOf, so the two agree on the current code or the guard fails.
//
// Every key below is labelled test material, used nowhere else.
//
//   node packages/org-identity/test/vectors/generate.ts
import { createHmac, generateKeyPairSync } from 'node:crypto';
import { existsSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  asSecretBytes,
  type PrincipalReference,
  pseudonym,
  referenceJson,
} from '@soorma/service-kit';
import { KeyRing } from '../../src/crypto/key-ring.ts';
import { associatedData, encryptSeed } from '../../src/crypto/seed-cipher.ts';

const here = dirname(fileURLToPath(import.meta.url));
const VECTORS = join(here, 'canonical-vectors.json');
const FIXTURE = join(here, 'seed-fixture.json');

/** 32 bytes counting up from `start`: fixed, labelled test keys. */
const testKey = (start: number): Buffer =>
  Buffer.from(Array.from({ length: 32 }, (_, i) => start + i));

const LOG_PSEUDONYM_KEY = testKey(0x00);
const COUNTER_SECRET = testKey(0x20);
const SEED_KEY = testKey(0x40);
const SEED_KEY_ID = 'fixture-1';
const SEED = Buffer.from(Array.from({ length: 20 }, (_, i) => 0xa0 + i));

const SPECIALS = "!#$%&'*+/=?^_`{|}~.@:-";
const references: PrincipalReference[] = [
  { organization: 'o1', principal: 'h@example.com' },
  { organization: 'o1', principal: "o'brien@example.com" },
  { organization: 'acme', principal: 'a/b|c@d+e:f.g' },
  { organization: 'o1', principal: `x${SPECIALS}` },
  { organization: 'o1', principal: 'x' },
  { organization: 'o1', principal: "q'/|@+:.".repeat(40).slice(0, 256) },
  { organization: 'O1._~-'.repeat(11).slice(0, 64), principal: 'h@example.com' },
  { organization: 'Org.Two', principal: 'MiXeD.Case+1@Example.COM' },
  { organization: 'o-3', principal: 'a:b:c' },
];

const seedPairs: { reference: PrincipalReference; recordId: string }[] = [
  { reference: references[0]!, recordId: '6f1c2b3a-4d5e-4f60-8172-93a4b5c6d7e8' },
  { reference: references[1]!, recordId: '00000000-0000-4000-8000-000000000000' },
  { reference: references[2]!, recordId: 'ffffffff-ffff-4fff-bfff-ffffffffffff' },
  { reference: references[5]!, recordId: '0f8fad5b-d9cb-469f-a165-70867728950e' },
];

/** P8's slotOf, by its documented formula (see the header). */
function slot(reference: PrincipalReference): number {
  const mac = createHmac('sha256', COUNTER_SECRET)
    .update(referenceJson(reference), 'utf8')
    .digest();
  return mac.readUInt32BE(mac.length - 4) % 2 ** 20;
}

for (const path of [VECTORS, FIXTURE])
  if (existsSync(path))
    throw new Error(`${path} exists: the vectors are written once, never regenerated`);

const vectors = {
  $comment:
    "U3 NP-03 step 1: the outputs of U2's canonicalJson before the swap, written once by generate.ts. Test material only.",
  keys: {
    logPseudonymKeyHex: LOG_PSEUDONYM_KEY.toString('hex'),
    counterSecretHex: COUNTER_SECRET.toString('hex'),
  },
  references: references.map((reference) => ({
    ...reference,
    referenceJsonHex: Buffer.from(referenceJson(reference), 'utf8').toString('hex'),
    pseudonym: pseudonym(reference, asSecretBytes(LOG_PSEUDONYM_KEY)),
    slot: slot(reference),
  })),
  seedAssociatedData: seedPairs.map(({ reference, recordId }) => ({
    ...reference,
    recordId,
    bytesHex: associatedData(reference, recordId).toString('hex'),
  })),
};

const signing = generateKeyPairSync('ed25519');
const keys = KeyRing.fromConfiguration({
  signingKey: Buffer.from(signing.privateKey.export({ format: 'pem', type: 'pkcs8' })),
  verifyKeys: [],
  seedKeys: { current: SEED_KEY_ID, keys: [{ id: SEED_KEY_ID, key: SEED_KEY }] },
  counterSecret: COUNTER_SECRET,
  logPseudonymKey: LOG_PSEUDONYM_KEY,
  internalCallers: [],
});
const fixtureReference = references[0]!;
const fixtureRecordId = seedPairs[0]!.recordId;
const fixture = {
  $comment:
    "U3 NP-03 step 1: a seed encrypted by U2's encryptSeed before the swap, written once by generate.ts. Test material only.",
  seedKeyId: SEED_KEY_ID,
  seedKeyHex: SEED_KEY.toString('hex'),
  reference: fixtureReference,
  recordId: fixtureRecordId,
  stored: encryptSeed(asSecretBytes(SEED), fixtureReference, fixtureRecordId, keys),
  plaintextHex: SEED.toString('hex'),
};

writeFileSync(VECTORS, `${JSON.stringify(vectors, null, 2)}\n`);
writeFileSync(FIXTURE, `${JSON.stringify(fixture, null, 2)}\n`);
console.log(`wrote ${VECTORS}\nwrote ${FIXTURE}`);
