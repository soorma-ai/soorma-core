// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The key ring (P-02): every key comes from organization-level configuration,
// and none is ever written to the org store.
//
// - Signing key: one Ed25519 private key; never leaves the process
// - Verify keys: the signing key's public half and any configured further
//   public keys, each with its RFC 7638 thumbprint as `kid`; served as a JWKS
//   by verifyOnlyMaterial (BR-INT-03)
// - Seed-encryption keys: AES-256, by key id, one current (R-3: old keys stay)
// - Counter secret and log-pseudonym key: separate HMAC-SHA-256 keys
// - Environment caller keys: each configured environment's Ed25519 public key
//
// Any missing or malformed key stops start-up (BR-CFG-08).
import { createPrivateKey, createPublicKey, type KeyObject } from 'node:crypto';
import {
  asSecretBytes,
  KeyMaterialError,
  thumbprint,
  type CallerKey,
  type PublicJwk,
  type SecretBytes,
  type VerifyKey,
} from '@soorma/service-kit';

/** The raw key material, as configuration delivers it. */
export interface KeyMaterialInput {
  signingKey: Buffer;
  verifyKeys: Buffer[];
  seedKeys: { current: string; keys: { id: string; key: Buffer }[] };
  counterSecret: Buffer;
  logPseudonymKey: Buffer;
  internalCallers: { environment: string; publicKey: Buffer }[];
}

function ed25519Public(key: KeyObject): VerifyKey {
  const kid = thumbprint(key);
  const { x } = key.export({ format: 'jwk' });
  return {
    kid,
    key,
    jwk: { kty: 'OKP', crv: 'Ed25519', x: String(x), kid, alg: 'Ed25519', use: 'sig' },
  };
}

export class KeyRing {
  readonly signingKey: KeyObject;
  readonly signingKid: string;
  readonly verifyKeys: readonly VerifyKey[];
  readonly currentSeedKeyId: string;
  readonly counterSecret: SecretBytes;
  readonly logPseudonymKey: SecretBytes;
  readonly callers: readonly CallerKey[];
  private readonly seedKeys: ReadonlyMap<string, SecretBytes>;

  private constructor(fields: {
    signingKey: KeyObject;
    signingKid: string;
    verifyKeys: VerifyKey[];
    currentSeedKeyId: string;
    seedKeys: Map<string, SecretBytes>;
    counterSecret: SecretBytes;
    logPseudonymKey: SecretBytes;
    callers: CallerKey[];
  }) {
    this.signingKey = fields.signingKey;
    this.signingKid = fields.signingKid;
    this.verifyKeys = fields.verifyKeys;
    this.currentSeedKeyId = fields.currentSeedKeyId;
    this.seedKeys = fields.seedKeys;
    this.counterSecret = fields.counterSecret;
    this.logPseudonymKey = fields.logPseudonymKey;
    this.callers = fields.callers;
  }

  /** Builds the ring, or throws KeyMaterialError listing every problem. */
  static fromConfiguration(input: KeyMaterialInput): KeyRing {
    const problems: string[] = [];

    let signingKey: KeyObject | undefined;
    try {
      signingKey = createPrivateKey(input.signingKey);
      if (signingKey.asymmetricKeyType !== 'ed25519') {
        problems.push('the signing key is not an Ed25519 private key');
        signingKey = undefined;
      }
    } catch {
      problems.push('the signing key is not a PEM private key');
    }

    const verifyKeys: VerifyKey[] = [];
    if (signingKey) verifyKeys.push(ed25519Public(createPublicKey(signingKey)));
    for (const [i, pem] of input.verifyKeys.entries()) {
      try {
        const key = createPublicKey(pem);
        if (key.asymmetricKeyType !== 'ed25519') problems.push(`verify key ${i} is not Ed25519`);
        else verifyKeys.push(ed25519Public(key));
      } catch {
        problems.push(`verify key ${i} is not a PEM public key`);
      }
    }

    const seedKeys = new Map<string, SecretBytes>();
    for (const { id, key } of input.seedKeys.keys) {
      if (key.length !== 32) problems.push(`seed key ${id} is not 256 bits`);
      seedKeys.set(id, asSecretBytes(key));
    }
    if (!seedKeys.has(input.seedKeys.current))
      problems.push('the current seed key is not configured');
    if (input.counterSecret.length < 32) problems.push('the counter secret is under 256 bits');
    if (input.logPseudonymKey.length < 32) problems.push('the log-pseudonym key is under 256 bits');

    const callers: CallerKey[] = [];
    for (const { environment, publicKey } of input.internalCallers) {
      try {
        const key = createPublicKey(publicKey);
        if (key.asymmetricKeyType !== 'ed25519')
          problems.push(`the caller key for environment ${environment} is not Ed25519`);
        else callers.push({ environment, kid: thumbprint(key), key });
      } catch {
        problems.push(`the caller key for environment ${environment} is not a PEM public key`);
      }
    }

    if (problems.length > 0 || !signingKey) throw new KeyMaterialError(problems);
    return new KeyRing({
      signingKey,
      signingKid: verifyKeys[0]!.kid,
      verifyKeys,
      currentSeedKeyId: input.seedKeys.current,
      seedKeys,
      counterSecret: asSecretBytes(input.counterSecret),
      logPseudonymKey: asSecretBytes(input.logPseudonymKey),
      callers,
    });
  }

  /** The verify-only material environments hold (BR-INT-03): public keys only. */
  jwks(): { keys: PublicJwk[] } {
    return { keys: this.verifyKeys.map((k) => k.jwk) };
  }

  verifyKey(kid: string): KeyObject | undefined {
    return this.verifyKeys.find((k) => k.kid === kid)?.key;
  }

  seedKey(id: string): SecretBytes | undefined {
    return this.seedKeys.get(id);
  }

  callerByKid(kid: string): CallerKey | undefined {
    return this.callers.find((c) => c.kid === kid);
  }
}
