// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P10, the organization level's flows (business-logic-model §2): the first
// Admin at start-up, first authentication, authentication, renewing and
// ending a sign-in, and material change. S1 runs checks 1 to 4 of the check
// order (body size, no credential header, contract version, schema) before
// calling these; each flow runs checks 5 to 9: the abuse bound, material
// verification through P6, the second-factor requirement, the K policy or the
// P confirmation, and the state change, atomically (P-13).
//
// The flows return outcomes and never log: S1 maps each outcome to its
// Problem and its security event. A store failure throws UnavailableError
// (fail closed). Nothing presented (K, a P proof, enrollment material, a
// token) is ever stored or returned, except the new token itself.
import { randomBytes } from 'node:crypto';
import type { HumanPrincipalReference, IdentityResolver } from '@soorma/identity-resolution-seam';
import type { Clock } from '../clock.ts';
import type { PrincipalReference } from '../crypto/canonical.ts';
import type { KeyRing } from '../crypto/key-ring.ts';
import type { SecretHasher } from '../crypto/secret-hash.ts';
import { asSecretText, type SecretText } from '../crypto/secret-types.ts';
import {
  decryptSeed,
  encryptSeed,
  SeedDecryptionError,
  type StoredSeed,
} from '../crypto/seed-cipher.ts';
import { mintSignIn, type MaterialClass, type SignInClaims } from '../crypto/sign-in-token.ts';
import { asTotpCode } from '../crypto/secret-types.ts';
import { base32, matchStep, newSeed, otpauthUri } from '../crypto/totp.ts';
import type { Lifetimes } from '../lifetimes.ts';
import type { SecretPolicy, SecretRejection } from '../policy/secret-policy.ts';
import { SQL } from '../sql.ts';
import type { Queryable, Store } from '../store/store.ts';
import type { AttemptBound, FailureRecorder, Surface } from './ports.ts';

export type Refusal =
  | { code: 'too_many_attempts'; retryAfterSeconds: number }
  | { code: 'authentication_failed' }
  | { code: 'second_factor_enrollment_required' }
  | { code: 'second_factor_not_confirmed' }
  | { code: 'secret_rejected'; pointer: string; reason: SecretRejection }
  | { code: 'credential_refused' };

export type Result<T> = { ok: true; value: T } | { ok: false; refusal: Refusal };

export interface SecondFactorProof {
  type: string;
  code: string;
}

export interface IssuedSignIn {
  token: string;
  sid: string;
  expiresAt: Date;
  subject: PrincipalReference;
  authenticatedAt: Date;
  classes: MaterialClass[];
}

export interface FirstAuthentication {
  principal: PrincipalReference;
  state: 'active';
  signIn?: IssuedSignIn;
  secondFactorEnrollmentRequired?: true;
}

export type MaterialChange =
  | { type: 'replaceSecret'; newSecret: string }
  | { type: 'beginSecondFactor'; authenticatorType: string }
  | { type: 'confirmSecondFactor'; enrollment: string; proof: SecondFactorProof };

export type MaterialChangeResult =
  | { type: 'replaceSecret'; retired: MaterialClass[]; signInsEnded: number }
  | {
      type: 'beginSecondFactor';
      enrollment: {
        id: string;
        expiresAt: Date;
        setup: { type: 'totp'; seed: string; otpauthUri: string };
      };
    }
  | { type: 'confirmSecondFactor'; retired: MaterialClass[]; signInsEnded: number };

export interface FirstAdminOutcome {
  registered: PrincipalReference[];
  /** Existing principals whose configured enrollment material was ignored (BR-CFG-04). */
  ignored: PrincipalReference[];
}

export class FirstAdminError extends Error {
  constructor(count: number) {
    super(`${count} first Admin(s) do not exist and have no enrollment material configured`);
    this.name = 'FirstAdminError';
  }
}

export interface OrgIdentityDependencies {
  organization: string;
  secondFactorRequired: boolean;
  store: Store;
  bound: AttemptBound;
  failures: FailureRecorder;
  resolver: IdentityResolver;
  hasher: SecretHasher;
  policy: SecretPolicy;
  keys: KeyRing;
  lifetimes: Lifetimes;
  clock: Clock;
}

