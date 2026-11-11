// SPDX-License-Identifier: FSL-1.1-ALv2
//
// RFC 8785 (JCS) serialization for the values this package keys on: objects
// of strings and safe integers. Since U3 (NFR Design NP-03) the serialization
// is @soorma/jcs, the repository's one RFC 8785 implementation. This module
// keeps U2's narrower Canonical type and its safe-integer check. The bytes are
// pinned by test/canonical-vectors.test.ts, written from the code before the
// swap: the pseudonym, P8's attempt slot, and the seed associated data.
import { canonicalize } from '@soorma/jcs';

export type Canonical = string | number | { readonly [key: string]: Canonical };

/** U2's rule, kept: only safe integers are serialized. Checked without recursion. */
function checkNumbers(value: Canonical): void {
  const pending: Canonical[] = [value];
  while (pending.length > 0) {
    const v = pending.pop()!;
    if (typeof v === 'number') {
      if (!Number.isSafeInteger(v)) throw new TypeError('only safe integers are serialized');
    } else if (typeof v === 'object') pending.push(...Object.values(v));
  }
}

export function canonicalJson(value: Canonical): string {
  checkNumbers(value);
  return canonicalize(value).text;
}

/** A human principal reference: always composed with its organization (D-OI-21). */
export interface PrincipalReference {
  organization: string;
  principal: string;
}

/** The reference's RFC 8785 form, the input of every keyed hash over it. */
export function referenceJson(reference: PrincipalReference): string {
  return canonicalJson({ organization: reference.organization, principal: reference.principal });
}
