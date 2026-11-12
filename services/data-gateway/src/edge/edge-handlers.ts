// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's two operations (contract/data-gateway.openapi.yaml), in U1's check
// order as business-logic-model §2 and §3 apply it. Neither carries an
// envelope (GAP-INT-008), so steps 7, 8, and 10 do not apply.
//
// exchangeBootstrap (names no security scheme):
//   1  body size (Fastify, 16 KiB)                      payload_too_large
//   2  no Authorization or Soorma-Delegation header     malformed_request, naming it
//   5  Soorma-Contract-Version                          unsupported_contract_version
//   6  JSON, then the contract's schema: not counted    malformed_request
//   -  the bound, keyed on the presented agent, before
//      any material is parsed or any record read        too_many_attempts, Retry-After
//   -  P6's agent half: the prefix, the parse, the digest, ONE read of the
//      registration and the secret record, the constant-time compare
//   -  one transaction: the registration is registered, the agent is not
//      revoked (the direct read), then the record and its attribution
//   every failure after the bound                       authentication_failed (the one refusal)
//   -  settle the bound; mint with E's agent key ring; 200, no-store
//
// renewAgentCredential (names agentCredential):
//   1  body size; 2 to 4 P1's checkAgentRequest: the presenter, O1 (E's agent
//      ring), O2, O4, then O3 by the direct revocation read; then the record by
//      cid, bound to the token's agent and instance        credential_refused, credential_expired
//   5  contract version; 6 no body
//   -  one transaction: revocation read directly again (D-AC-01); the
//      registration is registered; the expiry moves to min(now + L, the
//      lineage end), only for the record's agent and instance; the attribution
//      record
//   -  mint a new token for the same cid; 200, no-store
//
// Refusals: specific for validation, generic for trust (BR-RF-AC-01); each is
// a security event with its internal reason, never in a response (BR-RF-AC-03).
import { agentSlotKey, type BootstrapFailureReason, type Reservation } from '@soorma/abuse-bound';
import { createAgentIdentityResolver, type AgentRejection } from '@soorma/agent-identity';
import { recordAttribution } from '@soorma/attribution';
import type { components } from '@soorma/contract/types/data-gateway';
import {
  directRevocationSource,
  insertAgentCredential,
  lineageTimes,
  mintAgentCredential,
  readAgentCredential,
  renewAgentCredentialRecord,
  renewedExpiry,
  verifyAgentCredential,
} from '@soorma/credentials';
import { newRecordId, withTransaction } from '@soorma/env-store';
import {
  checkAgentRequest,
  CONTRACT_VERSION,
  presentedCredentialHeaders,
  ProblemError,
  type AgentVerification,
  type CheckedAgentContext,
} from '@soorma/perimeter';
import type { EnvironmentRef } from '@soorma/policy-decision-seam';
import { registrationForBootstrap } from '@soorma/registry';
import { UnavailableError, type SecretText } from '@soorma/service-kit';
import { rawBody } from '@soorma/service-kit/http';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';

type Schemas = components['schemas'];

const JSON_TYPE = /^application\/json\s*(;\s*charset=utf-8\s*)?$/i;

/** Why a bootstrap was refused after the bound: the resolver's reasons, then core's. */
type BootstrapRefusal =
  AgentRejection | 'registration_not_registered' | 'agent_revoked' | 'store_unavailable';

/** Why a renewal was refused after P1: the record, revocation, and the registration. */
type RenewalRefusal =
  'no_record' | 'record_mismatch' | 'credential_revoked' | 'registration_not_registered';

export class EdgeHandlers {
  private readonly rt: Runtime;

  constructor(runtime: Runtime) {
    this.rt = runtime;
  }

  // ---- exchangeBootstrap (BR-PR-AC-02; BR-BQ; BR-AB-AC; BR-BS; D-AC-34) ---------

