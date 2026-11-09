// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P10 wired for tests: a test database, the real abuse bound and identity
// resolution, the real hasher and policy, a controllable clock, and a failure
// recorder that captures what would be queued. Shared by the package's and
// the service's tests.
import { generateKeyPairSync, randomBytes } from 'node:crypto';
import { resolve } from 'node:path';
import { AbuseBound } from '../../../abuse-bound/src/index.ts';
import { StoreIdentityResolver } from '../../../identity-resolution/src/index.ts';
import {
  asSecretText,
  BreachedList,
  HashSemaphore,
  KeyRing,
  Lifetimes,
  OrgIdentity,
  SecretHasher,
  SecretPolicy,
  type Argon2id,
  type Clock,
  type FailureRecorder,
} from '../../src/index.ts';
import type { TestDatabase } from './database.ts';

export class TestClock implements Clock {
  ms: number;
  constructor(iso = '2026-11-08T12:00:00Z') {
    this.ms = Date.parse(iso);
  }
  now(): Date {
    return new Date(this.ms);
  }
  advance(seconds: number): void {
    this.ms += seconds * 1000;
  }
}

export type RecordedAttempt = Parameters<FailureRecorder['record']>[0];

export class CapturingRecorder implements FailureRecorder {
  readonly records: RecordedAttempt[] = [];
  record(attempt: RecordedAttempt): void {
    this.records.push(attempt);
  }
}

export const BREACHED_DIR = resolve(import.meta.dirname, '../../../../data/breached');
let breached: BreachedList | undefined;
export function breachedList(): BreachedList {
  breached ??= BreachedList.load(BREACHED_DIR);
  return breached;
}

export function testKeys(): KeyRing {
  return KeyRing.fromConfiguration({
    signingKey: Buffer.from(
      generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' }),
    ),
    verifyKeys: [],
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers: [],
  });
}

export interface Domain {
  identity: OrgIdentity;
  clock: TestClock;
  failures: CapturingRecorder;
  keys: KeyRing;
  hasher: SecretHasher;
  bound: AbuseBound;
}

export async function testDomain(
  db: TestDatabase,
  options: {
    organization?: string;
    secondFactorRequired?: boolean;
    clock?: TestClock;
    keys?: KeyRing;
    argon2id?: Argon2id;
  } = {},
): Promise<Domain> {
  const clock = options.clock ?? new TestClock();
  const keys = options.keys ?? testKeys();
  const failures = new CapturingRecorder();
  const hasher = new SecretHasher(new HashSemaphore(8), options.argon2id);
  await hasher.prepareDecoy();
  const bound = new AbuseBound(db.store, keys.counterSecret, clock);
  const identity = new OrgIdentity({
    organization: options.organization ?? 'o1',
    secondFactorRequired: options.secondFactorRequired ?? false,
    store: db.store,
    bound,
    failures,
    resolver: new StoreIdentityResolver(db.store, hasher, keys, clock),
    hasher,
    policy: new SecretPolicy(breachedList()),
    keys,
    lifetimes: new Lifetimes(clock),
    clock,
  });
  return { identity, clock, failures, keys, hasher, bound };
}

export const enrollmentMaterial = (): string =>
  `soorma_em_${randomBytes(32).toString('base64url')}`;

export { asSecretText };
