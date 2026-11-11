// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1's five operations (contract/org-gateway.openapi.yaml), in U1's check
// order as business-logic-model §1 applies it.
//
// Operations naming no security scheme (firstAuthenticate, authenticate,
// changeMaterial):
//   1 body size (Fastify, 16 KiB)        payload_too_large
//   2 no Authorization or Soorma-Delegation header   malformed_request, naming it
//   3 Soorma-Contract-Version            unsupported_contract_version
//   4 JSON, then the contract's schema   malformed_request
//   5 to 9 in P10                        too_many_attempts, authentication_failed, …
// Sign-in operations (renewSignIn, endSignIn):
//   1 body size; 2 to 4 the presented sign-in (P1): credential_refused,
//   credential_expired; 5 contract version; then no body; then P10
import type { components } from '@soorma/contract/types/org-gateway';
import type {
  IssuedSignIn,
  MaterialChangeResult,
  PrincipalReference,
  Refusal,
  SignInClaims,
} from '@soorma/org-identity';
import { CONTRACT_VERSION, presentedCredentialHeaders, ProblemError } from '@soorma/perimeter';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { RequestSchema } from '../contract-validator.ts';
import { rawBody } from '../http.ts';
import type { Runtime } from '../runtime.ts';

type Schemas = components['schemas'];

const JSON_TYPE = /^application\/json\s*(;\s*charset=utf-8\s*)?$/i;

function wireSignIn(s: IssuedSignIn): Schemas['SignIn'] {
  return {
    token: s.token,
    expiresAt: s.expiresAt.toISOString(),
    subject: { ...s.subject },
    authenticatedAt: s.authenticatedAt.toISOString(),
    classes: [...s.classes],
  };
}

function wireChange(result: MaterialChangeResult): Schemas['ChangeMaterialResponse'] {
  if (result.type === 'beginSecondFactor')
    return {
      type: result.type,
      enrollment: {
        id: result.enrollment.id,
        expiresAt: result.enrollment.expiresAt.toISOString(),
        setup: { ...result.enrollment.setup },
      },
    };
  return { type: result.type, retired: [...result.retired], signInsEnded: result.signInsEnded };
}

export class EdgeHandlers {
  private readonly rt: Runtime;

  constructor(runtime: Runtime) {
    this.rt = runtime;
  }

  async firstAuthenticate(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const body = this.unauthenticated<Schemas['FirstAuthenticateRequest']>(
      request,
      'FirstAuthenticateRequest',
    );
    const result = await this.rt.identity.firstAuthenticate(
      body.principal,
      body.enrollmentMaterial,
      body.newSecret,
    );
    if (!result.ok) return this.refused(request, body.principal, result.refusal);
    const { value } = result;
    if (value.signIn)
      this.rt.log.event('signin.issued', request.id, {
        pseudonym: this.rt.pseudonym(body.principal),
      });
    const response: Schemas['FirstAuthenticateResponse'] = {
      principal: { ...value.principal },
      state: value.state,
      ...(value.signIn
        ? { signIn: wireSignIn(value.signIn) }
        : { secondFactorEnrollmentRequired: true }),
    };
    this.json(reply, 200, response);
  }

  async authenticate(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const body = this.unauthenticated<Schemas['AuthenticateRequest']>(
      request,
      'AuthenticateRequest',
    );
    const result = await this.rt.identity.authenticate(
      body.principal,
      body.secret,
      body.secondFactor,
    );
    if (!result.ok) return this.refused(request, body.principal, result.refusal);
    this.rt.log.event('signin.issued', request.id, {
      pseudonym: this.rt.pseudonym(body.principal),
    });
    this.json(reply, 200, { signIn: wireSignIn(result.value) } satisfies Schemas['SignInResponse']);
  }

  async renewSignIn(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const claims = await this.signInBearing(request);
    const reference = { organization: this.rt.organization, principal: claims.principal };
    const result = await this.rt.identity.renewSignIn(claims);
    if (!result.ok) return this.refused(request, reference, result.refusal);
    this.rt.log.event('signin.issued', request.id, {
      pseudonym: this.rt.pseudonym(reference),
      code: 'renewal',
    });
    this.json(reply, 200, { signIn: wireSignIn(result.value) } satisfies Schemas['SignInResponse']);
  }