const refuse = <T>(refusal: Refusal): Result<T> => ({ ok: false, refusal });
const ok = <T>(value: T): Result<T> => ({ ok: true, value });
const newId = (): string => randomBytes(16).toString('hex');

interface PendingRow {
  id: string;
  authenticator_type: string;
  seed: StoredSeed;
  expires_at: Date;
}

export class OrgIdentity {
  private readonly d: OrgIdentityDependencies;

  constructor(dependencies: OrgIdentityDependencies) {
    this.d = dependencies;
  }

  // ---- Start-up (business-logic-model §2.1) ----------------------------------

  /**
   * Registers each configured first Admin who does not exist, `pending`, with
   * a class-K `enrollment` record. An existing principal is left alone, and
   * any material configured for it is ignored (BR-CFG-03 to 05). Atomic and
   * idempotent: concurrent start-ups register a principal at most once.
   */
  async ensureFirstAdmin(
    firstAdmins: readonly { principal: string; registeredBy: string }[],
    enrollment: readonly { principal: string; material: SecretText }[],
  ): Promise<FirstAdminOutcome> {
    const outcome: FirstAdminOutcome = { registered: [], ignored: [] };
    const missing: string[] = [];
    for (const admin of firstAdmins) {
      const reference = { organization: this.d.organization, principal: admin.principal };
      const configured = enrollment.find((e) => e.principal === admin.principal);
      if (await this.exists(reference)) {
        if (configured) outcome.ignored.push(reference);
        continue;
      }
      if (!configured) {
        missing.push(admin.principal);
        continue;
      }
      const verifier = await this.d.hasher.hash(configured.material);
      const now = this.d.clock.now();
      const inserted = await this.d.store.transaction(async (tx) => {
        const rows = await tx.query(SQL.registerPrincipal, [
          reference.organization,
          reference.principal,
          now,
          admin.registeredBy,
        ]);
        if (rows.length === 0) return false;
        await tx.query(SQL.insertEnrollment, [
          newId(),
          reference.organization,
          reference.principal,
          verifier,
          now,
        ]);
        return true;
      });
      (inserted ? outcome.registered : outcome.ignored).push(reference);
    }
    if (missing.length > 0) throw new FirstAdminError(missing.length);
    return outcome;
  }

  // ---- First authentication (§2.2) -------------------------------------------

  async firstAuthenticate(
    reference: PrincipalReference,
    enrollmentMaterial: string,
    newSecret: string,
  ): Promise<Result<FirstAuthentication>> {
    const admission = await this.d.bound.admit(reference);
    if (!admission.admitted) return this.boundRefused(reference, 'firstAuthenticate', admission);
    const { reservation } = admission;

    const resolved = await this.d.resolver.resolve('enrollment', reference, enrollmentMaterial);
    if (!resolved.resolved) return this.failed(reference, 'firstAuthenticate', reservation);

    const policy = this.d.policy.check(asSecretText(newSecret), {
      reference,
      replaces: asSecretText(enrollmentMaterial),
    });
    if (!policy.accepted) {
      await this.d.bound.settleSuccess(reservation); // the material verified: not counted
      return refuse({ code: 'secret_rejected', pointer: '/newSecret', reason: policy.reason });
    }
    const verifier = await this.d.hasher.hash(policy.secret);
    const now = this.d.clock.now();
    const issue = !this.d.secondFactorRequired;
    const sid = newId();
    const expiresAt = this.d.lifetimes.signInExpiry(now);

    const won = await this.d.store.transaction(async (tx) => {
      const established = await tx.query(SQL.establishFromEnrollment, [
        resolved.materialId,
        verifier,
        now,
        reference.organization,
        reference.principal,
      ]);
      if (established.length !== 1) return false; // used by a concurrent call: single use
      const activated = await tx.query(SQL.activatePrincipal, [
        reference.organization,
        reference.principal,
        now,
      ]);
      if (activated.length !== 1)
        throw new Error('principal not pending with an enrollment record');
      if (issue)
        await tx.query(SQL.insertSignIn, [
          sid,
          reference.organization,
          reference.principal,
          now,
          ['K'],
          expiresAt,
        ]);
      return true;
    });
    if (!won) return this.failed(reference, 'firstAuthenticate', reservation);
    await this.d.bound.settleSuccess(reservation);

    if (!issue)
      return ok({
        principal: { ...reference },
        state: 'active',
        secondFactorEnrollmentRequired: true,
      });
    const signIn = await this.mint(reference, sid, now, ['K'], now, expiresAt);
    return ok({ principal: { ...reference }, state: 'active', signIn });
  }

