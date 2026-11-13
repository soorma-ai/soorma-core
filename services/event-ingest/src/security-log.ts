// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's log helper (NP-ET-16; NFR-ET-18, 19): @soorma/service-kit's, typed by
// S4's security events, and U3's security-log port (envelopeRefused). An
// event names E, the logical agent and the asserted instance once known, and
// the internal reason, each a JSON value. There is no field for a token, a
// seal, an envelope, a payload, a trace value, or a human, so none can reach
// a log by mistake (NFR-AE-20).
import { ConsoleLogger } from '@nestjs/common';
import type { EnvelopeRefusedEvent, SecurityLog as EnvelopeSecurityLog } from '@soorma/authority';
import { SecurityLog as ServiceSecurityLog, type LogSink } from '@soorma/service-kit/http';

export type { LogSink } from '@soorma/service-kit/http';

export const SECURITY_EVENTS = [
  'event.published',
  'stream.opened',
  'stream.ended',
  'stream.revoked',
  'stream.overflow',
  'ingest.refused',
  'envelope.refused',
  'store.unavailable',
  'throttle.refused',
] as const;

export type SecurityEvent = (typeof SECURITY_EVENTS)[number];

/** Fixed operational messages: the only free text the service logs. */
export type Notice = 'started' | 'stopping';

/** What an agent event may carry. */
export interface AgentFields {
  /** The verified logical agent identifier. */
  readonly agent?: string;
  /** The asserted instance identifier. */
  readonly instance?: string;
  /** The contract code, or the stream's end code. */
  readonly code?: string;
  /** The internal reason (BR-RF-ET-01), never in a response. */
  readonly reason?: string;
}

export class SecurityLog
  extends ServiceSecurityLog<SecurityEvent, Notice>
  implements EnvelopeSecurityLog
{
  private readonly out: LogSink;
  private readonly environment: string | undefined;

  constructor(
    sink: LogSink = new ConsoleLogger('event-ingest', { json: true }),
    environment?: string,
  ) {
    super(sink);
    this.out = sink;
    this.environment = environment;
  }

  /** An event about an agent in E, naming the agent and instance as values. */
  agentEvent(name: SecurityEvent, requestId: string, fields: AgentFields = {}): void {
    this.out.log({
      event: name,
      requestId,
      ...(this.environment === undefined ? {} : { environment: this.environment }),
      ...(fields.agent === undefined ? {} : { agent: fields.agent }),
      ...(fields.instance === undefined ? {} : { instance: fields.instance }),
      ...(fields.code === undefined ? {} : { code: fields.code }),
      ...(fields.reason === undefined ? {} : { reason: fields.reason }),
    });
  }

  /** U3's port (NFR-AE-20): one event per refusal from `admit`. */
  envelopeRefused(event: EnvelopeRefusedEvent): void {
    this.agentEvent('envelope.refused', event.requestId, {
      agent: event.agent,
      instance: event.instance,
      code: event.code,
      reason: event.reason,
    });
  }
}