  async exchangeBootstrap(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const environment = this.rt.environment;
    // Step 2: an operation naming no scheme accepts no credential header.
    const headers = presentedCredentialHeaders(request.raw.rawHeaders);
    if (headers.length > 0)
      throw new ProblemError('malformed_request', {
        errors: headers.map((header) => ({
          header,
          detail: 'This operation accepts no credential',
        })),
      });
    // Steps 5 and 6: the contract version, then the closed body. Not counted (BR-BQ-02).
    this.contractVersion(request);
    const value = this.json_(request);
    const errors = this.rt.validator.validate('BootstrapRequest', value);
    if (errors.length > 0) throw new ProblemError('malformed_request', { errors });
    const { agent, secret, instance } = value as Schemas['BootstrapRequest'];
    const now = this.rt.clock.now();

    // The bound: admitted for (E, agent), known or not, before any material is
    // parsed or any record read (BR-AB-AC-01; D-AC-06, 34).
    const admission = await this.rt.bound.admit(agentSlotKey(environment, agent));
    if (!admission.admitted) {
      this.attempt(agent, now, true, 'bound_refused');
      this.rt.log.agentEvent('bound.refused', request.id, { agent, instance });
      throw new ProblemError('too_many_attempts', {
        retryAfterSeconds: admission.retryAfterSeconds,
      });
    }
    const reservation = admission.reservation;

    // P6's agent half: one read of the registration and the secret record (BR-BS-01 to 04).
    let rejection: AgentRejection = 'unknown_secret';
    const resolver = createAgentIdentityResolver({
      store: this.rt.store,
      onRejected: (reason) => (rejection = reason),
    });
    const resolution = await this.unlessUnavailable(request, reservation, agent, instance, () =>
      resolver.resolve('registrationSecret', { environment, agent }, secret),
    );
    if (!resolution.resolved)
      return this.refuseBootstrap(request, reservation, agent, instance, rejection, now);

    // One transaction: the registration's state, the agent's revocation (the
    // direct read, D-AC-01), the credential record, and its attribution record
    // (BR-BS-05, 06; BR-AT-AC-01). A refusal inside writes nothing.
    const cid = newRecordId();
    const times = lineageTimes(now);
    const refused = await this.unlessUnavailable(request, reservation, agent, instance, () =>
      withTransaction(this.rt.store, async (tx) => {
        const registration = await registrationForBootstrap(tx, environment, agent);
        if (registration?.state !== 'registered') return 'registration_not_registered' as const;
        if ((await directRevocationSource(tx).isRevoked({ environment, agent })) === 'revoked')
          return 'agent_revoked' as const;
        await insertAgentCredential(tx, {
          cid,
          environment,
          agent,
          instance,
          secret: resolution.secretId,
          ...times,
        });
        await recordAttribution(tx, {
          id: newRecordId(),
          recordedAt: now,
          requestId: request.id,
          environment,
          operation: 'exchangeBootstrap',
          actor: { kind: 'agent', registration: agent, instance, sponsor: registration.sponsor },
          target: { kind: 'agentCredential', id: cid },
        });
        return undefined;
      }),
    );
    if (refused !== undefined)
      return this.refuseBootstrap(request, reservation, agent, instance, refused, now);

    await this.rt.bound.settleSuccess(reservation);
    const credential = await mintAgentCredential(
      {
        environment,
        agent,
        instance,
        cid,
        jti: newRecordId(),
        issuedAt: times.issuedAt,
        expiresAt: times.expiresAt,
      },
      this.rt.ring,
    );
    this.rt.log.agentEvent('credential.issued', request.id, { agent, instance });
    this.issued(reply, credential, environment, agent, instance, times.expiresAt);
  }

  // ---- renewAgentCredential (BR-PR-AC-03, 04; BR-RN; D-AC-02, 15, 27) -----------