  // ---- Authenticate (§2.3) ---------------------------------------------------

  async authenticate(
    reference: PrincipalReference,
    secret: string,
    secondFactor?: SecondFactorProof,
  ): Promise<Result<IssuedSignIn>> {
    const admission = await this.d.bound.admit(reference);
    if (!admission.admitted) return this.boundRefused(reference, 'authenticate', admission);
    const { reservation } = admission;

    const verified = await this.verifyCurrent(reference, secret, secondFactor);
    if (!verified) return this.failed(reference, 'authenticate', reservation);
    await this.d.bound.settleSuccess(reservation);

    if (!verified.classes.includes('P') && this.d.secondFactorRequired)
      return refuse({ code: 'second_factor_enrollment_required' });

    const now = this.d.clock.now();
    const sid = newId();
    const expiresAt = this.d.lifetimes.signInExpiry(now);
    await this.d.store.query(SQL.insertSignIn, [
      sid,
      reference.organization,
      reference.principal,
      now,
      verified.classes,
      expiresAt,
    ]);
    return ok(await this.mint(reference, sid, now, verified.classes, now, expiresAt));
  }

  // ---- Sign-ins (§2.4) -------------------------------------------------------

  /**
   * O3 for a verified token: its sign-in record is `live`, it names the same
   * principal, and the principal is `active`. Anything else is
   * `credential_refused`.
   */
  async checkSignIn(claims: SignInClaims): Promise<boolean> {
    const [row] = await this.d.store.query<{
      principal: string;
      state: string;
      principal_state: string;
    }>(SQL.signInWithPrincipal, [claims.sid, this.d.organization]);
    return (
      row !== undefined &&
      row.state === 'live' &&
      row.principal === claims.principal &&
      row.principal_state === 'active'
    );
  }

  /** A new token for the same sign-in (BR-SI-04, 05). The caller has run O1 to O3. */
  async renewSignIn(claims: SignInClaims): Promise<Result<IssuedSignIn>> {
    if (this.d.secondFactorRequired && !claims.classes.includes('P'))
      return refuse({ code: 'second_factor_enrollment_required' });
    const now = this.d.clock.now();
    const expiresAt = this.d.lifetimes.signInExpiry(claims.authenticatedAt);
    const renewed = await this.d.store.query(SQL.renewSignIn, [
      claims.sid,
      this.d.organization,
      expiresAt,
    ]);
    if (renewed.length !== 1) return refuse({ code: 'credential_refused' });
    const reference = { organization: this.d.organization, principal: claims.principal };
    return ok(
      await this.mint(
        reference,
        claims.sid,
        claims.authenticatedAt,
        claims.classes,
        now,
        expiresAt,
      ),
    );
  }

  /** The logout (BR-SI-06). The caller has run O1 to O3. */
  async endSignIn(claims: SignInClaims): Promise<Result<undefined>> {
    const ended = await this.d.store.query(SQL.endSignIn, [
      claims.sid,
      this.d.organization,
      this.d.clock.now(),
    ]);
    return ended.length === 1 ? ok(undefined) : refuse({ code: 'credential_refused' });
  }

  // ---- Material change (§2.5, 2.6) -------------------------------------------

  async changeMaterial(
    reference: PrincipalReference,
    current: { secret: string; secondFactor?: SecondFactorProof },
    change: MaterialChange,
  ): Promise<Result<MaterialChangeResult>> {
    const admission = await this.d.bound.admit(reference);
    if (!admission.admitted) return this.boundRefused(reference, 'changeMaterial', admission);
    const { reservation } = admission;

    const verified = await this.verifyCurrent(reference, current.secret, current.secondFactor);
    if (!verified) return this.failed(reference, 'changeMaterial', reservation);
    // The current material verified: what follows is not counted (BR-AB-03),
    // and the P requirement never applies here (BR-P-10).
    await this.d.bound.settleSuccess(reservation);

    switch (change.type) {
      case 'replaceSecret':
        return this.replaceSecret(reference, current.secret, change.newSecret, verified.kId);
      case 'beginSecondFactor':
        return this.beginSecondFactor(reference);
      case 'confirmSecondFactor':
        return this.confirmSecondFactor(reference, change.enrollment, change.proof);
    }
  }

