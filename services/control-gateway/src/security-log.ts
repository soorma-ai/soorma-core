// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's log helper (NP-EHA-12; NFR-EHA-18, 19): @soorma/service-kit's, typed by
// S2's security events: U4's ten and U5's four (NFR-AR-18). It has no parameter for a token, a key, or a
// principal identifier, so none can reach a log by mistake; a human is named
// only by E's own log pseudonym (`hp_`).
import { ConsoleLogger } from '@nestjs/common';
import { SecurityLog as ServiceSecurityLog, type LogSink } from '@soorma/service-kit/http';

export type { EventFields, LogSink } from '@soorma/service-kit/http';

export const SECURITY_EVENTS = [
  'credential.issued',
  'credential.renewed',
  'credential.ended',
  'credential.refused',
  'grant.made',
  'grant.denied',
  'first_grant.applied',
  'orglevel.unavailable',
  'store.unavailable',
  'throttle.refused',
  // U5 (NFR-AR-18)
  'registration.created',
  'registration.refused',
  'secret.issued',
  'secret.refused',
] as const;

export type SecurityEvent = (typeof SECURITY_EVENTS)[number];

/** Fixed operational messages: the only free text the service logs. */
export type Notice = 'started' | 'stopping' | 'verify_keys.loaded' | 'migrations.applied';

export class SecurityLog extends ServiceSecurityLog<SecurityEvent, Notice> {
  constructor(sink: LogSink = new ConsoleLogger('control-gateway', { json: true })) {
    super(sink);
  }
}
