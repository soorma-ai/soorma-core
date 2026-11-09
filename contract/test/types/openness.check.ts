// SPDX-License-Identifier: Apache-2.0
//
// Type-level fixture (TC-WC-032; NFR-WC-05): typechecked under `strict` against
// the generated types. The permitted assignments must compile, and each
// `@ts-expect-error` line must be a genuine error: an unused one is itself an
// error (TS2578), so a clean typecheck proves both.
import type { components } from '../../generated/components.ts';
import type { components as orgGateway } from '../../generated/org-gateway.ts';

type Schemas = components['schemas'];
type S1 = orgGateway['schemas'];

const base: Schemas['Envelope'] = {
  envelopeVersion: 1,
  scope: { organization: 'o1', project: 'p1', environment: 'e1' },
  originMode: 'autonomous',
  actorChain: [{ agent: 'agent-a', instance: 'host-1:4100' }],
  traceContext: { traceparent: '00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01' },
};
const draft: Schemas['Draft'] = { clientContractVersion: '0.1.0', traceContext: base.traceContext };

/** An unknown origin mode is accepted: the enumeration is open. */
export const sponsored: Schemas['Envelope'] = { ...base, originMode: 'sponsored' };

/** An unknown field is accepted: the envelope is open. */
export const extraKey: Schemas['Envelope'] = { ...base, 'x-future': 1 };

/** A received identifier is a plain string, of any length. */
export const longAgent: Schemas['ActorReference'] = { agent: 'a'.repeat(300), instance: 'host-1' };

/** Every member of the Problem is optional (amendment A3). */
export const emptyProblem: Schemas['Problem'] = {};

/** A secret_rejected reason is open: an unknown reason is accepted (amendment A5). */
export const futureReason: Schemas['SecretRejectedReason'] = 'too_similar';

/** ProblemFieldError's pointer, header (A4), and reason (A5) are all optional. */
export const headerError: Schemas['ProblemFieldError'] = { header: 'Authorization' };
export const reasonError: Schemas['ProblemFieldError'] = {
  pointer: '/newSecret',
  reason: 'breached',
};

/** A received S1 response is open: an unknown class and an unknown field are accepted. */
export const signIn: S1['SignIn'] = {
  token: 'soorma_si_x',
  expiresAt: '2026-11-08T12:15:00Z',
  subject: { organization: 'o1', principal: 'h@example.com' },
  authenticatedAt: '2026-11-08T12:00:00Z',
  classes: ['K', 'X'],
  'x-future': true,
};

const replaceSecret: S1['ReplaceSecretChange'] = { type: 'replaceSecret', newSecret: 'x' };

export const refused = [
  // @ts-expect-error reason is open, but still a string
  { pointer: '/newSecret', reason: 3 } satisfies Schemas['ProblemFieldError'],
  // @ts-expect-error an S1 request is closed: no unknown field
  { ...replaceSecret, extra: 1 } satisfies S1['ReplaceSecretChange'],
  // @ts-expect-error the request-side second-factor type is a closed set
  { type: 'webauthn', code: '123456' } satisfies S1['SecondFactorProof'],
  // @ts-expect-error originMode is open, but still a string
  { ...base, originMode: 7 } satisfies Schemas['Envelope'],
  // @ts-expect-error a draft cannot carry a platform-stamped field
  { ...draft, scope: base.scope } satisfies Schemas['Draft'],
  // @ts-expect-error a draft cannot carry envelopeVersion
  { ...draft, envelopeVersion: 1 } satisfies Schemas['Draft'],
];
