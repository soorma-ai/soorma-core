// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TOTP (RFC 6238; P-12; NFR-OI-07, 08): HMAC-SHA-1, 6 digits, a 30-second
// step, one step of drift either side. A seed is 160 bits from the CSPRNG
// (NFR-OI-09). Each code is accepted at most once: the caller stores the last
// accepted step and accepts a step only when it is later (a conditional update
// in the store, so two concurrent uses of one code cannot both succeed).
import { createHmac, randomBytes } from 'node:crypto';
import {
  asSecretBytes,
  asTotpCode,
  secretEqual,
  type SecretBytes,
  type TotpCode,
} from './secret-types.ts';

export const TOTP_STEP_SECONDS = 30;
export const TOTP_DIGITS = 6;
export const TOTP_DRIFT_STEPS = 1;
export const TOTP_SEED_BYTES = 20;

export function newSeed(): SecretBytes {
  return asSecretBytes(randomBytes(TOTP_SEED_BYTES));
}

/** The step a time falls in. */
export function stepAt(time: Date): number {
  return Math.floor(time.getTime() / 1000 / TOTP_STEP_SECONDS);
}

/** RFC 4226 HOTP over the step counter, RFC 6238's TOTP with HMAC-SHA-1. */
export function codeAt(seed: SecretBytes, step: number, digits: number = TOTP_DIGITS): TotpCode {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(step));
  const mac = createHmac('sha1', seed).update(counter).digest();
  const offset = mac[mac.length - 1]! & 0x0f;
  const binary = mac.readUInt32BE(offset) & 0x7fffffff;
  return asTotpCode(String(binary % 10 ** digits).padStart(digits, '0'));
}

/**
 * The step a presented code matches, within one step of drift and later than
 * `lastAcceptedStep`; undefined when none does. Every candidate step is
 * compared, in constant time, so the time taken does not say which matched.
 */
export function matchStep(
  seed: SecretBytes,
  code: TotpCode,
  now: Date,
  lastAcceptedStep: number | null,
): number | undefined {
  const current = stepAt(now);
  let matched: number | undefined;
  for (let step = current - TOTP_DRIFT_STEPS; step <= current + TOTP_DRIFT_STEPS; step++) {
    const equal = secretEqual(codeAt(seed, step), code);
    if (equal && matched === undefined && (lastAcceptedStep === null || step > lastAcceptedStep))
      matched = step;
  }
  return matched;
}

/** RFC 4648 Base32, unpadded, as authenticator apps read it. */
export function base32(bytes: Buffer): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0;
  let value = 0;
  let out = '';
  for (const byte of bytes) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += alphabet[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) out += alphabet[(value << (5 - bits)) & 31];
  return out;
}

/** The Key URI authenticator apps read (D-CG-OI-08), each part percent-encoded. */
export function otpauthUri(seed: SecretBytes, organization: string, principal: string): string {
  const label = `soorma:${encodeURIComponent(organization)}:${encodeURIComponent(principal)}`;
  return (
    `otpauth://totp/${label}?secret=${base32(seed)}&issuer=soorma` +
    `&algorithm=SHA1&digits=${TOTP_DIGITS}&period=${TOTP_STEP_SECONDS}`
  );
}
