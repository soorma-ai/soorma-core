// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-AC-089 (U6 D-ID-AC-03, 05, 06, 08): `stack:init` generates U6's secrets
// safely, beside U4's (stack-init.test.ts, unchanged): each environment's agent
// signing key (Ed25519) and its matching verify half, the bound's counter
// secret (256 bits), the data role's password, and S3's TLS leaf; 0600,
// distinct per environment, never overwritten; a mismatched verify half is
// refused. And TC-AC-020's key half: E's and E2's agent keys differ.
import { execFileSync } from 'node:child_process';
import {
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
  type KeyObject,
} from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stackInit, verifyHalfOf } from '../local/scripts/stack-init.ts';

const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

function fresh(): string {
  const dir = mkdtempSync(join(tmpdir(), 'soorma-stack-'));
  dirs.push(dir);
  return dir;
}

const modeOf = (path: string): number => statSync(path).mode & 0o777;
const U6_SECRETS = (env: string): string[] => [
  `${env}-agent-signing-key-1`,
  `${env}-agent-verify-key-1`,
  `${env}-bootstrap-counter-secret`,
  `${env}-db-data-password`,
  `${env}-data-gateway-tls`,
];
const spki = (key: KeyObject): string => key.export({ format: 'pem', type: 'spki' }).toString();

describe('TC-AC-089: stack:init generates U6’s secrets safely', () => {
  it('each environment’s five, 0600, distinct per environment, never overwritten', () => {
    const dir = fresh();
    const first = stackInit({ dir });
    expect(first.created).toEqual(
      expect.arrayContaining([...U6_SECRETS('e'), ...U6_SECRETS('e2')]),
    );
    for (const name of [...U6_SECRETS('e'), ...U6_SECRETS('e2')])
      expect(modeOf(join(dir, name)), name).toBe(0o600);
    for (const name of ['agent-signing-key-1', 'bootstrap-counter-secret', 'db-data-password'])
      expect(readFileSync(join(dir, `e-${name}`), 'utf8'), name).not.toBe(
        readFileSync(join(dir, `e2-${name}`), 'utf8'),
      );
    const before = Object.fromEntries(
      [...U6_SECRETS('e'), ...U6_SECRETS('e2')].map((n) => [n, readFileSync(join(dir, n), 'utf8')]),
    );
    const second = stackInit({ dir });
    expect(second.created).toEqual([]);
    for (const [n, text] of Object.entries(before))
      expect(readFileSync(join(dir, n), 'utf8'), n).toBe(text);
  });

  it('the signing key is Ed25519 and its verify half matches it; the counter is 256 bits', () => {
    const dir = fresh();
    stackInit({ dir });
    for (const env of ['e', 'e2']) {
      const key = createPrivateKey(readFileSync(join(dir, `${env}-agent-signing-key-1`)));
      expect(key.asymmetricKeyType).toBe('ed25519');
      expect(readFileSync(join(dir, `${env}-agent-verify-key-1`), 'utf8')).toBe(
        spki(createPublicKey(key)),
      );
      const counter = readFileSync(join(dir, `${env}-bootstrap-counter-secret`), 'utf8').trim();
      expect(Buffer.from(counter, 'base64url')).toHaveLength(32);
    }
    // The agent ring is not the human ring.
    expect(readFileSync(join(dir, 'e-agent-signing-key-1'), 'utf8')).not.toBe(
      readFileSync(join(dir, 'e-signing-key-1'), 'utf8'),
    );
  });

  it('a verify half that no longer matches its key refuses the run', () => {
    const dir = fresh();
    stackInit({ dir });
    writeFileSync(
      join(dir, 'e-agent-verify-key-1'),
      spki(generateKeyPairSync('ed25519').publicKey),
      { mode: 0o600 },
    );
    expect(() => stackInit({ dir })).toThrow(
      'e-agent-verify-key-1 does not match e-agent-signing-key-1',
    );
  });

  it('S3’s TLS leaf names data-gateway.{env}.soorma.internal and verifies against the CA', () => {
    const dir = fresh();
    stackInit({ dir });
    for (const env of ['e', 'e2']) {
      const leaf = join(dir, `${env}-data-gateway-tls`);
      const text = execFileSync(
        'openssl',
        ['x509', '-in', leaf, '-noout', '-ext', 'subjectAltName'],
        {
          encoding: 'utf8',
        },
      );
      expect(text).toContain(`DNS:data-gateway.${env}.soorma.internal`);
      expect(
        execFileSync('openssl', ['verify', '-CAfile', join(dir, 'stack-ca.pem'), leaf], {
          encoding: 'utf8',
        }),
      ).toMatch(/OK/);
    }
  });

  it('a verify half is named after its signing key', () => {
    expect(verifyHalfOf('e-agent-signing-key-1')).toBe('e-agent-verify-key-1');
    expect(verifyHalfOf('e2-agent-signing-key-12')).toBe('e2-agent-verify-key-12');
    expect(() => verifyHalfOf('e-signing-key-1')).toThrow();
  });
});
