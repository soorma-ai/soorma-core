// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's two operations (contract/event-ingest.openapi.yaml), in U1's check
// order (business-rules §11). Both are envelope-bearing; the draft is the
// body's `draft` member (D-ET-01).
//
//   -  throttle, at request start (throttle.ts)               unavailable
//   1  the raw body over its route's limit (Fastify:
//      publish 256 KiB, subscribe 64 KiB)                     payload_too_large
//   2-4 P1's checkAgentRequest: the presenter (exactly one
//      soorma_ac_, no Soorma-Delegation), O1 with E's agent
//      verify halves, O2, O4, then O3 through P5's cache at
//      both granularities                                    credential_refused,
//                                                            credential_expired,
//                                                            unavailable
//   -  the parse step (NP-ET-05): parse 1, the draft as today; parse 2, for a
//      publish, the payload with every number by its source text
//   5-10 admit, once, with the Body Form (U3's entry point)   its codes
//   -  subscribe: the open-stream cap                         unavailable
//   -  publish: the Delivery's frame, built before anything is written
//   write one transaction: the sponsor, then the record (P7)  unavailable
//   then: publish hands the frame to E's channel, 202; subscribe opens the
//   stream, registers and supersedes, releases its permit
//
// Nothing here consults another entry point's result: every check runs on
// the raw request (BR-CK-06). A refusal is a Problem through P1 and one
// security event; the internal reason only in the log (BR-RF-ET-01).
import type { Admitted, BodyForm, EnvelopeAdmission, MemberMeasure } from '@soorma/authority';
import { recordAttribution } from '@soorma/attribution';
import { verifyAgentCredential } from '@soorma/credentials';
import { newRecordId, withTransaction } from '@soorma/env-store';
import { canonicalize, CanonicalizationError, parseRawNumbers } from '@soorma/jcs';
import {
  checkAgentRequest,
  CONTRACT_VERSION,
  ProblemError,
  rawHeaderValues,
  type AgentVerification,
  type CheckedAgentContext,
} from '@soorma/perimeter';
import { sponsorForRecord } from '@soorma/registry';
import type { SecretText } from '@soorma/service-kit';
import { rawBody } from '@soorma/service-kit/http';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';
import { DELIVERY_PAYLOAD_BOUND, RETRY_AFTER_SECONDS } from '../settings.ts';
import { deliveryFrame as sseDelivery, Stream } from '../stream/stream.ts';
import { releasePermit } from '../throttle.ts';
import { markReached } from './reached.ts';

const JSON_TYPE = /^application\/json\s*(;\s*charset=utf-8\s*)?$/i;

/**
 * The payload's size (NP-ET-05; D-CG-ET-20): its JCS form with each number
 * counted by its source text, or the pointer of a value that has none (a lone
 * surrogate). `admit` reports either from the member's root (`/payload/...`).
 */
export const measurePayload: MemberMeasure = (value) => {
  try {
    return { bytes: canonicalize(value, { numbers: 'source' }).bytes.length };
  } catch (error) {
    if (error instanceof CanonicalizationError) return { invalid: error.pointer };
    throw error;
  }
};

/**
 * One Delivery's SSE frame, serialized once for every stream (NP-ET-11, as
 * amended by D-CG-ET-29): spliced from the envelope and the seal by
 * JSON.stringify (no raw values, at most 16 KiB) and the payload's JCS text
 * with each number by its source text, exactly the bytes measured against P.
 * canonicalize is iterative, so any nesting P admits is written; JSON.stringify
 * would recurse once a raw value is present. Object members of the payload
 * arrive in RFC 8785 order (envelope.md).
 */
export function deliveryFrame(admitted: Admitted, payload: unknown): string {
  return sseDelivery(
    `{"envelope":${JSON.stringify(admitted.envelope)},"seal":${JSON.stringify(admitted.seal)},` +
      `"payload":${canonicalize(payload, { numbers: 'source' }).text}}`,
  );
}

const PUBLISH_FORM: BodyForm = Object.freeze({
  draft: 'draft',
  members: Object.freeze([
    Object.freeze({ name: 'payload', measure: measurePayload, maxBytes: DELIVERY_PAYLOAD_BOUND }),
  ]),
});
const SUBSCRIBE_FORM: BodyForm = Object.freeze({ draft: 'draft', members: Object.freeze([]) });

