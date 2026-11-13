// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The entry point (U3 D-AE-04; NP-05; NP-08): createEnvelopeAdmission(
// dependencies).admit(request), the only import a surface makes. S4 (U7)
// builds it once per instance and calls admit once per publish and per
// subscribe, after it has run check-order steps 1 to 4 (BR-IN-01).
//
// admit runs, in order, and returns the first refusal:
//   the invariant checks: an empty required set, or a credential scope that
//     differs from the configured scope, is internal_error (D-AE-10, 23)
//   5  contract version (P2)                                    no read
//   6  draft schema and trace context (P2)                      no read
//   7  forwarded context (P2)                                   no read
//   8  chain depth (P2)                                         no read
//   9  ONE agent-facts read for the presenter and the distinct upstream
//      agents, all or nothing; the request snapshot; origin from it; P11
//      built over it; then effective authority (P3)
//   10 stamp, bound, and seal (P2)
//
// - Construction builds, once: the draft validator (NFR-AE-03) and the
//   sealer over the key ring (NP-02). The agent-facts source arrives already
//   wrapped by createCachingAgentFacts, which S4 builds once per instance
// - Every refusal is RETURNED, never thrown, and writes exactly one
//   envelope_refused event to the security log: code, internal reason,
//   request id, environment, agent, instance. Never the body, the seal, the
//   forwarded envelope, or trace values (D-AE-26; NFR-AE-20). The returned
//   refusal carries no internal reason: it is P1's Refusal shape, ready for
//   problemResponse
// - An unexpected exception propagates to the surface's handler, which
//   answers internal_error
// - unavailable carries Retry-After 1 (NFR-AE-21)
// - Nothing outlives a call except the cache behind its port (NFR-AE-22)
// - U7 (D-ET-01; NP-ET-06; D-CG-ET-18, 20): an optional Body Form puts the
//   draft in a named member of the body, beside other required members. Step
//   5 refuses a body that is not an object, then a draft member that is not
//   one, then reads the version there; step 6 judges the body's members with
//   the draft's schema under the published precedence, pointers from the
//   body's root; then each member's bound, through a measure the caller
//   supplies (S4: jcs's source mode). Without a Body Form nothing changes
import {
  byPointer,
  checkChainDepth,
  checkVersion,
  isObject,
  MAX_ERRORS,
  own,
  createDraftValidator,
  createSealer,
  stamp,
  verifyInbound,
  type FieldError,
  type Refusal,
  type RefusalCode,
  type RefusalReason,
  type Result,
  type SealKeyRing,
  type ValidDraft,
  type VerifiedInbound,
} from '@soorma/envelope';
import type { EnvironmentRef, PermissionId, PolicyDecision } from '@soorma/policy-decision-seam';
import {
  requestGrantSource,
  requestSnapshot,
  type AgentFacts,
  type AgentFactsSource,
  type GrantSource,
} from './agent-facts.ts';
import { evaluateAgent } from './evaluate.ts';
import { resolveOrigin, type Origin } from './origin.ts';

/** What P1 hands U3 after steps 1 to 4: every field from the verified credential. */
export interface CheckedAgentContext {
  readonly scope: EnvironmentRef;
  /** The logical agent the credential is bound to. */
  readonly agent: string;
  /** The instance it asserts: recorded, not verified (I10). */
  readonly instance: string;
}

/**
 * A member's size, from the caller's measure (U7 D-CG-ET-20): its byte count,
 * or the pointer (within the member) of a value that has no measurable form.
 */
export type MemberMeasure = (
  value: unknown,
) => { readonly bytes: number } | { readonly invalid: string };

/** A body member beside the draft: required, and bounded when a measure is given. */
export interface BodyFormMember {
  readonly name: string;
  readonly measure?: MemberMeasure;
  /** The bound, in the measure's bytes: over it is payload_too_large. */
  readonly maxBytes?: number;
}

/** Where the draft sits in the body, and what else the body holds (U7 D-ET-01). */
export interface BodyForm {
  /** The member holding the draft. */
  readonly draft: string;
  /** Every other member the body must hold; any other member is unknown_field. */
  readonly members: readonly BodyFormMember[];
}

export interface EnvelopeRequest {
  /** The parsed body: any JSON value, untrusted. */
  readonly body: unknown;
  /** Absent: the body is the draft, as before U7. */
  readonly bodyForm?: BodyForm;
  /** Every Soorma-Contract-Version value the request carried, possibly none. */
  readonly contractVersionHeader: readonly string[];
  readonly agent: CheckedAgentContext;
  /** Non-empty: { event:publish } or { event:subscribe } (D-AE-10). */
  readonly required: Iterable<PermissionId>;
  readonly requestId: string;
}

/** The security log's one event (NFR-AE-20). */
export interface EnvelopeRefusedEvent {
  readonly code: RefusalCode;
  readonly reason: RefusalReason;
  readonly requestId: string;
  readonly environment: string;
  readonly agent: string;
  readonly instance: string;
}

