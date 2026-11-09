// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The log helper (P-17; D-CG-OI-06; NFR-OI-22, 23). Structured JSON to stdout
// through NestJS's ConsoleLogger. It takes only:
//   - an event name from the fixed list
//   - the request id
//   - non-secret fields: a HumanPseudonym (a type only pseudonym() makes), a
//     count, a code, an environment
// It has no parameter for material, a token, or a principal identifier, so
// none can reach a log by mistake.
import { ConsoleLogger } from '@nestjs/common';
import type { HumanPseudonym } from '@soorma/org-identity';

export const SECURITY_EVENTS = [
  'auth.failed',
  'auth.bound_refused',
  'auth.second_factor_required',
  'signin.issued',
  'signin.ended',
  'material.changed',
  'failed_attempt.dropped',
  'internal.call_refused',
  'config.enrollment_ignored',
] as const;

export type SecurityEvent = (typeof SECURITY_EVENTS)[number];

export interface EventFields {
  pseudonym?: HumanPseudonym;
  count?: number;
  code?: string;
  environment?: string;
}

/** Where log lines go: NestJS's ConsoleLogger in JSON mode, or a test capture. */
export interface LogSink {
  log(message: unknown): void;
  error(message: unknown): void;
}

/** Fixed operational messages: the only free text the service logs. */
export type Notice =
  'started' | 'stopping' | 'first_admin.registered' | 'migrations.applied' | 'prune.done';

export class SecurityLog {
  private readonly sink: LogSink;

  constructor(sink: LogSink = new ConsoleLogger('org-gateway', { json: true })) {
    this.sink = sink;
  }

  event(name: SecurityEvent, requestId: string | undefined, fields: EventFields = {}): void {
    this.sink.log({ event: name, ...(requestId ? { requestId } : {}), ...fields });
  }

  notice(name: Notice, fields: { count?: number } = {}): void {
    this.sink.log({ notice: name, ...fields });
  }

  /** An unexpected error: its code only, never its message or stack, which may hold input. */
  error(requestId: string | undefined, code: string): void {
    this.sink.error({ error: code, ...(requestId ? { requestId } : {}) });
  }
}
