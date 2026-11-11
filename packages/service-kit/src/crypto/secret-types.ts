// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Branded types for secret values (D-CG-OI-05). A secret value carries one of
// these types from where it enters the process to where it is used, so:
// - the `compare` check (tools/checks) fails on `===` or `!==` when either
//   operand has one of these types: a secret is compared only by secretEqual
// - a function that takes a secret says so in its signature
// The brands exist only in the type system; at run time each value is a plain
// Buffer or string.
import { createHash, timingSafeEqual } from 'node:crypto';

declare const secretBytesBrand: unique symbol;
declare const verifierBrand: unique symbol;
declare const secretTextBrand: unique symbol;
declare const totpCodeBrand: unique symbol;

/** Key material: signing-key bytes, seed keys, the counter secret, the log-pseudonym key, TOTP seeds. */
export type SecretBytes = Buffer & { readonly [secretBytesBrand]: true };

/** A stored verifier: an Argon2id PHC string over K or enrollment material, or a derived tag. */
export type Verifier = string & { readonly [verifierBrand]: true };

/**
 * K or enrollment material, as presented or configured; and a bearer token, as
 * presented or as minted (U4 NP-EHA-14), so `===` on one fails the compare check.
 */
export type SecretText = string & { readonly [secretTextBrand]: true };

/** A presented or generated TOTP code. */
export type TotpCode = string & { readonly [totpCodeBrand]: true };

export const asSecretBytes = (value: Buffer): SecretBytes => value as SecretBytes;
export const asVerifier = (value: string): Verifier => value as Verifier;
export const asSecretText = (value: string): SecretText => value as SecretText;
export const asTotpCode = (value: string): TotpCode => value as TotpCode;

function digest(value: Buffer | string): Buffer {
  return createHash('sha256').update(value).digest();
}

/**
 * Compares two secret-derived values in constant time (NFR-OI-29). Each side is
 * reduced to its SHA-256 digest first, so the comparison is over equal lengths
 * and its time does not depend on either value's length.
 */
export function secretEqual(
  a: SecretBytes | Verifier | SecretText | TotpCode | Buffer,
  b: SecretBytes | Verifier | SecretText | TotpCode | Buffer,
): boolean {
  return timingSafeEqual(digest(a), digest(b));
}