export interface SecurityLog {
  envelopeRefused(event: EnvelopeRefusedEvent): void;
}

export interface AdmissionDependencies {
  /** P1's accepted contract versions (D-AE-25). */
  readonly acceptedVersions: readonly string[];
  /** This environment, as configured (P9). Compared, never stamped (D-AE-08). */
  readonly scope: EnvironmentRef;
  /** This environment's seal key ring (loadSealKeyRing over P9's loadSealKeys). */
  readonly keyRing: SealKeyRing;
  /** The agent-facts port, wrapped by createCachingAgentFacts. */
  readonly facts: AgentFactsSource;
  /** Builds the policy decision for a request: P11's createPolicyDecision by default. */
  readonly policyFactory: (options: {
    environment: EnvironmentRef;
    grants: GrantSource;
  }) => PolicyDecision;
  /** U4's human grants, uncached (NFR-AE-14). */
  readonly humanGrants: GrantSource;
  readonly securityLog: SecurityLog;
}

export interface Admitted {
  readonly envelope: Record<string, unknown>;
  readonly seal: string;
  /** For U7's attribution record (BR-ST-08). */
  readonly outcome: {
    readonly origin: Origin;
    readonly reBroadeningLoadBearing: boolean;
    readonly actorChain: readonly unknown[];
  };
}

/** P1's Refusal shape: a contract code, any field errors, any Retry-After. */
export interface Refused {
  readonly code: RefusalCode;
  readonly errors?: readonly FieldError[];
  readonly retryAfterSeconds?: number;
}

export type AdmissionResult = { readonly admitted: Admitted } | { readonly refused: Refused };

export interface EnvelopeAdmission {
  admit(request: EnvelopeRequest): Promise<AdmissionResult>;
}

/** RFC 6901's token for a member name. */
const pointerTo = (name: string): string => '/' + name.replaceAll('~', '~0').replaceAll('/', '~1');

/** The draft's field errors, re-pointed from the body's root. */
function rebase(errors: readonly FieldError[] | undefined, base: string): FieldError[] {
  return (errors ?? []).map((e) =>
    e.pointer === undefined ? e : { ...e, pointer: base + e.pointer },
  );
}

/**
 * Step 6 with a Body Form: the body's members and the draft's schema judged
 * together under the published precedence (stamped, then unknown, then any
 * other), errors[] the winning code's, ordered by pointer, at most 10; then
 * each member's bound. Undefined when everything passes.
 */
function judgeBody(
  body: Record<string, unknown>,
  form: BodyForm,
  draft: Result<ValidDraft>,
): Refusal | undefined {
  const base = pointerTo(form.draft);
  const named = new Set([form.draft, ...form.members.map((m) => m.name)]);
  const unknown: FieldError[] = Object.keys(body)
    .filter((k) => !named.has(k))
    .map((k) => ({ pointer: pointerTo(k) }));
  const missing: FieldError[] = form.members
    .filter((m) => !Object.hasOwn(body, m.name))
    .map((m) => ({ pointer: pointerTo(m.name) }));
  const failed = draft.ok ? undefined : draft.refusal;
  const draftErrors = rebase(failed?.errors, base);
  const list = (errors: FieldError[]): FieldError[] => byPointer(errors).slice(0, MAX_ERRORS);

  if (failed?.code === 'stamped_field_set') return { ...failed, errors: draftErrors };
  if (failed?.code === 'unknown_field' || unknown.length > 0)
    return {
      code: 'unknown_field',
      reason: failed?.code === 'unknown_field' ? failed.reason : 'unknown_field',
      errors: list([...(failed?.code === 'unknown_field' ? draftErrors : []), ...unknown]),
    };
  if (failed?.code === 'malformed_request' || missing.length > 0)
    return {
      code: 'malformed_request',
      reason: failed?.code === 'malformed_request' ? failed.reason : 'schema',
      errors: list([...(failed?.code === 'malformed_request' ? draftErrors : []), ...missing]),
    };
  if (failed) return { ...failed, errors: draftErrors };

  for (const member of form.members) {
    if (!member.measure) continue;
    const measured = member.measure(body[member.name]);
    if ('invalid' in measured)
      return {
        code: 'malformed_request',
        reason: 'member_invalid',
        errors: [{ pointer: pointerTo(member.name) + measured.invalid }],
      };
    if (member.maxBytes !== undefined && measured.bytes > member.maxBytes)
      return {
        code: 'payload_too_large',
        reason: 'member_too_large',
        errors: [{ pointer: pointerTo(member.name) }],
      };
  }
  return undefined;
}

function sameScope(a: EnvironmentRef, b: EnvironmentRef): boolean {
  return (
    a.organization === b.organization && a.project === b.project && a.environment === b.environment
  );
}

