// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's four operations (contract/control-gateway.openapi.yaml), in Functional
// Design §11's check order. Steps 7, 8, and 10 do not apply: no envelope.
//
//   step  issue                  renew                    end            grantToHuman
//   1     body size (Fastify, 16 KiB): payload_too_large
//   2     a soorma_si_ (P1)      a soorma_ec_ (P1)        same           same
//   3     the sign-in, verified  the credential (P5)      same           same
//   4     signInStatus (A7)      O4, O3; signInStatus     O4, O3         O4, O3
//   5     Soorma-Contract-Version: unsupported_contract_version
//   6     no body                no body                  no body        schema; accepted ids
//   9     holdsAnyGrant          (self)                   (self)         grant:human; the target
//   write credential + record    expiry + record          ended + record grant + record
//
// Refusals: specific for validation, generic for trust (BR-RF-01); every
// refusal is a security event with its internal reason, never in a response
// (BR-RF-03); a human is named only by E's log pseudonym. Each write and its
// attribution record commit in one transaction (D-EHA-17).
import { recordAttribution } from '@soorma/attribution';
import { evaluateHuman, holdsAnyGrant } from '@soorma/authority';
import type { components } from '@soorma/contract/types/control-gateway';
import {
  checkCredentialRecord,
  endCredential,
  insertCredential,
  mintEnvironmentCredential,
  renewCredential,
  verifyEnvironmentCredential,
  type CredentialClaims,
  type CredentialRecord,
} from '@soorma/credentials';
import { newRecordId, withTransaction } from '@soorma/env-store';
import { CONTRACT_VERSION, presentedEnvironmentCredential, ProblemError } from '@soorma/perimeter';
import { createGrant, unacceptedPositions } from '@soorma/registry';
import type { SignInStatus } from '@soorma/service-kit';
import { rawBody } from '@soorma/service-kit/http';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';
import { CREDENTIAL_LIFETIME_MS } from '../settings.ts';

type Schemas = components['schemas'];

const JSON_TYPE = /^application\/json\s*(;\s*charset=utf-8\s*)?$/i;

/** Whole seconds: the token's exp, and the record's expiry, are the same instant. */
const toSeconds = (ms: number): Date => new Date(Math.floor(ms / 1000) * 1000);

interface Presented {
  claims: CredentialClaims;
  record: CredentialRecord;
}

export class EdgeHandlers {
  private readonly rt: Runtime;

  constructor(runtime: Runtime) {
    this.rt = runtime;
  }

  // ---- issueEnvironmentCredential (BR-IS, BR-EC-01, 04) ------------------------

