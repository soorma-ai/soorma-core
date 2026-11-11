// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The log pseudonym (NFR-OI-22, amended; P-17): how a log line names a human.
// `hp_` + base64url of the first 128 bits of HMAC-SHA-256, under the
// dedicated log-pseudonym key, over the reference's RFC 8785 form. No human
// identifier appears in a log; HumanPseudonym is the only type the log helper
// accepts for a human, and only this function produces it.
import { createHmac } from 'node:crypto';
import { referenceJson, type PrincipalReference } from './canonical.ts';
import type { SecretBytes } from './secret-types.ts';

declare const pseudonymBrand: unique symbol;

export type HumanPseudonym = string & { readonly [pseudonymBrand]: true };

export function pseudonym(reference: PrincipalReference, key: SecretBytes): HumanPseudonym {
  const mac = createHmac('sha256', key).update(referenceJson(reference), 'utf8').digest();
  return `hp_${mac.subarray(0, 16).toString('base64url')}` as HumanPseudonym;
}
