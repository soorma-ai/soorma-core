// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Refusals, returned and never thrown (U3 D-AE-11; D-CG-AE-05). A refusal is
// a contract code (a code in P1's table) and an internal reason. The reason
// goes to the security log only, never into a response (BR-RF-01). Field
// errors are for steps 5 and 6 only (BR-DV-03; BR-VR-04).

/** Every contract code U3 can return (BR-RF-03: all in P1's table). */
export type RefusalCode =
  | 'malformed_request'
  | 'unsupported_contract_version'
  | 'stamped_field_set'
  | 'unknown_field'
  | 'invalid_inbound_context'
  | 'chain_too_deep'
  | 'forbidden'
  | 'unavailable'
  | 'envelope_too_large'
  // U7 (D-CG-ET-18): a Body Form member over its bound, at step 6
  | 'payload_too_large'
  | 'internal_error';

/** The internal reasons, a closed list (business-rules §10). */
export type RefusalReason =
  // Step 5
  | 'body_not_object'
  | 'version_missing'
  | 'version_not_accepted'
  | 'version_header_mismatch'
  // Step 6
  | 'stamped_field'
  | 'unknown_field'
  | 'schema'
  | 'trace_context'
  // Step 6, a Body Form member (U7 D-CG-ET-18, 20): not measurable, or over its bound
  | 'member_invalid'
  | 'member_too_large'
  // Step 7
  | 'jcs_invalid'
  | 'inbound_too_large'
  | 'seal_failed'
  | 'envelope_version'
  | 'scope_mismatch'
  | 'rebroadening_index'
  // Step 8
  | 'chain_depth'
  // Step 9
  | 'o12_undeclared'
  | 'origin_unsupported'
  | 'presenter_unresolved'
  | 'human_only_permission'
  | 'upstream_unresolved'
  | 'authority_denied'
  | 'agent_facts_read_failed'
  // Step 10
  | 'envelope_bound'
  // Invariant breaches
  | 'credential_scope_mismatch'
  | 'empty_required_set';

/** A field error: a JSON Pointer into the body, or a request header. Never a value. */
export interface FieldError {
  readonly pointer?: string;
  readonly header?: string;
  readonly detail?: string;
}

export interface Refusal {
  readonly code: RefusalCode;
  readonly reason: RefusalReason;
  readonly errors?: readonly FieldError[];
  readonly retryAfterSeconds?: number;
}

export type Result<T> =
  { readonly ok: true; readonly value: T } | { readonly ok: false; readonly refusal: Refusal };

export function ok<T>(value: T): Result<T> {
  return { ok: true, value };
}

export function refuse<T>(
  code: RefusalCode,
  reason: RefusalReason,
  errors?: readonly FieldError[],
): Result<T> {
  return { ok: false, refusal: errors ? { code, reason, errors } : { code, reason } };
}

/** Field errors ordered by pointer, then header (BR-DV-03). */
export function byPointer(errors: readonly FieldError[]): FieldError[] {
  const key = (e: FieldError): string => e.pointer ?? `￿${e.header ?? ''}`;
  return [...errors].sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0));
}

/** A plain JSON object: not null, not an array. */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** An own property only: never one reached through the prototype. */
export function own(value: Record<string, unknown>, key: string): unknown {
  return Object.hasOwn(value, key) ? value[key] : undefined;
}
