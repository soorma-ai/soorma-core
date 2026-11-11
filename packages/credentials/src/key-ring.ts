// SPDX-License-Identifier: FSL-1.1-ALv2
//
// An environment's own key ring (NP-EHA-02; ID §6; PF §6). One signing key and
// a set of verify keys, each Ed25519, with kid = its RFC 7638 thumbprint, from
// the environment's configuration. Built once at start-up and held in memory;
// no key is written to the store, and nothing is published: only E's own S2
// instances verify E's credentials.
//
// Start-up fails closed (D-EHA-28) on a key that is not an Ed25519 private key
// in PKCS #8 PEM, on a signing key that is not among the verify keys, and on
// two verify entries holding one key.
import { createPrivateKey, createPublicKey, type KeyObject } from 'node:crypto';
import { KeyMaterialError, thumbprint, type SecretBytes } from '@soorma/service-kit';

export interface EnvironmentKeyRing {
  readonly signingKey: KeyObject;
  readonly signingKid: string;
  readonly kids: readonly string[];
  verifyKey(kid: string): KeyObject | undefined;
}

function privateEd25519(pem: SecretBytes, name: string, problems: string[]): KeyObject | undefined {
  try {
    const key = createPrivateKey(pem);
    if (key.asymmetricKeyType !== 'ed25519') {
      problems.push(`${name} is not an Ed25519 key`);
      return undefined;
    }
    return key;
  } catch {
    problems.push(`${name} is not a PEM private key`);
    return undefined;
  }
}

/**
 * The ring, from the configured secrets: `signing` names one of `verify`
 * (`signingIndex`), so rotation is a configuration change in three steps.
 */
export function loadEnvironmentKeyRing(input: {
  verify: readonly { name: string; pem: SecretBytes }[];
  signing: string;
}): EnvironmentKeyRing {
  const problems: string[] = [];
  const keys = new Map<string, KeyObject>();
  let signing: { key: KeyObject; kid: string } | undefined;
  for (const { name, pem } of input.verify) {
    const key = privateEd25519(pem, name, problems);
    if (!key) continue;
    const kid = thumbprint(createPublicKey(key));
    if (keys.has(kid)) {
      problems.push(`verify key ${name} repeats a key already configured (kid ${kid})`);
      continue;
    }
    keys.set(kid, createPublicKey(key));
    if (name === input.signing) signing = { key, kid };
  }
  if (input.verify.length === 0) problems.push('no verify key is configured');
  if (!input.verify.some((v) => v.name === input.signing))
    problems.push(`the signing key ${input.signing} is not among the verify keys`);
  if (problems.length > 0 || !signing) throw new KeyMaterialError(problems);
  const { key, kid } = signing;
  return Object.freeze({
    signingKey: key,
    signingKid: kid,
    kids: Object.freeze([...keys.keys()]),
    verifyKey: (k: string) => keys.get(k),
  });
}