  private async replaceSecret(
    reference: PrincipalReference,
    currentSecret: string,
    newSecret: string,
    kId: string,
  ): Promise<Result<MaterialChangeResult>> {
    const policy = this.d.policy.check(asSecretText(newSecret), {
      reference,
      replaces: asSecretText(currentSecret),
    });
    if (!policy.accepted)
      return refuse({
        code: 'secret_rejected',
        pointer: '/change/newSecret',
        reason: policy.reason,
      });
    const verifier = await this.d.hasher.hash(policy.secret);
    const now = this.d.clock.now();
    const ended = await this.d.store.transaction(async (tx) => {
      const retired = await tx.query(SQL.retireMaterial, [kId, now]);
      if (retired.length !== 1) return undefined; // changed by a concurrent call
      await tx.query(SQL.insertActiveK, [
        newId(),
        reference.organization,
        reference.principal,
        verifier,
        now,
      ]);
      await tx.query(SQL.removePending, [reference.organization, reference.principal]);
      return this.endAllSignIns(tx, reference, now);
    });
    if (ended === undefined) return refuse({ code: 'authentication_failed' });
    return ok({ type: 'replaceSecret', retired: ['K'], signInsEnded: ended });
  }

  private async beginSecondFactor(
    reference: PrincipalReference,
  ): Promise<Result<MaterialChangeResult>> {
    const id = newId();
    const seed = newSeed();
    const expiresAt = this.d.lifetimes.pendingSecondFactorExpiry();
    await this.d.store.query(SQL.upsertPending, [
      reference.organization,
      reference.principal,
      id,
      'totp',
      JSON.stringify(encryptSeed(seed, reference, id, this.d.keys)),
      expiresAt,
    ]);
    return ok({
      type: 'beginSecondFactor',
      enrollment: {
        id,
        expiresAt,
        setup: {
          type: 'totp',
          seed: base32(seed),
          otpauthUri: otpauthUri(seed, reference.organization, reference.principal),
        },
      },
    });
  }

  private async confirmSecondFactor(
    reference: PrincipalReference,
    enrollmentId: string,
    proof: SecondFactorProof,
  ): Promise<Result<MaterialChangeResult>> {
    const notConfirmed = refuse<MaterialChangeResult>({ code: 'second_factor_not_confirmed' });
    const now = this.d.clock.now();
    const [pending] = await this.d.store.query<PendingRow>(SQL.pendingFor, [
      reference.organization,
      reference.principal,
    ]);
    if (!pending || pending.id !== enrollmentId || pending.expires_at.getTime() <= now.getTime())
      return notConfirmed;
    if (proof.type !== pending.authenticator_type) return notConfirmed;
    let seed;
    try {
      seed = decryptSeed(pending.seed, reference, pending.id, this.d.keys);
    } catch (error) {
      if (error instanceof SeedDecryptionError) return notConfirmed;
      throw error;
    }
    const step = matchStep(seed, asTotpCode(proof.code), now, null);
    if (step === undefined) return notConfirmed;

    const materialId = newId();
    const stored = JSON.stringify(encryptSeed(seed, reference, materialId, this.d.keys));
    const outcome = await this.d.store.transaction(async (tx) => {
      const removed = await tx.query(SQL.removePendingById, [
        reference.organization,
        reference.principal,
        pending.id,
      ]);
      if (removed.length !== 1) return undefined; // confirmed or replaced concurrently
      const [old] = await tx.query<{ id: string }>(SQL.activeMaterialId, [
        reference.organization,
        reference.principal,
        'P',
      ]);
      if (old) await tx.query(SQL.retireMaterial, [old.id, now]);
      await tx.query(SQL.insertActiveP, [
        materialId,
        reference.organization,
        reference.principal,
        pending.authenticator_type,
        stored,
        step,
        now,
      ]);
      const ended = await this.endAllSignIns(tx, reference, now);
      return { retired: old ? (['P'] as MaterialClass[]) : [], ended };
    });
    if (!outcome) return notConfirmed;
    return ok({
      type: 'confirmSecondFactor',
      retired: outcome.retired,
      signInsEnded: outcome.ended,
    });
  }

