// SPDX-License-Identifier: FSL-1.1-ALv2
//
// K and enrollment material, stored only as Argon2id verifiers (NFR-OI-11;
// BR-K-08), through Node's built-in crypto.argon2 (Q-CG-1 A: treated as
// Stable; a test fails if Node ever emits an ExperimentalWarning for it).
//
// - Input: the UTF-8 encoding of the NFKC-normalized secret, whole, never
//   truncated
// - The verifier is a PHC string that records the algorithm and parameters,
//   so they can be raised later without a reset
// - Every operation holds a hashing permit (P-09)
// - The decoy verifier (P-10) is computed once, with the same parameters, and
//   verified against whenever the principal or its material is absent, so the
//   work done does not depend on existence (BR-RF-03)
import { argon2, randomBytes, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import type { HashSemaphore } from './hash-semaphore.ts';
import { asSecretText, asVerifier, type SecretText, type Verifier } from './secret-types.ts';

const argon2Async = promisify(argon2);

/** The Argon2id primitive's parameters, as crypto.argon2 takes them. */
export interface Argon2Call {
  message: Buffer;
  nonce: Buffer;
  memory: number;
  passes: number;
  parallelism: number;
  tagLength: number;
}

/** The primitive itself: Node's crypto.argon2('argon2id', …). Tests may record calls to it. */
export type Argon2id = (parameters: Argon2Call) => Promise<Buffer>;

export const nodeArgon2id: Argon2id = (parameters) => argon2Async('argon2id', parameters);

export interface Argon2Parameters {
  /** KiB. */
  memory: number;
  passes: number;
  parallelism: number;
  tagLength: number;
  saltLength: number;
}

/** NFR-OI-11: the parameters of every verifier the organization level writes. */
export const ARGON2_PARAMETERS: Readonly<Argon2Parameters> = {
  /** KiB: 64 MiB. */
  memory: 65536,
  passes: 3,
  parallelism: 1,
  tagLength: 32,
  saltLength: 16,
};

interface Parsed {
  memory: number;
  passes: number;
  parallelism: number;
  salt: Buffer;
  tag: Buffer;
}

const PHC = /^\$argon2id\$v=19\$m=(\d+),t=(\d+),p=(\d+)\$([A-Za-z0-9+/]+)\$([A-Za-z0-9+/]+)$/;

function unpadded(bytes: Buffer): string {
  return bytes.toString('base64').replace(/=+$/, '');
}

function parse(verifier: Verifier): Parsed | undefined {
  const m = PHC.exec(verifier);
  if (!m) return undefined;
  return {
    memory: Number(m[1]),
    passes: Number(m[2]),
    parallelism: Number(m[3]),
    salt: Buffer.from(m[4]!, 'base64'),
    tag: Buffer.from(m[5]!, 'base64'),
  };
}

/** The bytes hashed: the UTF-8 of the NFKC-normalized secret, whole. */
export function secretInput(secret: SecretText): Buffer {
  return Buffer.from(secret.normalize('NFKC'), 'utf8');
}

export class SecretHasher {
  private readonly semaphore: HashSemaphore;
  private readonly argon2id: Argon2id;
  readonly parameters: Readonly<Argon2Parameters>;
  private decoy: Verifier | undefined;

  /**
   * `parameters` defaults to NFR-OI-11's, which production never overrides.
   * Only tests that do not measure hashing pass a cheaper profile.
   */
  constructor(
    semaphore: HashSemaphore,
    argon2id: Argon2id = nodeArgon2id,
    parameters: Readonly<Argon2Parameters> = ARGON2_PARAMETERS,
  ) {
    this.semaphore = semaphore;
    this.argon2id = argon2id;
    this.parameters = parameters;
  }

  /** Hashes a secret into a new verifier, with a fresh 16-byte salt. */
  async hash(secret: SecretText): Promise<Verifier> {
    const salt = randomBytes(this.parameters.saltLength);
    const { memory, passes, parallelism, tagLength } = this.parameters;
    const tag = await this.semaphore.run(() =>
      this.argon2id({
        message: secretInput(secret),
        nonce: salt,
        memory,
        passes,
        parallelism,
        tagLength,
      }),
    );
    const params = `m=${memory},t=${passes},p=${parallelism}`;
    return asVerifier(['', 'argon2id', 'v=19', params, unpadded(salt), unpadded(tag)].join('$'));
  }

  /** True only when `secret` matches `verifier`. A malformed verifier never matches. */
  async verify(secret: SecretText, verifier: Verifier): Promise<boolean> {
    const parsed = parse(verifier);
    if (!parsed) return false;
    const tag = await this.semaphore.run(() =>
      this.argon2id({
        message: secretInput(secret),
        nonce: parsed.salt,
        memory: parsed.memory,
        passes: parsed.passes,
        parallelism: parsed.parallelism,
        tagLength: parsed.tag.length,
      }),
    );
    return tag.length === parsed.tag.length && timingSafeEqual(tag, parsed.tag);
  }

  /** Computes the decoy verifier once, at start-up (P-10). */
  async prepareDecoy(): Promise<void> {
    this.decoy = await this.hash(asSecretText(randomBytes(32).toString('base64url')));
  }

  /**
   * Does the same work as a real verification, against the decoy, and always
   * fails. Used when the principal or the presented class's material is absent.
   */
  async verifyDecoy(secret: SecretText): Promise<false> {
    if (!this.decoy) throw new Error('the decoy verifier is computed at start-up');
    await this.verify(secret, this.decoy);
    return false;
  }
}
