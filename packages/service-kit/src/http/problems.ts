// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Problems (RFC 9457) as soorma-core emits them: the one table and the one
// emission, framework-neutral (U3 D-AE-06, D-AE-25; BR-PE-01 to 04). Moved
// from S1 (services/org-gateway/src/problems.ts) with no change in behaviour;
// S1, and later S2, S3, and S4, keep only a thin adapter to their framework.
//
// - The table holds every code in contract/conventions/errors.md, with its
//   status and a generic title. A test checks it against the convention
// - Every Problem carries type (urn:soorma:problem:{code}), title, status,
//   code, and instance (urn:soorma:request:{request id}) (BR-ERR-08)
// - A 401 carries `WWW-Authenticate: Bearer`; a 403 never does (D-OI-13); a
//   429 and a 503 carry `Retry-After`, at least 1
// - Validation errors name the field or header; trust failures name nothing
//   beyond their code (BR-ERR-01)
// - The server's contract version and the accepted set are defined here, once
//   (D-AE-25)

export const CONTRACT_VERSION = '0.1.0';
export const SUPPORTED_VERSIONS: readonly string[] = Object.freeze([CONTRACT_VERSION]);

export type ProblemCode =
  | 'malformed_request'
  | 'unknown_field'
  | 'stamped_field_set'
  | 'invalid_inbound_context'
  | 'chain_too_deep'
  | 'envelope_too_large'
  | 'unsupported_contract_version'
  | 'secret_rejected'
  | 'unknown_permission'
  | 'unknown_principal'
  | 'human_only_permission'
  | 'declaration_outside_standing'
  | 'unknown_registration'
  | 'credential_refused'
  | 'credential_expired'
  | 'forbidden'
  | 'exceeds_sponsor_ceiling'
  | 'authentication_failed'
  | 'second_factor_enrollment_required'
  | 'second_factor_not_confirmed'
  | 'registration_exists'
  | 'secret_limit_reached'
  | 'payload_too_large'
  | 'too_many_attempts'
  | 'unavailable'
  | 'internal_error';

interface Entry {
  readonly status: number;
  readonly title: string;
}

/** The one Problem table: status and generic title per code (BR-PE-01). */
export const PROBLEM_TABLE: Readonly<Record<ProblemCode, Entry>> = Object.freeze({
  malformed_request: { status: 400, title: 'Malformed request' },
  unknown_field: { status: 400, title: 'Unknown field' },
  stamped_field_set: { status: 400, title: 'Stamped field set' },
  invalid_inbound_context: { status: 400, title: 'Invalid inbound context' },
  chain_too_deep: { status: 400, title: 'Chain too deep' },
  envelope_too_large: { status: 400, title: 'Envelope too large' },
  unsupported_contract_version: { status: 400, title: 'Unsupported contract version' },
  secret_rejected: { status: 400, title: 'Secret rejected' },
  unknown_permission: { status: 400, title: 'Unknown permission' },
  unknown_principal: { status: 400, title: 'Unknown principal' },
  human_only_permission: { status: 400, title: 'Human-only permission' },
  declaration_outside_standing: { status: 400, title: 'Declaration outside standing set' },
  unknown_registration: { status: 400, title: 'Unknown registration' },
  credential_refused: { status: 401, title: 'Credential refused' },
  credential_expired: { status: 401, title: 'Credential expired' },
  forbidden: { status: 403, title: 'Forbidden' },
  exceeds_sponsor_ceiling: { status: 403, title: 'Exceeds sponsor ceiling' },
  authentication_failed: { status: 403, title: 'Authentication failed' },
  second_factor_enrollment_required: { status: 403, title: 'Second factor enrollment required' },
  second_factor_not_confirmed: { status: 403, title: 'Second factor not confirmed' },
  registration_exists: { status: 409, title: 'Registration exists' },
  secret_limit_reached: { status: 409, title: 'Secret limit reached' },
  payload_too_large: { status: 413, title: 'Payload too large' },
  too_many_attempts: { status: 429, title: 'Too many attempts' },
  unavailable: { status: 503, title: 'Unavailable' },
  internal_error: { status: 500, title: 'Internal error' },
});

export function isProblemCode(code: string): code is ProblemCode {
  return Object.hasOwn(PROBLEM_TABLE, code);
}

export interface FieldError {
  pointer?: string;
  header?: string;
  detail?: string;
  reason?: string;
}

/** A refusal to emit: its code, any field errors, and any `Retry-After`. */
export interface Refusal {
  readonly code: ProblemCode;
  readonly errors?: readonly FieldError[] | undefined;
  readonly retryAfterSeconds?: number | undefined;
}

/** A refusal thrown by a surface's handler, emitted by its error handler. */
export class ProblemError extends Error implements Refusal {
  readonly code: ProblemCode;
  readonly errors: FieldError[] | undefined;
  readonly retryAfterSeconds: number | undefined;

  constructor(
    code: ProblemCode,
    options: { errors?: FieldError[]; retryAfterSeconds?: number } = {},
  ) {
    super(code);
    this.name = 'ProblemError';
    this.code = code;
    this.errors = options.errors;
    this.retryAfterSeconds = options.retryAfterSeconds;
  }

  get status(): number {
    return PROBLEM_TABLE[this.code].status;
  }
}

export interface ProblemResponse {
  readonly status: number;
  readonly headers: Readonly<Record<string, string>>;
  readonly body: Readonly<Record<string, unknown>>;
}

/** The Problem body (BR-ERR-08). */
export function problemBody(refusal: Refusal, requestId: string): Record<string, unknown> {
  const { status, title } = PROBLEM_TABLE[refusal.code];
  return {
    type: `urn:soorma:problem:${refusal.code}`,
    title,
    status,
    code: refusal.code,
    instance: `urn:soorma:request:${requestId}`,
    ...(refusal.errors ? { errors: refusal.errors.map((e) => ({ ...e })) } : {}),
    ...(refusal.code === 'unsupported_contract_version'
      ? { supportedVersions: [...SUPPORTED_VERSIONS] }
      : {}),
  };
}

/**
 * The whole response for a refusal, framework-neutral (BR-PE-02; D-CG-AE-04):
 * status, headers, and body. The headers include `Soorma-Contract-Version` and
 * `Soorma-Request-Id`, which every response carries, so the response is
 * complete on its own.
 */
export function problemResponse(refusal: Refusal, requestId: string): ProblemResponse {
  const { status } = PROBLEM_TABLE[refusal.code];
  const headers: Record<string, string> = {
    'Content-Type': 'application/problem+json; charset=utf-8',
    'Soorma-Contract-Version': CONTRACT_VERSION,
    'Soorma-Request-Id': requestId,
  };
  if (status === 401) headers['WWW-Authenticate'] = 'Bearer';
  if (status === 429 || status === 503)
    headers['Retry-After'] = String(Math.max(1, Math.ceil(refusal.retryAfterSeconds ?? 1)));
  return { status, headers, body: problemBody(refusal, requestId) };
}
