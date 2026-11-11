// SPDX-License-Identifier: FSL-1.1-ALv2
// TC-OI-057 (stack:init's half): secrets are generated safely: each 0600,
// never overwritten, enrollment material only in its secret and the one-time
// handover file; and TC-OI-056's certificate half: a name-constrained CA, and
// leaves that verify against it.
import { execFileSync } from 'node:child_process';
import { createPrivateKey, createPublicKey } from 'node:crypto';
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stackInit } from '../local/scripts/stack-init.ts';

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

describe('TC-OI-057: stack:init generates secrets safely', () => {
  it('writes every named secret 0600, and never overwrites one', () => {
    const dir = fresh();
    const first = stackInit({ dir });
    expect(first.created).toEqual(
      expect.arrayContaining([
        'org-enrollment-1',
        'org-signing-key',
        'org-counter-secret',
        'org-log-pseudonym-key',
        'org-db-app-password',
        'org-db-migrator-password',
        'org-db-superuser-password',
        'org-gateway-tls',
        'org-db-tls',
        'stack-ca-cert',
      ]),
    );
    const files = readdirSync(dir).filter((f) => f !== 'handover');
    for (const f of files) expect(modeOf(join(dir, f)), f).toBe(0o600);
    const before = Object.fromEntries(files.map((f) => [f, readFileSync(join(dir, f), 'utf8')]));
    const second = stackInit({ dir });
    expect(second.created).toEqual([]);
    expect(second.handover).toEqual([]);
    for (const f of files) expect(readFileSync(join(dir, f), 'utf8'), f).toBe(before[f]);
  });

  it('puts enrollment material only in its secret and the handover file, by index', () => {
    const dir = fresh();
    const result = stackInit({ dir });
    const material = readFileSync(join(dir, 'org-enrollment-1'), 'utf8').trim();
    expect(material).toMatch(/^soorma_em_[A-Za-z0-9_-]{43}$/);
    expect(result.handover).toEqual([join(dir, 'handover', 'first-admin-1.txt')]);
    expect(modeOf(result.handover[0]!)).toBe(0o600);
    expect(readFileSync(result.handover[0]!, 'utf8')).toContain(material);
    expect(JSON.stringify(result)).not.toContain(material);
    expect(createPrivateKey(readFileSync(join(dir, 'org-signing-key'))).asymmetricKeyType).toBe(
      'ed25519',
    );
    expect(readFileSync(join(dir, 'org-counter-secret'), 'utf8').trim()).not.toBe(
      readFileSync(join(dir, 'org-log-pseudonym-key'), 'utf8').trim(),
    );
  });
});

describe('TC-OI-056 (certificates): a name-constrained CA, and leaves that verify', () => {
  it('constrains the CA to localhost, soorma.internal, and loopback, critically', () => {
    const dir = fresh();
    stackInit({ dir });
    const ca = execFileSync(
      'openssl',
      ['x509', '-in', join(dir, 'stack-ca.pem'), '-noout', '-text'],
      {
        encoding: 'utf8',
      },
    );
    expect(ca).toContain('X509v3 Name Constraints: critical');
    expect(ca).toContain('DNS:soorma.internal');
    expect(ca).toContain('pathlen:0');
    const verified = execFileSync(
      'openssl',
      [
        'verify',
        '-CAfile',
        join(dir, 'stack-ca.pem'),
        join(dir, 'org-gateway-tls'),
        join(dir, 'org-db-tls'),
      ],
      { encoding: 'utf8' },
    );
    expect(verified).toMatch(/org-gateway-tls: OK/);
    expect(verified).toMatch(/org-db-tls: OK/);
  });
});

describe("U4 Infrastructure Design §3: each environment's secrets", () => {
  const ENV_SECRETS = (env: string): string[] => [
    `${env}-signing-key-1`,
    `${env}-caller-key`,
    `${env}-caller-public-key`,
    `${env}-log-pseudonym-key`,
    `${env}-db-app-password`,
    `${env}-db-migrator-password`,
    `${env}-db-superuser-password`,
    `${env}-control-gateway-tls`,
    `${env}-db-tls`,
  ];

  it('generates every E and E2 secret, 0600, distinct per environment', () => {
    const dir = fresh();
    const result = stackInit({ dir });
    expect(result.created).toEqual(
      expect.arrayContaining([...ENV_SECRETS('e'), ...ENV_SECRETS('e2')]),
    );
    for (const name of [...ENV_SECRETS('e'), ...ENV_SECRETS('e2')])
      expect(modeOf(join(dir, name)), name).toBe(0o600);
    for (const name of ['signing-key-1', 'caller-key', 'log-pseudonym-key', 'db-app-password'])
      expect(readFileSync(join(dir, `e-${name}`), 'utf8'), name).not.toBe(
        readFileSync(join(dir, `e2-${name}`), 'utf8'),
      );
    for (const env of ['e', 'e2'])
      for (const name of ['signing-key-1', 'caller-key'])
        expect(
          createPrivateKey(readFileSync(join(dir, `${env}-${name}`))).asymmetricKeyType,
          `${env}-${name}`,
        ).toBe('ed25519');
    expect(readFileSync(join(dir, 'e-log-pseudonym-key'), 'utf8')).not.toBe(
      readFileSync(join(dir, 'org-log-pseudonym-key'), 'utf8'),
    );
  });

  it('derives each caller PUBLIC key from its private key, as SPKI PEM, holding no private part', () => {
    const dir = fresh();
    stackInit({ dir });
    for (const env of ['e', 'e2']) {
      const pub = readFileSync(join(dir, `${env}-caller-public-key`), 'utf8');
      expect(pub).toMatch(/^-----BEGIN PUBLIC KEY-----/);
      expect(pub).not.toContain('PRIVATE');
      const derived = createPublicKey(
        createPrivateKey(readFileSync(join(dir, `${env}-caller-key`))),
      ).export({ format: 'pem', type: 'spki' });
      expect(pub).toBe(derived);
    }
  });

  it('refuses a caller public key that no longer matches its private key, and names only the files', () => {
    const dir = fresh();
    stackInit({ dir });
    const other = createPublicKey(
      createPrivateKey(readFileSync(join(dir, 'e2-caller-key'))),
    ).export({
      format: 'pem',
      type: 'spki',
    });
    writeFileSync(join(dir, 'e-caller-public-key'), other, { mode: 0o600 });
    expect(() => stackInit({ dir })).toThrow(
      'e-caller-public-key does not match e-caller-key: remove it and run stack:init again',
    );
  });

  it("each environment's certificates verify against the local CA, under its own names", () => {
    const dir = fresh();
    stackInit({ dir });
    for (const env of ['e', 'e2']) {
      const verified = execFileSync(
        'openssl',
        [
          'verify',
          '-CAfile',
          join(dir, 'stack-ca.pem'),
          join(dir, `${env}-control-gateway-tls`),
          join(dir, `${env}-db-tls`),
        ],
        { encoding: 'utf8' },
      );
      expect(verified).toMatch(new RegExp(`${env}-control-gateway-tls: OK`));
      expect(verified).toMatch(new RegExp(`${env}-db-tls: OK`));
      const text = execFileSync(
        'openssl',
        [
          'x509',
          '-in',
          join(dir, `${env}-control-gateway-tls`),
          '-noout',
          '-ext',
          'subjectAltName',
        ],
        { encoding: 'utf8' },
      );
      expect(text).toContain(`DNS:control-gateway.${env}.soorma.internal`);
    }
  });
});