/** Steps 2 to 4 passed: the checked context and the credential's `exp`. */
interface Presented {
  readonly context: CheckedAgentContext;
  readonly expiresAt: Date;
}

export class EdgeHandlers {
  private readonly rt: Runtime;
  private readonly admission: EnvelopeAdmission;

  constructor(runtime: Runtime) {
    this.rt = runtime;
    this.admission = runtime.admission;
  }

  // ---- publish (BR-PB) -------------------------------------------------------------

  async publish(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    markReached(request);
    const { context } = await this.present(request);
    const body = this.parse(request, true);
    const admitted = await this.admit(request, context, body, PUBLISH_FORM, 'event:publish');
    // The frame first: a frame that cannot be built leaves no record behind a 500.
    const frame = deliveryFrame(admitted, (body as Record<string, unknown>).payload);
    // Then the record, in its own transaction; nothing is delivered without it (D-ET-09, 16).
    await this.record(request, 'publish', context, admitted);
    try {
      this.rt.channel.publish({ kind: 'delivery', frame });
    } catch {
      // The record stands: an authorized attempt, recorded (BR-PB-04).
      this.refused(request, context, 'unavailable', 'hand_off_failed');
      throw new ProblemError('unavailable', { retryAfterSeconds: RETRY_AFTER_SECONDS });
    }
    this.rt.log.agentEvent('event.published', request.id, {
      agent: context.agent,
      instance: context.instance,
    });
    void reply.status(202).send();
  }

  // ---- subscribe (BR-SB, BR-SM) ----------------------------------------------------

  async subscribe(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    markReached(request);
    const { context, expiresAt } = await this.present(request);
    const body = this.parse(request, false);
    const admitted = await this.admit(request, context, body, SUBSCRIBE_FORM, 'event:subscribe');
    // The open-stream cap (D-ET-25): a slot, held until the stream registers.
    const slot = this.rt.streams.reserve(context.cid);
    if (!slot) {
      this.rt.log.event('throttle.refused', request.id, { code: 'streams' });
      throw new ProblemError('unavailable', { retryAfterSeconds: RETRY_AFTER_SECONDS });
    }
    try {
      await this.record(request, 'subscribe', context, admitted);
    } catch (error) {
      slot.release();
      throw error;
    }
    // The subscribe's own envelope is recorded and given to no one (BR-SB-04).
    void reply.hijack();
    const stream = new Stream(
      {
        requestId: request.id,
        environment: this.rt.environment,
        agent: context.agent,
        instance: context.instance,
        cid: context.cid,
        expiresAt,
        order: this.rt.orderKey(),
      },
      reply.raw,
      {
        clock: this.rt.clock,
        scheduler: this.rt.scheduler,
        revocation: this.rt.revocation,
        onEnded: (s, ending) => this.rt.ended(s, ending),
      },
    );
    stream.open({
      'Soorma-Contract-Version': CONTRACT_VERSION,
      'Soorma-Request-Id': request.id,
    });
    this.rt.streams.register(stream, slot);
    // An open stream holds no permit (NFR-ET-12; NP-ET-13).
    releasePermit(request);
    this.rt.log.agentEvent('stream.opened', request.id, {
      agent: context.agent,
      instance: context.instance,
    });
  }

  // ---- Shared steps ----------------------------------------------------------------

  /** Steps 2 to 4 through P1, with E's verify-only ring and P5's cache (BR-CK-02). */
  private async present(request: FastifyRequest): Promise<Presented> {
    const environment = this.rt.environment;
    const now = this.rt.clock.now();
    let expiresAt: Date | undefined;
    const check = await checkAgentRequest(request.raw.rawHeaders, {
      verify: async (token: SecretText): Promise<AgentVerification> => {
        const verified = await verifyAgentCredential(token, this.rt.ring, environment, now);
        if (!verified.ok) return { ok: false, code: verified.code, reason: verified.reason };
        const { claims } = verified;
        expiresAt = claims.expiresAt;
        return {
          ok: true,
          context: {
            scope: { ...claims.environment },
            agent: claims.agent,
            instance: claims.instance,
            cid: claims.cid,
          },
        };
      },
      // Throws UnavailableError with no answer younger than B: 503 (BR-CK-04).
      revocation: (c) => this.rt.revocation.isRevoked({ environment, cid: c.cid, agent: c.agent }),
    });
    if (!check.accepted) {
      this.rt.log.agentEvent('ingest.refused', request.id, {
        ...(check.context ? { agent: check.context.agent, instance: check.context.instance } : {}),
        code: check.code,
        reason: check.reason,
      });
      throw new ProblemError(check.code);
    }
    return { context: check.context, expiresAt: expiresAt! };
  }