  async renewAgentCredential(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const environment = this.rt.environment;
    const now = this.rt.clock.now();
    // Steps 2 to 4: P1's check, verifying with E's agent ring and reading
    // revocation directly at both granularities (D-AC-01).
    const check = await checkAgentRequest(request.raw.rawHeaders, {
      verify: (token) => this.verify(token, environment, now),
      revocation: (c) =>
        directRevocationSource(this.rt.store).isRevoked({
          environment,
          cid: c.cid,
          agent: c.agent,
        }),
    });
    if (!check.accepted) {
      this.rt.log.agentEvent('renewal.refused', request.id, { code: check.reason });
      throw new ProblemError(check.code);
    }
    const { agent, instance, cid } = check.context;
    // The record, by cid in E, bound to the token's agent and instance (BR-RN-02).
    const record = await readAgentCredential(this.rt.store, cid, environment);
    if (!record) return this.refuseRenewal(request, check.context, 'no_record');
    if (record.agent !== agent || record.instance !== instance)
      return this.refuseRenewal(request, check.context, 'record_mismatch');
    this.contractVersion(request);
    this.noBody(request);

    // The new expiry: now + L, never past the lineage end (BR-RN-06; D-AC-02).
    const expiresAt = renewedExpiry(now, record.lineageEndsAt);
    // One transaction (BR-RN-07). Revocation is read directly again inside it,
    // before the expiry moves (D-AC-01): P1's read above keeps the check
    // order, so a bad token is refused before the store is needed; this one
    // keeps a revocation committed since then from being renewed past.
    const refused = await withTransaction(this.rt.store, async (tx) => {
      const revoked = await directRevocationSource(tx).isRevoked({ environment, cid, agent });
      if (revoked === 'revoked') return 'credential_revoked' as const;
      const registration = await registrationForBootstrap(tx, environment, agent);
      if (registration?.state !== 'registered') return 'registration_not_registered' as const;
      const renewed = await renewAgentCredentialRecord(tx, {
        cid,
        environment,
        agent,
        instance,
        expiresAt,
      });
      if (!renewed) return 'record_mismatch' as const;
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment,
        operation: 'renewAgentCredential',
        actor: {
          kind: 'agent',
          registration: agent,
          instance,
          sponsor: registration.sponsor,
          credential: { kind: 'agentCredential', id: cid },
        },
        target: { kind: 'agentCredential', id: cid },
      });
      return undefined;
    });
    if (refused !== undefined) return this.refuseRenewal(request, check.context, refused);

    const credential = await mintAgentCredential(
      { environment, agent, instance, cid, jti: newRecordId(), issuedAt: now, expiresAt },
      this.rt.ring,
    );
    this.rt.log.agentEvent('credential.renewed', request.id, { agent, instance });
    this.issued(reply, credential, environment, agent, instance, expiresAt);
  }

  // ---- Shared steps --------------------------------------------------------------

  /** O1, O2, O4 with E's agent key ring, as P1's callback (D-AC-03, 27). */
  private async verify(
    token: SecretText,
    environment: EnvironmentRef,
    now: Date,
  ): Promise<AgentVerification> {
    const verified = await verifyAgentCredential(token, this.rt.ring, environment, now);
    if (!verified.ok) return { ok: false, code: verified.code, reason: verified.reason };
    const { claims } = verified;
    return {
      ok: true,
      context: {
        scope: { ...claims.environment },
        agent: claims.agent,
        instance: claims.instance,
        cid: claims.cid,
      },
    };
  }

  /**
   * Runs a store step of bootstrap. A store failure is unavailable (503), and
   * the bound is settled as a failure and the attempt recorded, as far as the
   * store allows.
   */
  private async unlessUnavailable<T>(
    request: FastifyRequest,
    reservation: Reservation,
    agent: string,
    instance: string,
    work: () => Promise<T>,
  ): Promise<T> {
    try {
      return await work();
    } catch (error) {
      if (error instanceof UnavailableError) {
        this.rt.log.agentEvent('bootstrap.refused', request.id, {
          agent,
          instance,
          code: 'store_unavailable',
        });
        this.attempt(agent, this.rt.clock.now(), false, 'store_unavailable');
      }
      // Settled as a failure whatever went wrong; the request's own error is
      // what is answered, so a failure to settle is not allowed to replace it.
      await this.rt.bound.settleFailure(reservation).catch(() => undefined);
      throw error;
    }
  }

  /** The one refusal after the bound (D-AC-05): settled, recorded, logged, then 403. */
  private async refuseBootstrap(
    request: FastifyRequest,
    reservation: Reservation,
    agent: string,
    instance: string,
    reason: BootstrapRefusal,
    now: Date,
  ): Promise<never> {
    await this.rt.bound.settleFailure(reservation);
    // An unknown registration is never recorded: there is nothing to record it against (BR-FA-02).
    if (reason !== 'unknown_registration') this.attempt(agent, now, false, reason);
    this.rt.log.agentEvent('bootstrap.refused', request.id, { agent, instance, code: reason });
    throw new ProblemError('authentication_failed');
  }

  private refuseRenewal(
    request: FastifyRequest,
    context: CheckedAgentContext,
    reason: RenewalRefusal,
  ): never {
    this.rt.log.agentEvent('renewal.refused', request.id, {
      agent: context.agent,
      instance: context.instance,
      code: reason,
    });
    throw new ProblemError('credential_refused');
  }

  /** Queues a Failed Bootstrap Attempt, off the response path (BR-FA-01, 02). */
  private attempt(
    agent: string,
    at: Date,
    refusedByBound: boolean,
    reason: BootstrapFailureReason,
  ): void {
    this.rt.attempts.record({
      environment: this.rt.environment,
      agent,
      at,
      refusedByBound,
      reason,
    });
  }

  /** Both operations' 200 (D-AC-24): the credential, not cacheable. */
  private issued(
    reply: FastifyReply,
    credential: SecretText,
    environment: EnvironmentRef,
    agent: string,
    instance: string,
    expiresAt: Date,
  ): void {
    const body: Schemas['AgentCredential'] = {
      credential,
      agent,
      environment: {
        organization: environment.organization,
        project: environment.project,
        environment: environment.environment,
      },
      instance,
      expiresAt: expiresAt.toISOString(),
    };
    void reply.header('Cache-Control', 'no-store');
    this.json(reply, 200, body);
  }

  private contractVersion(request: FastifyRequest): void {
    if (request.headers['soorma-contract-version'] !== CONTRACT_VERSION)
      throw new ProblemError('unsupported_contract_version');
  }

  /** Renewal takes no body (D-AC-24). */
  private noBody(request: FastifyRequest): void {
    if (rawBody(request).length > 0)
      throw new ProblemError('malformed_request', {
        errors: [{ pointer: '', detail: 'This operation takes no request body' }],
      });
  }

  private json_(request: FastifyRequest): unknown {
    const body = rawBody(request);
    const type = request.headers['content-type'];
    if (body.length === 0 || typeof type !== 'string' || !JSON_TYPE.test(type))
      throw new ProblemError('malformed_request', {
        errors: [{ pointer: '', detail: 'The body must be JSON (application/json)' }],
      });
    try {
      return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(body)) as unknown;
    } catch {
      throw new ProblemError('malformed_request', {
        errors: [{ pointer: '', detail: 'The body is not valid JSON' }],
      });
    }
  }

  private json(reply: FastifyReply, status: number, body: unknown): void {
    void reply
      .status(status)
      .header('Content-Type', 'application/json; charset=utf-8')
      .send(JSON.stringify(body));
  }
}
