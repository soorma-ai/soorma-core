// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Check-order step 7: forwarded context, only when the draft carries inbound
// (U3 BR-FX-01 to 07; D-AE-15, 19, 22; NP-01, NP-03). Every failure is
// invalid_inbound_context, one code for every cause (BR-FC-03); the internal
// reason says which. In order:
//
// 1. jcs_invalid: inbound.envelope has no RFC 8785 form (a lone surrogate)
// 2. inbound_too_large: its JCS form exceeds 16384 UTF-8 bytes, checked
//    before any MAC is computed
// 3. seal_failed: the seal does not verify over the JCS form as received,
//    unknown fields included, with this environment's ring
// 4. envelope_version: envelopeVersion is not 1
// 5. scope_mismatch: scope's organization, project, and environment are not
//    all this environment's (exact; unknown fields in scope not compared)
// 6. rebroadening_index: a hop not less than the chain's length, or repeated
//
// The JCS form is computed once (NFR-AE-05). A verified forwarded envelope
// grants nothing (BR-FX-06): it contributes upstream terms and a chain prefix.
import { CanonicalizationError, canonicalize } from '@soorma/jcs';
import { ok, own, refuse, type Result } from './refusal.ts';
import type { Sealer } from './seal.ts';

/** The envelope bound: 16 KiB of the RFC 8785 serialization, UTF-8 (D-AE-22). */
export const ENVELOPE_BOUND = 16384;

/** An environment's identity, as a scope compares it. */
export interface Scope {
  readonly organization: string;
  readonly project: string;
  readonly environment: string;
}

export interface ActorReference {
  readonly agent: string;
  readonly instance: string;
}

/** inbound after step 7: the envelope as received, and what step 8 and 9 need. */
export interface VerifiedInbound {
  readonly envelope: Record<string, unknown>;
  readonly actorChain: readonly ActorReference[];
  readonly originMode: unknown;
}

export function verifyInbound(
  inbound: { readonly envelope: Record<string, unknown>; readonly seal: string },
  scope: Scope,
  sealer: Sealer,
): Result<VerifiedInbound> {
  let bytes: Buffer;
  try {
    bytes = canonicalize(inbound.envelope).bytes;
  } catch (error) {
    if (error instanceof CanonicalizationError)
      return refuse('invalid_inbound_context', 'jcs_invalid');
    throw error;
  }
  if (bytes.length > ENVELOPE_BOUND) return refuse('invalid_inbound_context', 'inbound_too_large');
  if (!sealer.verify(inbound.seal, bytes)) return refuse('invalid_inbound_context', 'seal_failed');

  // The schema (step 6) has checked the form: every field below is present.
  const envelope = inbound.envelope;
  if (own(envelope, 'envelopeVersion') !== 1)
    return refuse('invalid_inbound_context', 'envelope_version');
  const forwardedScope = own(envelope, 'scope') as Record<string, unknown>;
  if (
    own(forwardedScope, 'organization') !== scope.organization ||
    own(forwardedScope, 'project') !== scope.project ||
    own(forwardedScope, 'environment') !== scope.environment
  )
    return refuse('invalid_inbound_context', 'scope_mismatch');
  const actorChain = own(envelope, 'actorChain') as ActorReference[];
  const records = (own(envelope, 'reBroadening') ?? []) as Record<string, unknown>[];
  const hops = records.map((r) => own(r, 'hop') as number);
  if (hops.some((h) => h >= actorChain.length) || new Set(hops).size !== hops.length)
    return refuse('invalid_inbound_context', 'rebroadening_index');

  return ok({ envelope, actorChain, originMode: own(envelope, 'originMode') });
}
