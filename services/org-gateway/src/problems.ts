// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Problems (RFC 9457) as S1 emits them (P-08; BR-ERR-08): every one carries
// type (urn:soorma:problem:{code}), title, status, code, and instance
// (urn:soorma:request:{request id}). Titles are generic. A 401 carries
// `WWW-Authenticate: Bearer`; a 403 never does (D-OI-13); a 429 and a 503
// carry `Retry-After`. Validation errors name the field; trust failures name
// nothing beyond their code (BR-ERR-01).
import type { FastifyReply } from 'fastify';

export const CONTRACT_VERSION = '0.1.0';
export const SUPPORTED_VERSIONS = [CONTRACT_VERSION] as const;

export type ProblemCode =
  | 'malformed_request'
  | 'unsupported_contract_version'
  | 'secret_rejected'
  | 'credential_refused'
  | 'credential_expired'
  | 'authentication_failed'
  | 'second_factor_enrollment_required'
  | 'second_factor_not_confirmed'
  | 'payload_too_large'
  | 'too_many_attempts'
  | 'unavailable'
  | 'internal_error';

const STATUS: Record<ProblemCode, number> = {
  malformed_request: 400,
  unsupported_contract_version: 400,
  secret_rejected: 400,
  credential_refused: 401,
  credential_expired: 401,
  authentication_failed: 403,
  second_factor_enrollment_required: 403,
  second_factor_not_confirmed: 403,
  payload_too_large: 413,
  too_many_attempts: 429,
  unavailable: 503,
  internal_error: 500,
};

const TITLE: Record<ProblemCode, string> = {
  malformed_request: 'Malformed request',
  unsupported_contract_version: 'Unsupported contract version',
  secret_rejected: 'Secret rejected',
  credential_refused: 'Credential refused',
  credential_expired: 'Credential expired',
  authentication_failed: 'Authentication failed',
  second_factor_enrollment_required: 'Second factor enrollment required',
  second_factor_not_confirmed: 'Second factor not confirmed',
  payload_too_large: 'Payload too large',
  too_many_attempts: 'Too many attempts',
  unavailable: 'Unavailable',
  internal_error: 'Internal error',
};

export interface FieldError {
  pointer?: string;
  header?: string;
  detail?: string;
  reason?: string;
}

export class ProblemError extends Error {
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
    return STATUS[this.code];
  }
}

export function problemBody(problem: ProblemError, requestId: string): Record<string, unknown> {
  return {
    type: `urn:soorma:problem:${problem.code}`,
    title: TITLE[problem.code],
    status: problem.status,
    code: problem.code,
    instance: `urn:soorma:request:${requestId}`,
    ...(problem.errors ? { errors: problem.errors } : {}),
    ...(problem.code === 'unsupported_contract_version'
      ? { supportedVersions: [...SUPPORTED_VERSIONS] }
      : {}),
  };
}

export function sendProblem(reply: FastifyReply, requestId: string, problem: ProblemError): void {
  if (problem.status === 401) void reply.header('WWW-Authenticate', 'Bearer');
  if (problem.status === 429 || problem.status === 503)
    void reply.header('Retry-After', String(Math.max(1, problem.retryAfterSeconds ?? 1)));
  void reply
    .status(problem.status)
    .header('Content-Type', 'application/problem+json; charset=utf-8')
    .send(JSON.stringify(problemBody(problem, requestId)));
}
