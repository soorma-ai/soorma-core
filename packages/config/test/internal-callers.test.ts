// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-EHA-082 (the configuration half): internal callers list publicKeys, and a
// secret name names one key of one environment (U4 Infrastructure Design §4;
// I1). The kid checks over the loaded keys are P10's (org-identity).
import { randomBytes } from 'node:crypto';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stringify } from 'yaml';
import { ConfigurationError, listSecrets, loadOrganization } from '../src/index.ts';

const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

const MATERIAL = `soorma_em_${randomBytes(32).toString('base64url')}`;
const key = (): string => randomBytes(32).toString('base64url');

function tenancy(): Record<string, any> {
  return {
    organization: 'o1',
    secondFactorRequired: false,
    organizationLevel: {
      edge: { port: 8443, tls: 'org-gateway-tls' },
      internal: { port: 9443, tls: 'org-gateway-tls' },
      health: { port: 8080 },
      database: {
        host: 'org-db.soorma.internal',
        port: 5432,
        name: 'soorma_org',
        user: 'soorma_org_app',
        password: 'org-db-app-password',
        ca: 'stack-ca-cert',
      },
      migrator: { user: 'soorma_org_migrator', password: 'org-db-migrator-password' },
      keys: {
        signing: 'org-signing-key',
        seed: { current: 's1', keys: [{ id: 's1', secret: 'org-seed-key' }] },
        counter: 'org-counter-secret',
        logPseudonym: 'org-log-pseudonym-key',
      },
      enrollment: [{ principal: 'h@example.com', secret: 'org-enrollment-1' }],
      internalCallers: [
        { environment: 'e', publicKeys: ['env-e-caller-key'] },
        { environment: 'e2', publicKeys: ['env-e2-caller-key'] },
      ],
    },
    projects: [
      {
        id: 'p1',
        environments: [
          { id: 'e', firstAdmin: 'h@example.com' },
          { id: 'e2', firstAdmin: 'h@example.com' },
        ],
      },
    ],
  };
}

const gatewaySecrets: Record<string, string> = {
  'org-gateway-tls': 'PEM',
  'org-db-app-password': 'app-password',
  'stack-ca-cert': 'CA',
  'org-signing-key': 'SIGNING',
  'org-seed-key': key(),
  'org-counter-secret': key(),
  'org-log-pseudonym-key': key(),
  'org-enrollment-1': MATERIAL,
  'env-e-caller-key': 'CALLER',
  'env-e2-caller-key': 'CALLER2',
  'env-e-caller-key-2': 'CALLER3',
};

function setup(
  config: Record<string, any> = tenancy(),
  secrets: Record<string, string> = gatewaySecrets,
): { configPath: string; secretsDir: string } {
  const dir = mkdtempSync(join(tmpdir(), 'soorma-config-'));
  dirs.push(dir);
  const configPath = join(dir, 'tenancy.yaml');
  writeFileSync(configPath, stringify(config));
  for (const [name, value] of Object.entries(secrets)) writeFileSync(join(dir, name), value);
  return { configPath, secretsDir: dir };
}

function problems(fn: () => unknown): string[] {
  try {
    fn();
  } catch (error) {
    if (error instanceof ConfigurationError) return [...error.problems];
    throw error;
  }
  throw new Error('expected a ConfigurationError');
}

/** The internal callers of a test tenancy, typed. */
const callers = (config: Record<string, any>): { environment: string; publicKeys: string[] }[] =>
  config.organizationLevel.internalCallers as { environment: string; publicKeys: string[] }[];

describe('TC-EHA-082: internal callers, by publicKeys (Infrastructure Design §4)', () => {
  it('loads every listed key, in order, and lists each as a gateway secret', () => {
    const config = tenancy();
    callers(config)[0]!.publicKeys.push('env-e-caller-key-2');
    const paths = setup(config);
    const { secrets } = loadOrganization(paths);
    expect(secrets.internalCallers).toEqual([
      { environment: 'e', publicKeys: [Buffer.from('CALLER'), Buffer.from('CALLER3')] },
      { environment: 'e2', publicKeys: [Buffer.from('CALLER2')] },
    ]);
    expect(listSecrets(paths).gateway).toEqual(
      expect.arrayContaining(['env-e-caller-key', 'env-e-caller-key-2', 'env-e2-caller-key']),
    );
  });

  it('still refuses an environment listed twice', () => {
    const config = tenancy();
    callers(config)[1]!.environment = 'e';
    expect(problems(() => loadOrganization(setup(config))).join('\n')).toContain(
      'environment e appears twice',
    );
  });

  it('refuses a secret name listed twice within one environment', () => {
    const config = tenancy();
    callers(config)[0]!.publicKeys.push('env-e-caller-key');
    expect(problems(() => loadOrganization(setup(config)))).toEqual([
      '/organizationLevel/internalCallers/0/publicKeys/0: env-e-caller-key is listed more than once',
      '/organizationLevel/internalCallers/0/publicKeys/1: env-e-caller-key is listed more than once',
    ]);
  });

  it('refuses a secret name listed for two environments', () => {
    const config = tenancy();
    callers(config)[1]!.publicKeys = ['env-e-caller-key'];
    expect(problems(() => loadOrganization(setup(config)))).toEqual([
      '/organizationLevel/internalCallers/0/publicKeys/0: env-e-caller-key is listed more than once',
      '/organizationLevel/internalCallers/1/publicKeys/0: env-e-caller-key is listed more than once',
    ]);
  });

  it('refuses an empty publicKeys list (the schema)', () => {
    const config = tenancy();
    callers(config)[0]!.publicKeys = [];
    expect(problems(() => loadOrganization(setup(config))).length).toBeGreaterThan(0);
  });
});
