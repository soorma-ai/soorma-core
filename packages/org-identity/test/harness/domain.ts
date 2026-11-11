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
import { asSecretText, type Clock } from '@soorma/service-kit';
import {
  BreachedList,
  HashSemaphore,
  KeyRing,
  Lifetimes,
  OrgIdentity,
  SecretHasher,
  SecretPolicy,
  nodeArgon2id,
  type Argon2Call,
  type Argon2id,
  type FailureRecorder,
} from '../../src/index.ts';
import type { TestDatabase } from './database.ts';

/**
 * A cheap hashing profile for flow tests that do not measure hashing: same
 * algorithm and code path, 1 MiB and one pass. Tests of NFR-OI-11 itself, and
 * of TC-OI-029 and 062, pass `realHashing: true`.
 */
export const FAST_ARGON2 = {
  memory: 1024,
  passes: 1,
  parallelism: 1,
  tagLength: 32,
  saltLength: 16,
};

/**
 * TC-OI-029's recording test double for the Argon2id primitive: it records
 * each call's parameters exactly as the hasher passed them (the real ones,
 * which the test asserts), then computes with FAST_ARGON2, so hashing and
 * verification through it agree, cheaply.
 */
export function recordingArgon2id(calls: Argon2Call[]): Argon2id {
  return (parameters) => {
    calls.push({ ...parameters });
    const { memory, passes, parallelism } = FAST_ARGON2;
    return nodeArgon2id({ ...parameters, memory, passes, parallelism });
  };
}

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

export function testKeys(
  internalCallers: { environment: string; publicKeys: Buffer[] }[] = [],
): KeyRing {
  return KeyRing.fromConfiguration({
    signingKey: Buffer.from(
      generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' }),
    ),
    verifyKeys: [],
    seedKeys: { current: 's1', keys: [{ id: 's1', key: randomBytes(32) }] },
    counterSecret: randomBytes(32),
    logPseudonymKey: randomBytes(32),
    internalCallers,
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
    semaphore?: HashSemaphore;
    store?: TestDatabase['store'];
    failures?: CapturingRecorder;
    realHashing?: boolean;
  } = {},
): Promise<Domain> {
  const clock = options.clock ?? new TestClock();
  const keys = options.keys ?? testKeys();
  const failures = options.failures ?? new CapturingRecorder();
  const hasher = new SecretHasher(
    options.semaphore ?? new HashSemaphore(8),
    options.argon2id,
    options.realHashing ? undefined : FAST_ARGON2,
  );
  await hasher.prepareDecoy();
  const store = options.store ?? db.store;
  const bound = new AbuseBound(store, keys.counterSecret, clock);
  const identity = new OrgIdentity({
    organization: options.organization ?? 'o1',
    secondFactorRequired: options.secondFactorRequired ?? false,
    store,
    bound,
    failures,
    resolver: new StoreIdentityResolver(store, hasher, keys, clock),
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
