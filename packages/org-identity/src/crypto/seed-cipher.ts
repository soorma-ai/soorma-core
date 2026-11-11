// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Seed encryption (P-03; NFR-OI-09): AES-256-GCM in the application, a 96-bit
// random nonce per encryption, and associated data binding the ciphertext to
// its row (the principal reference and the record's id), so a ciphertext
// copied to another row fails to decrypt. Decryption uses the key its `keyId`
// names (R-3); an unknown key id fails closed.
import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';
import { canonicalJson, type PrincipalReference } from './canonical.ts';
import type { KeyRing } from './key-ring.ts';
import { asSecretBytes, type SecretBytes } from './secret-types.ts';

export interface StoredSeed {
  keyId: string;
  nonce: string;
  ciphertext: string;
  tag: string;
}

export class SeedDecryptionError extends Error {
  constructor() {
    super('the seed cannot be decrypted');
    this.name = 'SeedDecryptionError';
  }
}

export function associatedData(reference: PrincipalReference, recordId: string): Buffer {
  return Buffer.from(
    canonicalJson({
      organization: reference.organization,
      principal: reference.principal,
      recordId,
    }),
    'utf8',
  );
}

export function encryptSeed(
  seed: SecretBytes,
  reference: PrincipalReference,
  recordId: string,
  keys: KeyRing,
): StoredSeed {
  const keyId = keys.currentSeedKeyId;
  const key = keys.seedKey(keyId);
  if (!key) throw new SeedDecryptionError();
  const nonce = randomBytes(12);
  const cipher = createCipheriv('aes-256-gcm', key, nonce);
  cipher.setAAD(associatedData(reference, recordId));
  const ciphertext = Buffer.concat([cipher.update(seed), cipher.final()]);
  return {
    keyId,
    nonce: nonce.toString('base64url'),
    ciphertext: ciphertext.toString('base64url'),
    tag: cipher.getAuthTag().toString('base64url'),
  };
}

export function decryptSeed(
  stored: StoredSeed,
  reference: PrincipalReference,
  recordId: string,
  keys: KeyRing,
): SecretBytes {
  const key = keys.seedKey(stored.keyId);
  if (!key) throw new SeedDecryptionError();
  try {
    const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(stored.nonce, 'base64url'));
    decipher.setAAD(associatedData(reference, recordId));
    decipher.setAuthTag(Buffer.from(stored.tag, 'base64url'));
    const seed = Buffer.concat([
      decipher.update(Buffer.from(stored.ciphertext, 'base64url')),
      decipher.final(),
    ]);
    return asSecretBytes(seed);
  } catch {
    throw new SeedDecryptionError();
  }
}
