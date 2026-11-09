// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P6, identity resolution, human half: implements the seam over the org
// store's verifiers (BR-SEAM-01, 02; P-10).
//
// - K: the principal's `active` K, verified with Argon2id
// - enrollment: the principal's K record in state `enrollment`, verified the
//   same way (NFR-OI-11: enrollment material uses the same hash)
// - P: the principal's `active` P; the seed is decrypted and the TOTP code
//   matched within one step of drift, later than the last accepted step
//
// When the principal, or the record the type needs, is absent, K and
// enrollment verify against the decoy instead, so the work done does not
// depend on existence (BR-RF-03). It changes no record: single use, the
// accepted step, and every state change are P10's (BR-SEAM-02).
import {
  asSecretText,
  asTotpCode,
  asVerifier,
  decryptSeed,
  matchStep,
  SeedDecryptionError,
  type Clock,
  type KeyRing,
  type Queryable,
  type SecretHasher,
  type StoredSeed,
} from '@soorma/org-identity';
import type {
  HumanPrincipalReference,
  IdentityResolver,
  MaterialType,
  PresentedMaterial,
  Resolution,
} from '@soorma/identity-resolution-seam';
import { SQL } from './sql.ts';

interface MaterialRow {
  id: string;
  state: 'enrollment' | 'active';
  verifier: string | null;
  seed: StoredSeed | null;
  last_step: string | null;
}

const REJECTED: Resolution = { resolved: false };

export class StoreIdentityResolver implements IdentityResolver {
  private readonly store: Queryable;
  private readonly hasher: SecretHasher;
  private readonly keys: KeyRing;
  private readonly clock: Clock;

  constructor(store: Queryable, hasher: SecretHasher, keys: KeyRing, clock: Clock) {
    this.store = store;
    this.hasher = hasher;
    this.keys = keys;
    this.clock = clock;
  }

  async resolve<T extends MaterialType>(
    type: T,
    reference: HumanPrincipalReference,
    material: PresentedMaterial[T],
  ): Promise<Resolution> {
    if (type === 'P') return this.resolveP(reference, material as PresentedMaterial['P']);
    const wanted = type === 'K' ? 'active' : 'enrollment';
    const secret = asSecretText(material as string);
    const row = await this.current(reference, 'K');
    if (!row || row.state !== wanted || row.verifier === null) {
      await this.hasher.verifyDecoy(secret);
      return REJECTED;
    }
    return (await this.hasher.verify(secret, asVerifier(row.verifier)))
      ? { resolved: true, principal: { ...reference }, materialId: row.id }
      : REJECTED;
  }

  private async resolveP(
    reference: HumanPrincipalReference,
    proof: PresentedMaterial['P'],
  ): Promise<Resolution> {
    const row = await this.current(reference, 'P');
    if (!row || row.state !== 'active' || row.seed === null || proof.type !== 'totp')
      return REJECTED;
    let seed;
    try {
      seed = decryptSeed(row.seed, reference, row.id, this.keys);
    } catch (error) {
      if (error instanceof SeedDecryptionError) return REJECTED;
      throw error;
    }
    const step = matchStep(
      seed,
      asTotpCode(proof.code),
      this.clock.now(),
      row.last_step === null ? null : Number(row.last_step),
    );
    return step === undefined
      ? REJECTED
      : { resolved: true, principal: { ...reference }, materialId: row.id, acceptedStep: step };
  }

  private async current(
    reference: HumanPrincipalReference,
    materialClass: 'K' | 'P',
  ): Promise<MaterialRow | undefined> {
    const [row] = await this.store.query<MaterialRow>(SQL.currentMaterial, [
      reference.organization,
      reference.principal,
      materialClass,
    ]);
    return row;
  }
}