  /**
   * The parse step (NP-ET-05): the body decoded once; parse 1 as every
   * envelope-bearing body is parsed; for a publish, parse 2 of the same text
   * carries the payload's numbers by their source text, and its `payload`
   * replaces parse 1's. Not JSON at all is step 5's `malformed_request` at "".
   */
  private parse(request: FastifyRequest, publish: boolean): unknown {
    const bytes = rawBody(request);
    const type = request.headers['content-type'];
    const notJson = (detail: string): ProblemError => {
      this.rt.log.agentEvent('ingest.refused', request.id, {
        code: 'malformed_request',
        reason: 'body_not_json',
      });
      return new ProblemError('malformed_request', { errors: [{ pointer: '', detail }] });
    };
    if (bytes.length === 0 || typeof type !== 'string' || !JSON_TYPE.test(type))
      throw notJson('The body must be JSON (application/json)');
    let text: string;
    let value: unknown;
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
      value = JSON.parse(text) as unknown;
    } catch {
      throw notJson('The body is not valid JSON');
    }
    if (publish && isObject(value) && Object.hasOwn(value, 'payload')) {
      const raw = parseRawNumbers(text) as Record<string, unknown>;
      value.payload = raw.payload;
    }
    return value;
  }

  /** Steps 5 to 10: `admit`, once, with the Body Form (BR-EP-02). */
  private async admit(
    request: FastifyRequest,
    context: CheckedAgentContext,
    body: unknown,
    bodyForm: BodyForm,
    required: string,
  ): Promise<Admitted> {
    const result = await this.admission.admit({
      body,
      bodyForm,
      contractVersionHeader: rawHeaderValues(request.raw.rawHeaders, 'soorma-contract-version'),
      agent: { scope: context.scope, agent: context.agent, instance: context.instance },
      required: [required],
      requestId: request.id,
    });
    if ('refused' in result) {
      // admit has written its own envelope.refused event (NFR-AE-20).
      const { code, errors, retryAfterSeconds } = result.refused;
      throw new ProblemError(code, {
        ...(errors ? { errors: errors.map((e) => ({ ...e })) } : {}),
        ...(retryAfterSeconds === undefined ? {} : { retryAfterSeconds }),
      });
    }
    return result.admitted;
  }

  /**
   * One transaction, its only write the record (BR-AT-ET-01 to 03): the
   * sponsor as of the write, then P7. `hop` is the chain's last index exactly
   * when re-broadening was load-bearing: it is local to the presenter's hop.
   * A store failure is UnavailableError: 503, nothing delivered, no stream.
   */
  private async record(
    request: FastifyRequest,
    operation: 'publish' | 'subscribe',
    context: CheckedAgentContext,
    admitted: Admitted,
  ): Promise<void> {
    const environment = this.rt.environment;
    const { actorChain, origin, reBroadeningLoadBearing } = admitted.outcome;
    await withTransaction(this.rt.store, async (tx) => {
      const sponsor = await sponsorForRecord(tx, environment, context.agent);
      // A verified, admitted agent always has its registration (never deleted).
      if (sponsor === undefined) throw new Error('no registration for an admitted agent');
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: this.rt.clock.now(),
        requestId: request.id,
        environment,
        operation,
        actor: {
          kind: 'agent',
          registration: context.agent,
          instance: context.instance,
          sponsor,
          credential: { kind: 'agentCredential', id: context.cid },
        },
        envelope: {
          chain: actorChain,
          origin: { originMode: origin },
          reBroadening: reBroadeningLoadBearing
            ? { loadBearing: true, hop: actorChain.length - 1 }
            : { loadBearing: false },
        },
      });
    });
  }

  private refused(
    request: FastifyRequest,
    context: CheckedAgentContext,
    code: string,
    reason: string,
  ): void {
    this.rt.log.agentEvent('ingest.refused', request.id, {
      agent: context.agent,
      instance: context.instance,
      code,
      reason,
    });
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
