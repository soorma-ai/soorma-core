// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The log helper (U2 P-17; D-CG-OI-06; NFR-OI-22, 23), generalised for every
// service (U4 NP-EHA-12, 15): each service types it by its own event list and
// notices. Structured JSON to stdout through NestJS's ConsoleLogger. It takes
// only:
//   - an event name from the service's fixed list
//   - the request id
//   - non-secret fields: a HumanPseudonym (a type only pseudonym() makes), a
//     count, a code, an environment
// It has no parameter for material, a token, or a principal identifier, so
// none can reach a log by mistake.
import type { HumanPseudonym } from '../crypto/pseudonym.ts';

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

/** What the exception filter needs: an unexpected error's code, never its message. */
export interface ErrorLog {
  error(requestId: string | undefined, code: string): void;
}

export class SecurityLog<Event extends string, Notice extends string = never> implements ErrorLog {
  private readonly sink: LogSink;

  constructor(sink: LogSink) {
    this.sink = sink;
  }

  event(name: Event, requestId: string | undefined, fields: EventFields = {}): void {
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
