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
// U5 adds registerAgent and issueRegistrationSecret (business-rules §10):
//
//   step  registerAgent                           issueRegistrationSecret
//   2-5   as grantToHuman: a soorma_ec_, O1 to O4, the contract version
//   6     schema; accepted ids (both sets);       schema
//         human-only class; declaration within
//         standing (P3, before any state read)
//   9     ONE read of the held set (P3):          ONE read (P3): agent:register;
//         agent:register; the ceiling             the registration; sponsor or Admin
//   write registration + record                   the cap under its lock; secret +
//         (registration_exists at the key)        record; the value returned once
//
// Refusals: specific for validation, generic for trust (BR-RF-01); every
// refusal is a security event with its internal reason, never in a response
// (BR-RF-03); a human is named only by E's log pseudonym. Each write and its
// attribution record commit in one transaction (D-EHA-17).
import { recordAttribution } from '@soorma/attribution';
import {
  checkRegistrationRequest,
  evaluateHuman,
  holdsAnyGrant,
  readHumanAuthority,
} from '@soorma/authority';
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
import {
  CONTRACT_VERSION,
  presentedEnvironmentCredential,
  ProblemError,
  type FieldError,
  type ProblemCode,
} from '@soorma/perimeter';
import {
  createGrant,
  findRegistration,
  generateRegistrationSecret,
  insertRegistration,
  insertSecretUnderCap,
  isAcceptedIdentifier,
  unacceptedPositions,
} from '@soorma/registry';
import { UnavailableError } from '@soorma/service-kit';
import type { SignInStatus } from '@soorma/service-kit';
import { rawBody } from '@soorma/service-kit/http';
import type { FastifyReply, FastifyRequest } from 'fastify';
import type { Runtime } from '../runtime.ts';
import { CREDENTIAL_LIFETIME_MS } from '../settings.ts';

type Schemas = components['schemas'];

const JSON_TYPE = /^application\/json\s*(;\s*charset=utf-8\s*)?$/i;

/** At most this many entries in errors[], the first by pointer (U1 BR-ERR; D-AR-03). */
const MAX_POINTERS = 10;

/** Pointers for the given indexes of a body member, ordered by pointer (code unit), at most 10. */
function pointersAt(member: string, indexes: Iterable<number>, detail: string): FieldError[] {
  return [...indexes]
    .map((i) => `/${member}/${i}`)
    .sort()
    .slice(0, MAX_POINTERS)
    .map((pointer) => ({ pointer, detail }));
}

