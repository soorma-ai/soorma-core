// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Check-order step 10: stamp, bound, and seal (U3 BR-ST-01 to 07; D-AE-05,
// 08, 14, 22; NP-07).
//
// Without inbound (BR-ST-01): envelopeVersion 1; scope from the Checked Agent
// Context, from the credential, never configuration (D-AE-08); originMode
// autonomous; no delegatingPrincipal; actorChain [this hop]; traceContext the
// draft's.
//
// With a verified inbound (BR-ST-02): start from inbound.envelope as
// received, every unknown field at every level included (D-AE-14), through an
// iterative copy that creates own data properties only (NP-07). Set
// envelopeVersion 1; keep scope, originMode, and delegatingPrincipal; append
// this hop to the chain as received.
//
// traceContext (BR-ST-03; U1 amendment A6): the forwarded traceContext's
// fields other than traceparent and tracestate, then the draft's
// traceparent, then the draft's tracestate only if the draft carries one.
//
// reBroadening (BR-ST-04): the forwarded records as received, then
// { hop: n } when re-broadening was load-bearing here, n this hop's
// zero-based index in the new chain. Absent when there is none.
//
// The stamped envelope's JCS form is computed once, for the bound and the
// seal (NFR-AE-05). Over 16384 bytes it is envelope_too_large: nothing is
// truncated or dropped to fit (BR-ST-06).
import { canonicalize } from '@soorma/jcs';
import { copyJson } from './copy.ts';
import type { ValidDraft } from './draft.ts';
import {
  ENVELOPE_BOUND,
  type ActorReference,
  type Scope,
  type VerifiedInbound,
} from './inbound.ts';
import { isObject, ok, own, refuse, type Result } from './refusal.ts';
import type { Sealer } from './seal.ts';

export interface StampInput {
  /** The Checked Agent Context's scope: stamped when there is no inbound. */
  readonly scope: Scope;
  /** This hop: the credential's logical agent, and the instance it asserts. */
  readonly actor: ActorReference;
  readonly draft: ValidDraft;
  readonly inbound?: VerifiedInbound | undefined;
  /** Whether re-broadening was load-bearing at this hop (BR-AU-05). */
  readonly loadBearing: boolean;
}

export interface Stamped {
  readonly envelope: Record<string, unknown>;
  readonly seal: string;
  /** The envelope's JCS size in bytes. */
  readonly size: number;
}

function draftTraceContext(draft: ValidDraft): Record<string, string> {
  const { traceparent, tracestate } = draft.traceContext;
  return tracestate === undefined ? { traceparent } : { traceparent, tracestate };
}

export function stamp(input: StampInput, sealer: Sealer): Result<Stamped> {
  const hop = { agent: input.actor.agent, instance: input.actor.instance };
  let envelope: Record<string, unknown>;

  if (!input.inbound) {
    envelope = {
      envelopeVersion: 1,
      scope: {
        organization: input.scope.organization,
        project: input.scope.project,
        environment: input.scope.environment,
      },
      originMode: 'autonomous',
      actorChain: [hop],
      traceContext: draftTraceContext(input.draft),
    };
  } else {
    envelope = copyJson(input.inbound.envelope);
    envelope.envelopeVersion = 1;
    envelope.actorChain = [...(own(envelope, 'actorChain') as unknown[]), hop];
    const forwarded = own(envelope, 'traceContext');
    const traceContext: Record<string, unknown> = isObject(forwarded) ? forwarded : {};
    delete traceContext.traceparent;
    delete traceContext.tracestate;
    Object.assign(traceContext, draftTraceContext(input.draft));
    envelope.traceContext = traceContext;
  }

  if (input.loadBearing) {
    const chain = own(envelope, 'actorChain') as unknown[];
    const records = (own(envelope, 'reBroadening') ?? []) as unknown[];
    envelope.reBroadening = [...records, { hop: chain.length - 1 }];
  }

  // A stamped envelope always has a JCS form: a failure here is a defect,
  // and propagates to the surface's handler as internal_error (NFR-AE-04).
  const { bytes } = canonicalize(envelope);
  if (bytes.length > ENVELOPE_BOUND) return refuse('envelope_too_large', 'envelope_bound');
  return ok({ envelope, seal: sealer.seal(bytes), size: bytes.length });
}