  async endSignIn(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const claims = await this.signInBearing(request);
    const reference = { organization: this.rt.organization, principal: claims.principal };
    const result = await this.rt.identity.endSignIn(claims);
    if (!result.ok) return this.refused(request, reference, result.refusal);
    this.rt.log.event('signin.ended', request.id, { pseudonym: this.rt.pseudonym(reference) });
    void reply.status(204).send();
  }

  async changeMaterial(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const body = this.unauthenticated<Schemas['ChangeMaterialRequest']>(
      request,
      'ChangeMaterialRequest',
    );
    const result = await this.rt.identity.changeMaterial(body.principal, body.current, body.change);
    if (!result.ok) return this.refused(request, body.principal, result.refusal);
    if (result.value.type !== 'beginSecondFactor')
      this.rt.log.event('material.changed', request.id, {
        pseudonym: this.rt.pseudonym(body.principal),
        code: result.value.type,
        count: result.value.signInsEnded,
      });
    this.json(reply, 200, wireChange(result.value));
  }

  // ---- The check order -------------------------------------------------------

  /** Steps 2 to 4 for an operation naming no security scheme; returns the valid body. */
  private unauthenticated<T>(request: FastifyRequest, schema: RequestSchema): T {
    const presented = presentedCredentialHeaders(request.raw.rawHeaders);
    if (presented.length > 0)
      throw new ProblemError('malformed_request', {
        errors: presented.map((header) => ({
          header,
          detail: 'This operation accepts no credential',
        })),
      });
    this.contractVersion(request);
    const value = this.json_(request);
    const errors = this.rt.validator.validate(schema, value);
    if (errors.length > 0) throw new ProblemError('malformed_request', { errors });
    return value as T;
  }

  /** Steps 2 to 5, then no body, for renewSignIn and endSignIn. */
  private async signInBearing(request: FastifyRequest): Promise<SignInClaims> {
    const check = await this.rt.perimeter.check(request.raw.rawHeaders);
    if (!check.accepted) throw new ProblemError(check.code);
    this.contractVersion(request);
    if (rawBody(request).length > 0)
      throw new ProblemError('malformed_request', {
        errors: [{ pointer: '', detail: 'This operation takes no request body' }],
      });
    return check.claims;
  }

  private contractVersion(request: FastifyRequest): void {
    if (request.headers['soorma-contract-version'] !== CONTRACT_VERSION)
      throw new ProblemError('unsupported_contract_version');
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

  // ---- Responses ---------------------------------------------------------------

  private json(reply: FastifyReply, status: number, body: unknown): void {
    void reply
      .status(status)
      .header('Content-Type', 'application/json; charset=utf-8')
      .send(JSON.stringify(body));
  }

  /** A refusal from P10: its Problem, and its security event (never an identifier). */
  private refused(request: FastifyRequest, reference: PrincipalReference, refusal: Refusal): never {
    const pseudonym = this.rt.pseudonym(reference);
    switch (refusal.code) {
      case 'too_many_attempts':
        this.rt.log.event('auth.bound_refused', request.id, { pseudonym });
        throw new ProblemError('too_many_attempts', {
          retryAfterSeconds: refusal.retryAfterSeconds,
        });
      case 'authentication_failed':
      case 'second_factor_not_confirmed':
        this.rt.log.event('auth.failed', request.id, { pseudonym, code: refusal.code });
        throw new ProblemError(refusal.code);
      case 'second_factor_enrollment_required':
        this.rt.log.event('auth.second_factor_required', request.id, { pseudonym });
        throw new ProblemError(refusal.code);
      case 'secret_rejected':
        throw new ProblemError('secret_rejected', {
          errors: [{ pointer: refusal.pointer, reason: refusal.reason }],
        });
      case 'credential_refused':
        throw new ProblemError('credential_refused');
    }
  }
}
