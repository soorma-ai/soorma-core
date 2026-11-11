// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1's log helper (P-17; D-CG-OI-06; NFR-OI-22, 23): @soorma/service-kit's,
// typed by S1's fixed event list and notices (U4 NP-EHA-15). It has no
// parameter for material, a token, or a principal identifier, so none can
// reach a log by mistake.
import { ConsoleLogger } from '@nestjs/common';
import { SecurityLog as ServiceSecurityLog, type LogSink } from '@soorma/service-kit/http';

export type { EventFields, LogSink } from '@soorma/service-kit/http';

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

/** Fixed operational messages: the only free text the service logs. */
export type Notice =
  'started' | 'stopping' | 'first_admin.registered' | 'migrations.applied' | 'prune.done';

export class SecurityLog extends ServiceSecurityLog<SecurityEvent, Notice> {
  constructor(sink: LogSink = new ConsoleLogger('org-gateway', { json: true })) {
    super(sink);
  }
}