export function createEnvelopeAdmission(dependencies: AdmissionDependencies): EnvelopeAdmission {
  const { acceptedVersions, facts, policyFactory, humanGrants, securityLog } = dependencies;
  const scope: EnvironmentRef = Object.freeze({
    organization: dependencies.scope.organization,
    project: dependencies.scope.project,
    environment: dependencies.scope.environment,
  });
  const validator = createDraftValidator();
  const sealer = createSealer(dependencies.keyRing);

  return Object.freeze({
    async admit(request: EnvelopeRequest): Promise<AdmissionResult> {
      const { agent } = request;
      const refused = (refusal: Refusal): AdmissionResult => {
        securityLog.envelopeRefused({
          code: refusal.code,
          reason: refusal.reason,
          requestId: request.requestId,
          environment: scope.environment,
          agent: agent.agent,
          instance: agent.instance,
        });
        return {
          refused: {
            code: refusal.code,
            ...(refusal.errors ? { errors: refusal.errors } : {}),
            ...(refusal.retryAfterSeconds === undefined
              ? {}
              : { retryAfterSeconds: refusal.retryAfterSeconds }),
          },
        };
      };
      const refuse = (code: RefusalCode, reason: RefusalReason): AdmissionResult =>
        refused({ code, reason });

      // Invariant checks: a defect, never a client's fault, never an allow.
      const required = new Set(request.required);
      if (required.size === 0) return refuse('internal_error', 'empty_required_set');
      if (!sameScope(agent.scope, scope))
        return refuse('internal_error', 'credential_scope_mismatch');

      // Steps 5 to 8: no read.
      const form = request.bodyForm;
      let draftBody: unknown = request.body;
      if (form) {
        // Step 5 with a Body Form: the body, then the draft member, are objects.
        if (!isObject(request.body))
          return refused({
            code: 'malformed_request',
            reason: 'body_not_object',
            errors: [{ pointer: '' }],
          });
        draftBody = own(request.body, form.draft);
        if (!isObject(draftBody))
          return refused({
            code: 'malformed_request',
            reason: 'body_not_object',
            errors: [{ pointer: pointerTo(form.draft) }],
          });
      }
      const version = checkVersion(draftBody, request.contractVersionHeader, acceptedVersions);
      if (!version.ok) return refused(version.refusal);
      const draft = validator.validate(version.value);
      if (form) {
        const judged = judgeBody(request.body as Record<string, unknown>, form, draft);
        if (judged) return refused(judged);
      }
      if (!draft.ok) return refused(draft.refusal);
      let inbound: VerifiedInbound | undefined;
      if (draft.value.inbound) {
        const verified = verifyInbound(draft.value.inbound, scope, sealer);
        if (!verified.ok) return refused(verified.refusal);
        inbound = verified.value;
      }
      const depth = checkChainDepth(inbound ? inbound.actorChain.length : 0);
      if (!depth.ok) return refused(depth.refusal);

      // Step 9: one read, all or nothing, for the presenter and the distinct upstream agents.
      const upstream = [...new Set((inbound?.actorChain ?? []).map((a) => a.agent))];
      const agents = [...new Set([agent.agent, ...upstream])];
      let found: ReadonlyMap<string, AgentFacts>;
      try {
        found = await facts.load(scope, agents);
      } catch {
        return refused({
          code: 'unavailable',
          reason: 'agent_facts_read_failed',
          retryAfterSeconds: 1,
        });
      }
      const snapshot = requestSnapshot(agents, found);
      const presenter = snapshot.facts(agent.agent);

      const origin = resolveOrigin(presenter?.registrationView, inbound);
      if (!origin.ok) return refused(origin.refusal);

      const policy = policyFactory({
        environment: scope,
        grants: requestGrantSource(snapshot, humanGrants),
      });
      const evaluation = await evaluateAgent({
        policy,
        environment: scope,
        presenter: agent.agent,
        declaration: presenter!.registrationView.reBroadeningDeclaration,
        upstream,
        unresolved: new Set(upstream.filter((a) => !snapshot.facts(a))),
        required,
      });
      if (!evaluation.allowed) return refuse('forbidden', evaluation.reason ?? 'authority_denied');

      // Step 10: stamp, bound, seal. Scope from the credential (D-AE-08).
      const stamped = stamp(
        {
          scope: agent.scope,
          actor: { agent: agent.agent, instance: agent.instance },
          draft: draft.value,
          inbound,
          loadBearing: evaluation.loadBearing,
        },
        sealer,
      );
      if (!stamped.ok) return refused(stamped.refusal);

      return {
        admitted: {
          envelope: stamped.value.envelope,
          seal: stamped.value.seal,
          outcome: {
            origin: origin.value,
            reBroadeningLoadBearing: evaluation.loadBearing,
            actorChain: stamped.value.envelope.actorChain as unknown[],
          },
        },
      };
    },
  });
}
