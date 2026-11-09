// SPDX-License-Identifier: FSL-1.1-ALv2
//
// RFC 8785 (JCS) serialization for the values this package keys on: objects
// of strings and safe integers. Keys are sorted by UTF-16 code units, and
// strings are serialized as ECMAScript's JSON.stringify does, which is what
// JCS specifies.
export type Canonical = string | number | { readonly [key: string]: Canonical };

export function canonicalJson(value: Canonical): string {
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number') {
    if (!Number.isSafeInteger(value)) throw new TypeError('only safe integers are serialized');
    return String(value);
  }
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k]!)}`).join(',')}}`;
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