/** Indexes of `values` matching `test`. */
const indexesOf = (values: readonly string[], test: (v: string) => boolean): number[] =>
  values.flatMap((v, i) => (test(v) ? [i] : []));

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

  // ---- registerAgent (U5 BR-RQ, BR-SP, BR-RG; D-AR-02, 03, 07) -------------------

  async registerAgent(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const { claims } = await this.presented(request);
    const sponsor = claims.principal;
    this.contractVersion(request);
    // Step 6: the schema; then the request's own sets, before any state is read.
    const value = this.json_(request);
    const errors = this.rt.validator.validate('RegistrationRequest', value);
    if (errors.length > 0) throw new ProblemError('malformed_request', { errors });
    const body = value as Schemas['RegistrationRequest'];
    const standing = body.standingPermissions;
    const declared = body.reBroadeningDeclaration ?? [];
    const autonomyDeclared = body.autonomyDeclared ?? false;
    const notAccepted = (p: string): boolean => !isAcceptedIdentifier(p);
    const unaccepted = [
      ...indexesOf(standing, notAccepted).map((i) => `/standingPermissions/${i}`),
      ...indexesOf(declared, notAccepted).map((i) => `/reBroadeningDeclaration/${i}`),
    ]
      .sort()
      .slice(0, MAX_POINTERS)
      .map((pointer) => ({ pointer, detail: 'Not an accepted permission' }));
    if (unaccepted.length > 0)
      this.refuseRegistration(
        request,
        'unknown_permission',
        'unknown_permission',
        sponsor,
        unaccepted,
      );
    const check = checkRegistrationRequest({ policy: this.rt.policy, standing, declared });
    if (check.humanOnly.length > 0)
      this.refuseRegistration(
        request,
        'human_only_permission',
        'human_only_in_standing',
        sponsor,
        pointersAt('standingPermissions', check.humanOnly, 'A human-only permission'),
      );
    if (check.outsideStanding.length > 0)
      this.refuseRegistration(
        request,
        'declaration_outside_standing',
        'declaration_outside_standing',
        sponsor,
        pointersAt('reBroadeningDeclaration', check.outsideStanding, 'Not in the standing set'),
      );
    // Step 9: one read of the sponsor's held set; every check through evaluateHeld (D-AR-07).
    const auth = await this.humanAuthority(request, 'registration.refused', sponsor);
    if (!auth.allows(['agent:register']))
      this.refuseRegistration(request, 'forbidden', 'authority_denied', sponsor);
    // The sponsor ceiling: standing within what the sponsor holds (PF FR-016). Empty is within.
    if (standing.length > 0 && !auth.allows(standing))
      this.refuseRegistration(
        request,
        'exceeds_sponsor_ceiling',
        'ceiling_exceeded',
        sponsor,
        pointersAt('standingPermissions', auth.exceeding(standing), 'Not held by the sponsor'),
      );
    const now = this.rt.clock.now();
    const written = await withTransaction(this.rt.store, async (tx) => {
      const w = await insertRegistration(tx, {
        environment: this.rt.environment,
        agent: body.agent,
        sponsor,
        ceilingSnapshot: auth.snapshot(),
        standingPermissions: standing,
        reBroadeningDeclaration: declared,
        autonomyDeclared,
        registeredAt: now,
      });
      if (w.kind === 'exists') return w;
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment: this.rt.environment,
        operation: 'registerAgent',
        actor: {
          kind: 'human',
          principal: sponsor,
          credential: { kind: 'environmentCredential', id: claims.cid },
        },
        target: { kind: 'registration', id: body.agent },
      });
      return w;
    });
    if (written.kind === 'exists')
      this.refuseRegistration(request, 'registration_exists', 'registration_exists', sponsor, [
        { pointer: '/agent', detail: 'Already registered in this environment' },
      ]);
    const r = written.registration;
    this.rt.log.event('registration.created', request.id, {
      pseudonym: this.rt.pseudonym(sponsor),
    });
    const response: Schemas['Registration'] = {
      agent: r.agent,
      environment: { ...this.rt.environment },
      sponsor: { organization: this.rt.environment.organization, principal: r.sponsor },
      ceilingSnapshot: [...r.ceilingSnapshot],
      standingPermissions: [...r.standingPermissions],
      reBroadeningDeclaration: [...r.reBroadeningDeclaration],
      autonomyDeclared: r.autonomyDeclared,
      registeredAt: r.registeredAt.toISOString(),
      state: r.state,
    };
    this.json(reply, 200, response);
  }

  // ---- issueRegistrationSecret (U5 BR-SE; D-AR-01, 04, 05, 16) ------------------

  async issueRegistrationSecret(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    const { claims } = await this.presented(request);
    const issuer = claims.principal;
    this.contractVersion(request);
    const value = this.json_(request);
    const errors = this.rt.validator.validate('RegistrationSecretRequest', value);
    if (errors.length > 0) throw new ProblemError('malformed_request', { errors });
    const body = value as Schemas['RegistrationSecretRequest'];
    // Step 9: one read; agent:register; the registration; sponsor or Admin (D-AR-01).
    const auth = await this.humanAuthority(request, 'secret.refused', issuer);
    if (!auth.allows(['agent:register']))
      this.refuseSecret(request, 'forbidden', 'authority_denied', issuer);
    const registration = await findRegistration(
      this.rt.store,
      this.rt.environment,
      body.registration,
    );
    if (!registration)
      this.refuseSecret(request, 'unknown_registration', 'unknown_registration', issuer, [
        { pointer: '/registration', detail: 'Not registered in this environment' },
      ]);
    // The sponsor (both parts equal: the registration is E's, so its organization is E's), or
    // an Admin in E: a holder of grant:human and human:manage (ID §3).
    const isSponsor = registration.sponsor === issuer;
    if (!isSponsor && !auth.allows(['grant:human', 'human:manage']))
      this.refuseSecret(request, 'forbidden', 'not_sponsor_or_admin', issuer);
    const generated = generateRegistrationSecret();
    const now = this.rt.clock.now();
    const written = await withTransaction(this.rt.store, async (tx) => {
      const w = await insertSecretUnderCap(tx, {
        id: generated.id,
        environment: this.rt.environment,
        registration: registration.agent,
        issuer,
        digest: generated.digest,
        issuedAt: now,
      });
      if (w.kind === 'limitReached') return w;
      await recordAttribution(tx, {
        id: newRecordId(),
        recordedAt: now,
        requestId: request.id,
        environment: this.rt.environment,
        operation: 'issueRegistrationSecret',
        actor: {
          kind: 'human',
          principal: issuer,
          credential: { kind: 'environmentCredential', id: claims.cid },
        },
        target: { kind: 'registration', id: registration.agent },
      });
      return w;
    });
    if (written.kind === 'limitReached')
      this.refuseSecret(request, 'secret_limit_reached', 'secret_limit_reached', issuer);
    this.rt.log.event('secret.issued', request.id, { pseudonym: this.rt.pseudonym(issuer) });
    // The value exists only here: never stored, logged, or recorded (NFR-AR-04).
    const response: Schemas['RegistrationSecret'] = {
      id: written.secret.id,
      registration: written.secret.registration,
      secret: generated.value,
      issuedAt: written.secret.issuedAt.toISOString(),
    };
    void reply.header('Cache-Control', 'no-store');
    this.json(reply, 200, response);
  }

  /** P3's one read of a human's held set; an unreadable set is unavailable (D-AR-13). */
  private async humanAuthority(
    request: FastifyRequest,
    event: 'registration.refused' | 'secret.refused',
    principal: string,
  ): Promise<Awaited<ReturnType<typeof readHumanAuthority>>> {
    try {
      return await readHumanAuthority({
        policy: this.rt.policy,
        environment: this.rt.environment,
        principal,
      });
    } catch (error) {
      if (error instanceof UnavailableError)
        this.rt.log.event(event, request.id, {
          code: 'held_set_unreadable',
          pseudonym: this.rt.pseudonym(principal),
        });
      throw error;
    }
  }

  private refuseRegistration(
    request: FastifyRequest,
    code: ProblemCode,
    reason: string,
    principal: string,
    errors?: FieldError[],
  ): never {
    this.rt.log.event('registration.refused', request.id, {
      code: reason,
      pseudonym: this.rt.pseudonym(principal),
    });
    throw new ProblemError(code, errors ? { errors } : {});
  }

  private refuseSecret(
    request: FastifyRequest,
    code: ProblemCode,
    reason: string,
    principal: string,
    errors?: FieldError[],
  ): never {
    this.rt.log.event('secret.refused', request.id, {
      code: reason,
      pseudonym: this.rt.pseudonym(principal),
    });
    throw new ProblemError(code, errors ? { errors } : {});
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
