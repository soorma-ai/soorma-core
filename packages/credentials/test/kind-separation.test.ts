// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-AC-082 (U4's verifier's half; NP-AC-09; D-AC-03): an agent credential's
// JWS presented behind U4's `soorma_ec_` prefix is refused by U4's
// verifyEnvironmentCredential, by its typ. A new file: U4's token.test.ts is
// not changed (stop condition 3).
import { generateKeyPairSync } from 'node:crypto';
import { asSecretBytes, asSecretText } from '@soorma/service-kit';
import { describe, expect, it } from 'vitest';
import {
  loadEnvironmentKeyRing,
  mintAgentCredential,
  verifyEnvironmentCredential,
} from '../src/index.ts';

const E = { organization: 'o1', project: 'p1', environment: 'e' };
const T0 = new Date('2026-11-12T08:00:00Z');

describe('TC-AC-082: an agent token is never a human environment credential', () => {
  it("U4's verifier refuses an agent token's JWS behind soorma_ec_, even with the same key", async () => {
    const { privateKey } = generateKeyPairSync('ed25519');
    const pem = asSecretBytes(Buffer.from(privateKey.export({ format: 'pem', type: 'pkcs8' })));
    const ring = loadEnvironmentKeyRing({ signing: 'k', verify: [{ name: 'k', pem }] });
    const agent = await mintAgentCredential(
      {
        environment: E,
        agent: 'a',
        instance: 'i-1',
        cid: 'c',
        jti: 'j',
        issuedAt: T0,
        expiresAt: new Date(T0.getTime() + 60_000),
      },
      ring,
    );
    const forged = asSecretText('soorma_ec_' + agent.slice('soorma_ac_'.length));
    expect(await verifyEnvironmentCredential(forged, ring, E, T0)).toMatchObject({
      ok: false,
      code: 'credential_refused',
    });
  });
});