  // ---- The internal interface (§2.7; BR-INT-03 to 06): read-only -------------

  async principalExists(reference: PrincipalReference): Promise<boolean> {
    return this.exists(reference);
  }

  async signInStatus(id: string): Promise<'live' | 'ended' | 'unknown'> {
    const [row] = await this.d.store.query<{ state: 'live' | 'ended' }>(SQL.signInState, [
      id,
      this.d.organization,
    ]);
    return row?.state ?? 'unknown';
  }

  verifyOnlyMaterial(): ReturnType<KeyRing['jwks']> {
    return this.d.keys.jwks();
  }

  // ---- Shared steps ----------------------------------------------------------

  /**
   * Verifies the current material: an `active` K, and, once P is `active`, a P
   * proof, whose step is then accepted at most once. A P proof where P is not
   * `active` fails (BR-P-07). Enrollment material never passes here (BR-MC-05).
   */
  private async verifyCurrent(
    reference: PrincipalReference,
    secret: string,
    secondFactor: SecondFactorProof | undefined,
  ): Promise<{ kId: string; classes: MaterialClass[] } | undefined> {
    const k = await this.d.resolver.resolve('K', reference, secret);
    if (!k.resolved) return undefined;
    const [p] = await this.d.store.query<{ id: string }>(SQL.activeMaterialId, [
      reference.organization,
      reference.principal,
      'P',
    ]);
    if (!p) return secondFactor ? undefined : { kId: k.materialId, classes: ['K'] };
    if (!secondFactor) return undefined;
    const resolved = await this.d.resolver.resolve('P', reference, secondFactor);
    if (!resolved.resolved || resolved.acceptedStep === undefined) return undefined;
    const accepted = await this.d.store.query(SQL.acceptStep, [
      resolved.materialId,
      resolved.acceptedStep,
    ]);
    if (accepted.length !== 1) return undefined; // the code was used concurrently
    return { kId: k.materialId, classes: ['K', 'P'] };
  }

  private async endAllSignIns(
    tx: Queryable,
    reference: PrincipalReference,
    now: Date,
  ): Promise<number> {
    const ended = await tx.query(SQL.endSignInsForMaterialChange, [
      reference.organization,
      reference.principal,
      now,
    ]);
    return ended.length;
  }

  private async mint(
    reference: PrincipalReference,
    sid: string,
    authenticatedAt: Date,
    classes: MaterialClass[],
    issuedAt: Date,
    expiresAt: Date,
  ): Promise<IssuedSignIn> {
    const { token, claims } = await mintSignIn(
      { ...reference, sid, authenticatedAt, classes, issuedAt, expiresAt },
      this.d.keys,
    );
    return {
      token,
      sid,
      expiresAt: claims.expiresAt,
      subject: { ...reference },
      authenticatedAt: claims.authenticatedAt,
      classes: claims.classes,
    };
  }

  private async exists(reference: HumanPrincipalReference): Promise<boolean> {
    const rows = await this.d.store.query(SQL.principalState, [
      reference.organization,
      reference.principal,
    ]);
    return rows.length === 1;
  }

  /**
   * A failure to authenticate: counted on the response path for every
   * reference; a Failed Attempt queued, off the response path, only for an
   * existing principal (BR-RF-03; D-OI-16, 27).
   */
  private async failed<T>(
    reference: PrincipalReference,
    surface: Surface,
    reservation: unknown,
  ): Promise<Result<T>> {
    await this.d.bound.settleFailure(reservation);
    await this.recordIfExists(reference, surface, false);
    return refuse({ code: 'authentication_failed' });
  }

  private async boundRefused<T>(
    reference: PrincipalReference,
    surface: Surface,
    admission: { retryAfterSeconds: number },
  ): Promise<Result<T>> {
    await this.recordIfExists(reference, surface, true); // BR-AB-07
    return refuse({ code: 'too_many_attempts', retryAfterSeconds: admission.retryAfterSeconds });
  }

  private async recordIfExists(
    reference: PrincipalReference,
    surface: Surface,
    refusedByBound: boolean,
  ): Promise<void> {
    if (await this.exists(reference))
      this.d.failures.record({
        organization: reference.organization,
        principal: reference.principal,
        surface,
        at: this.d.clock.now(),
        refusedByBound,
      });
  }
}
