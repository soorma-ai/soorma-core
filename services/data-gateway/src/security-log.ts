// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's log helper (NFR-AC-22; D-AC-26; D-ID-AC-11): @soorma/service-kit's,
// typed by S3's security events. An agent event names the logical agent, the
// asserted instance, and E, each a JSON value (BR-ID-09), with the internal
// reason (BR-RF-AC-03). There is no field for a secret, its id, its digest,
// or a token, so none can reach a log by mistake; and none for a human, whom
// S3 never logs (no log-pseudonym key, D-ID-AC-11).
import { ConsoleLogger } from '@nestjs/common';
import { SecurityLog as ServiceSecurityLog, type LogSink } from '@soorma/service-kit/http';

export type { LogSink } from '@soorma/service-kit/http';

export const SECURITY_EVENTS = [
  'credential.issued',
  'credential.renewed',
  'bootstrap.refused',
  'renewal.refused',
  'bound.refused',
  'store.unavailable',
  'throttle.refused',
] as const;

export type SecurityEvent = (typeof SECURITY_EVENTS)[number];

/** Fixed operational messages: the only free text the service logs. */
export type Notice = 'started' | 'stopping';

/** What an agent event may carry. */
export interface AgentFields {
  /** The presented or verified logical agent identifier. */
  readonly agent?: string;
  /** The asserted instance identifier. */
  readonly instance?: string;
  /** The internal reason (BR-RF-AC-03), for a refusal. */
  readonly code?: string;
}

export class SecurityLog extends ServiceSecurityLog<SecurityEvent, Notice> {
  private readonly out: LogSink;
  private readonly environment: string | undefined;

  constructor(
    sink: LogSink = new ConsoleLogger('data-gateway', { json: true }),
    environment?: string,
  ) {
    super(sink);
    this.out = sink;
    this.environment = environment;
  }

  /** An event about an agent in E, naming the agent and instance as values. */
  agentEvent(name: SecurityEvent, requestId: string, fields: AgentFields): void {
    this.out.log({
      event: name,
      requestId,
      ...(this.environment === undefined ? {} : { environment: this.environment }),
      ...(fields.agent === undefined ? {} : { agent: fields.agent }),
      ...(fields.instance === undefined ? {} : { instance: fields.instance }),
      ...(fields.code === undefined ? {} : { code: fields.code }),
    });
  }
}