  async issue(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const check = await this.rt.signIn.check(request.raw.rawHeaders);
    if (!check.accepted) this.refuse(request, check.code, 'sign_in_refused');
    const { claims, status } = check;
    this.contractVersion(request);
    this.noBody(request);
    const principal = claims.principal;
    if (
      !(await holdsAnyGrant({
        policy: this.rt.policy,
        environment: this.rt.environment,
        principal,
      }))
    )
      this.refuse(request, 'forbidden', 'no_grant_in_environment', principal);
    const now = this.rt.clock.now();
    const expiresAt = this.cap(now, status);
    if (expiresAt.getTime() <= now.getTime())
      this.refuse(request, 'credential_refused', 'sign_in_expiring', principal);
    const cid = newRecordId();
    await withTransaction(this.rt.store, async (tx) => {
      await insertCredential(tx, {
        id: cid,
        environment: this.rt.environment,
        principal,
        issuedFrom: claims.sid,
        issuedAt: now,
        expiresAt,
      });
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment: this.rt.environment,
        operation: 'issueEnvironmentCredential',
        actor: { kind: 'human', principal, credential: { kind: 'signIn', id: claims.sid } },
        target: { kind: 'environmentCredential', id: cid },
      });
    });
    const credential = await mintEnvironmentCredential(
      {
        environment: this.rt.environment,
        principal,
        cid,
        jti: newRecordId(),
        issuedAt: now,
        expiresAt,
      },
      this.rt.ring,
    );
    this.rt.log.event('credential.issued', request.id, { pseudonym: this.rt.pseudonym(principal) });
    const body: Schemas['EnvironmentCredentialResponse'] = {
      credential,
      expiresAt: expiresAt.toISOString(),
    };
    this.json(reply, 200, body);
  }

  // ---- renewEnvironmentCredential (BR-EC-04, 05) ---------------------------------

  async renew(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const { claims, record } = await this.presented(request);
    const principal = claims.principal;
    const status = await this.rt.orgLevel.signInStatus(record.issuedFrom);
    if (status.status !== 'live')
      this.refuse(request, 'credential_refused', 'sign_in_ended', principal);
    this.contractVersion(request);
    this.noBody(request);
    const now = this.rt.clock.now();
    const expiresAt = this.cap(now, status);
    if (expiresAt.getTime() <= now.getTime())
      this.refuse(request, 'credential_refused', 'sign_in_expiring', principal);
    const renewed = await withTransaction(this.rt.store, async (tx) => {
      if (
        !(await renewCredential(tx, {
          id: claims.cid,
          environment: this.rt.environment,
          expiresAt,
        }))
      )
        return false;
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment: this.rt.environment,
        operation: 'renewEnvironmentCredential',
        actor: {
          kind: 'human',
          principal,
          credential: { kind: 'environmentCredential', id: claims.cid },
        },
        target: { kind: 'environmentCredential', id: claims.cid },
      });
      return true;
    });
    // The end won the race (D-EHA-26): refused, with no record.
    if (!renewed) this.refuse(request, 'credential_refused', 'credential_ended', principal);
    const credential = await mintEnvironmentCredential(
      {
        environment: this.rt.environment,
        principal,
        cid: claims.cid,
        jti: newRecordId(),
        issuedAt: now,
        expiresAt,
      },
      this.rt.ring,
    );
    this.rt.log.event('credential.renewed', request.id, {
      pseudonym: this.rt.pseudonym(principal),
    });
    const body: Schemas['EnvironmentCredentialResponse'] = {
      credential,
      expiresAt: expiresAt.toISOString(),
    };
    this.json(reply, 200, body);
  }

  // ---- endEnvironmentCredential (BR-EC-07, 09): no call to S1 --------------------

  async end(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const { claims } = await this.presented(request);
    const principal = claims.principal;
    this.contractVersion(request);
    this.noBody(request);
    const now = this.rt.clock.now();
    const ended = await withTransaction(this.rt.store, async (tx) => {
      if (
        !(await endCredential(tx, {
          id: claims.cid,
          environment: this.rt.environment,
          endedAt: now,
        }))
      )
        return false;
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment: this.rt.environment,
        operation: 'endEnvironmentCredential',
        actor: {
          kind: 'human',
          principal,
          credential: { kind: 'environmentCredential', id: claims.cid },
        },
        target: { kind: 'environmentCredential', id: claims.cid },
      });
      return true;
    });
    if (!ended) this.refuse(request, 'credential_refused', 'credential_ended', principal);
    this.rt.log.event('credential.ended', request.id, { pseudonym: this.rt.pseudonym(principal) });
    void reply.status(204).send();
  }

  // ---- grantToHuman (BR-GR-01 to 09) ---------------------------------------------

  async grant(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const { claims } = await this.presented(request);
    const actor = claims.principal;
    this.contractVersion(request);
    // Step 6: the schema, then the accepted identifiers, before authority.
    const value = this.json_(request);
    const errors = this.rt.validator.validate('GrantRequest', value);
    if (errors.length > 0) throw new ProblemError('malformed_request', { errors });
    const body = value as Schemas['GrantRequest'];
    const unaccepted = unacceptedPositions(body.permissions);
    if (unaccepted.length > 0)
      throw new ProblemError('unknown_permission', {
        errors: unaccepted.map((i) => ({
          pointer: `/permissions/${i}`,
          detail: 'Not an accepted permission',
        })),
      });
    // Step 9: authority, then the target, so only an Admin in E learns existence (BR-RF-02).
    const allowed = await evaluateHuman({
      policy: this.rt.policy,
      environment: this.rt.environment,
      principal: actor,
      required: ['grant:human'],
    });
    if (!allowed.allowed) {
      this.rt.log.event('grant.denied', request.id, {
        pseudonym: this.rt.pseudonym(actor),
        code: 'authority_denied',
      });
      throw new ProblemError('forbidden');
    }
    const target = body.target;
    const exists =
      target.organization === this.rt.environment.organization &&
      (await this.rt.orgLevel.principalExists({
        organization: target.organization,
        principal: target.principal,
      }));
    if (!exists)
      throw new ProblemError('unknown_principal', {
        errors: [{ pointer: '/target', detail: 'No such principal in this organization' }],
      });
    const now = this.rt.clock.now();
    const grant = await withTransaction(this.rt.store, async (tx) => {
      const g = await createGrant(tx, {
        id: newRecordId(),
        environment: this.rt.environment,
        principal: target.principal,
        permissions: body.permissions,
        grantedBy: { principal: actor, credential: claims.cid },
        grantedAt: now,
      });
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment: this.rt.environment,
        operation: 'grantToHuman',
        actor: {
          kind: 'human',
          principal: actor,
          credential: { kind: 'environmentCredential', id: claims.cid },
        },
        target: { kind: 'grant', id: g.id },
        selfGrant: g.selfGrant,
      });
      return g;
    });
    this.rt.log.event('grant.made', request.id, { pseudonym: this.rt.pseudonym(actor) });
    const response: Schemas['Grant'] = {
      id: grant.id,
      target: { organization: target.organization, principal: grant.principal },
      permissions: [...grant.permissions],
      grantedAt: grant.grantedAt.toISOString(),
      selfGrant: grant.selfGrant,
    };
    this.json(reply, 200, response);
  }

  // ---- Shared steps --------------------------------------------------------------

  /** Steps 2 to 4 for a presented environment credential: P1, P5, then O3 (BR-EC-02). */
  private async presented(request: FastifyRequest): Promise<Presented> {
    const token = presentedEnvironmentCredential(request.raw.rawHeaders);
    // No === on a secret, even against undefined (NP-EHA-14): a present token is never empty.
    if (!token) this.refuse(request, 'credential_refused', 'presentation');
    const verified = await verifyEnvironmentCredential(
      token,
      this.rt.ring,
      this.rt.environment,
      this.rt.clock.now(),
    );
    if (!verified.ok) this.refuse(request, verified.code, verified.reason);
    const o3 = await checkCredentialRecord(this.rt.store, verified.claims);
    if (!o3.ok) this.refuse(request, 'credential_refused', o3.reason, verified.claims.principal);
    return { claims: verified.claims, record: o3.record };
  }

  /** The expiry cap (BR-EC-04): the earlier of now + 15 minutes and the sign-in's. */
  private cap(now: Date, status: Extract<SignInStatus, { status: 'live' }>): Date {
    return toSeconds(Math.min(now.getTime() + CREDENTIAL_LIFETIME_MS, status.expiresAt.getTime()));
  }

  private contractVersion(request: FastifyRequest): void {
    if (request.headers['soorma-contract-version'] !== CONTRACT_VERSION)
      throw new ProblemError('unsupported_contract_version');
  }

  /** The credential operations take no body (D-EHA-24). */
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

  /** A refusal: its security event with the internal reason, and a generic Problem. */
  private refuse(
    request: FastifyRequest,
    code: 'credential_refused' | 'credential_expired' | 'forbidden',
    reason: string,
    principal?: string,
  ): never {
    this.rt.log.event('credential.refused', request.id, {
      code: reason,
      ...(principal === undefined ? {} : { pseudonym: this.rt.pseudonym(principal) }),
    });
    throw new ProblemError(code);
  }
}
