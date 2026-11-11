// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The K policy (BR-K-01 to 07; NFR-OI-14). Checked on the NFKC form, in this
// order, and the first rule broken is the reason:
//   too_short, too_long        8 to 256 code points after normalization
//   disallowed_character       no Unicode Cc character
//   context_word               no principal identifier, organization
//                              identifier, or "soorma", case-folded; only
//                              words of 4 or more characters are matched
//   breached                   not on the breached-secret list
//   reused                     not the material it replaces
// No composition rule (BR-K-04). The caller runs it only after the presented
// material verified (BR-RF-04), and returns `secret_rejected` with one
// errors[] entry carrying the field's pointer and this reason (BR-K-07).
import {
  asSecretText,
  type PrincipalReference,
  secretEqual,
  type SecretText,
} from '@soorma/service-kit';
import type { BreachedList } from './breached-list.ts';

export const K_MIN_CODE_POINTS = 8;
export const K_MAX_CODE_POINTS = 256;
export const CONTEXT_WORD_MIN_LENGTH = 4;
const PRODUCT_WORD = 'soorma';
const CONTROL = /\p{Cc}/u;

/** The reasons U2 emits; the contract's SecretRejectedReason is open to more. */
export type SecretRejection =
  'too_short' | 'too_long' | 'disallowed_character' | 'context_word' | 'breached' | 'reused';

export type PolicyResult =
  { accepted: true; secret: SecretText } | { accepted: false; reason: SecretRejection };

export interface PolicyContext {
  reference: PrincipalReference;
  /** The material the new K replaces, as presented: the current K, or the enrollment material. */
  replaces: SecretText;
}

function fold(value: string): string {
  return value.normalize('NFKC').toLowerCase();
}

export class SecretPolicy {
  private readonly breached: BreachedList;

  constructor(breached: BreachedList) {
    this.breached = breached;
  }

  /** Checks a new K. On acceptance, returns its NFKC form, which is what is hashed. */
  check(candidate: SecretText, context: PolicyContext): PolicyResult {
    const secret = asSecretText(candidate.normalize('NFKC'));
    const length = [...secret].length;
    if (length < K_MIN_CODE_POINTS) return { accepted: false, reason: 'too_short' };
    if (length > K_MAX_CODE_POINTS) return { accepted: false, reason: 'too_long' };
    if (CONTROL.test(secret)) return { accepted: false, reason: 'disallowed_character' };
    const folded = fold(secret);
    const words = [context.reference.principal, context.reference.organization, PRODUCT_WORD]
      .map(fold)
      .filter((w) => [...w].length >= CONTEXT_WORD_MIN_LENGTH);
    if (words.some((w) => folded.includes(w))) return { accepted: false, reason: 'context_word' };
    if (this.breached.has(secret)) return { accepted: false, reason: 'breached' };
    if (secretEqual(secret, asSecretText(context.replaces.normalize('NFKC'))))
      return { accepted: false, reason: 'reused' };
    return { accepted: true, secret };
  }
}
