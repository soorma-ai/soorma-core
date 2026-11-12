// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The registration secret's format and verifier (U5 NFR-AR-01 to 05;
// NP-AR-02). One definition, imported by S2's issuance and U6's bootstrap,
// never copied. Pure: no store access.
//
// - The value is soorma_rs_{id}.{secret}: {id} the secret record's id (128
//   CSPRNG bits, base64url, 22 characters; env-store's newRecordId), {secret}
//   256 CSPRNG bits, base64url, 43 characters. No checksum. `.` is outside
//   the base64url alphabet, so the value parses with one split
// - One encoding per value: each part must decode to its exact length and
//   re-encode to the same characters, or the value is invalid
// - The stored verifier is unkeyed and fast: SHA-256 over a domain label, a
//   zero byte, and the 32 secret bytes. 256 random bits cannot be guessed or
//   reversed from a stolen row; never a slow password hash
// - Comparison is timingSafeEqual over two 32-byte buffers
// The value is a SecretText from generation to the response body; neither it
// nor the digest is ever logged (NFR-AR-04).
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { newRecordId } from '@soorma/env-store';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { asSecretText, type SecretText } from '@soorma/service-kit';

export const REGISTRATION_SECRET_PREFIX = 'soorma_rs_';
/** credentials.md: material is at most 256 characters. */
export const REGISTRATION_SECRET_MAX_LENGTH = 256;

const DIGEST_LABEL = Buffer.from('soorma.registration-secret.v1\0', 'utf8');
const ID_PART = /^[A-Za-z0-9_-]{22}$/;
const SECRET_PART = /^[A-Za-z0-9_-]{43}$/;

export interface GeneratedRegistrationSecret {
  /** The secret record's id, also the value's {id}. */
  readonly id: string;
  /** soorma_rs_{id}.{secret}: returned once, never stored. */
  readonly value: SecretText;
  /** The stored verifier: 32 bytes. */
  readonly digest: Buffer;
}

export type ParsedRegistrationSecret =
  | { readonly kind: 'parsed'; readonly id: string; readonly secretBytes: Buffer }
  | { readonly kind: 'invalid' };

/** SHA-256("soorma.registration-secret.v1" || 0x00 || secretBytes). */
export function digestRegistrationSecret(secretBytes: Buffer): Buffer {
  return createHash('sha256').update(DIGEST_LABEL).update(secretBytes).digest();
}

export function generateRegistrationSecret(): GeneratedRegistrationSecret {
  const id = newRecordId();
  const secretBytes = randomBytes(32);
  const value = asSecretText(
    `${REGISTRATION_SECRET_PREFIX}${id}.${secretBytes.toString('base64url')}`,
  );
  return { id, value, digest: digestRegistrationSecret(secretBytes) };
}

/** Exactly `bytes` bytes, in the one base64url encoding that produces `part`. */
function decodeExact(part: string, pattern: RegExp, bytes: number): Buffer | undefined {
  if (!pattern.test(part)) return undefined;
  const decoded = Buffer.from(part, 'base64url');
  if (decoded.length !== bytes || decoded.toString('base64url') !== part) return undefined;
  return decoded;
}

/** Parses a presented value; never throws for a malformed one (NFR-AR-03). */
export function parseRegistrationSecret(value: SecretText): ParsedRegistrationSecret {
  const text: string = value;
  if (text.length > REGISTRATION_SECRET_MAX_LENGTH) return { kind: 'invalid' };
  if (!text.startsWith(REGISTRATION_SECRET_PREFIX)) return { kind: 'invalid' };
  const parts = text.slice(REGISTRATION_SECRET_PREFIX.length).split('.');
  if (parts.length !== 2) return { kind: 'invalid' };
  const [idPart = '', secretPart = ''] = parts;
  const id = decodeExact(idPart, ID_PART, 16);
  const secretBytes = decodeExact(secretPart, SECRET_PART, 32);
  if (!id || !secretBytes) return { kind: 'invalid' };
  return { kind: 'parsed', id: idPart, secretBytes };
}

/** Recomputes the digest and compares in constant time; false for a stored digest not 32 bytes. */
export function registrationSecretMatches(secretBytes: Buffer, stored: Buffer): boolean {
  if (stored.length !== 32) return false;
  return timingSafeEqual(digestRegistrationSecret(secretBytes), stored);
}

const LOCK_LABEL = 'soorma.registration-secrets.v1';
const LOW_63_BITS = (1n << 63n) - 1n;

/**
 * The cap's advisory-lock key for one registration (NP-AR-03; D-CG-AR-08):
 * the first 63 bits of SHA-256(label || 0x00 || organization || 0x00 ||
 * project || 0x00 || environment || 0x00 || agent), as a decimal string for
 * pg_advisory_xact_lock($1::bigint). A collision only serialises two
 * registrations needlessly; it never admits an eleventh secret.
 */
export function registrationLockKey(environment: EnvironmentRef, agent: string): string {
  const hash = createHash('sha256')
    .update(
      [
        LOCK_LABEL,
        environment.organization,
        environment.project,
        environment.environment,
        agent,
      ].join('\0'),
      'utf8',
    )
    .digest();
  return (hash.readBigUInt64BE(0) & LOW_63_BITS).toString();
}
