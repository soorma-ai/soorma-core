// SPDX-License-Identifier: FSL-1.1-ALv2
//
// TC-EHA-036 (the configuration half): an environment's S2 part (U4
// Infrastructure Design §3; P-06). S2 reads only its own environment's part
// and secrets, never the migrator password; a secret is never shared between
// environments, or with the organization level, other than the CA certificate.
import { randomBytes } from 'node:crypto';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stringify } from 'yaml';
import {
  ConfigurationError,
  listSecrets,
  loadControlGateway,
  loadEnvironmentMigrator,
  loadOrganization,
} from '../src/index.ts';

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
          { id: 'e', firstAdmin: 'h@example.com', controlGateway: part('e') },
          { id: 'e2', firstAdmin: 'h@example.com', controlGateway: part('e2') },
        ],
      },
    ],
  };
}

function part(env: string): Record<string, any> {
  return {
    edge: { port: 8443, tls: `${env}-control-gateway-tls` },
    health: { port: 8080 },
    database: {
      host: `env-db.${env}.soorma.internal`,
      port: 5432,
      name: 'soorma_env',
      user: 'soorma_env_app',
      password: `${env}-db-app-password`,
      ca: 'stack-ca-cert',
    },
    migrator: { user: 'soorma_env_migrator', password: `${env}-db-migrator-password` },
    keys: {
      signing: `${env}-signing-key-1`,
      verify: [`${env}-signing-key-1`],
      caller: `${env}-caller-key`,
      logPseudonym: `${env}-log-pseudonym-key`,
    },
    organizationLevel: { host: 'org-gateway.soorma.internal', port: 9443, ca: 'stack-ca-cert' },
  };
}

const envSecrets = (env: string): Record<string, string> => ({
  [`${env}-control-gateway-tls`]: `TLS-${env}`,
  [`${env}-db-app-password`]: `app-${env}`,
  [`${env}-db-migrator-password`]: `migrator-${env}`,
  [`${env}-signing-key-1`]: `SIGNING-${env}`,
  [`${env}-caller-key`]: `CALLER-${env}`,
  [`${env}-log-pseudonym-key`]: key(),
});

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
  ...envSecrets('e'),
  ...envSecrets('e2'),
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

type Part = { keys: { signing: string; verify: string[]; caller: string; logPseudonym: string } };
const env = (config: Record<string, any>, i: number): { controlGateway: Part } =>
  (config.projects as { environments: { controlGateway: Part }[] }[])[0]!.environments[i]!;

const E = { project: 'p1', environment: 'e' };

describe("TC-EHA-036: S2 loads only its own environment's part", () => {
  it("loads E's settings and secrets, and none of E2's or the migrator's", () => {
    const { settings, secrets } = loadControlGateway(setup(), E);
    expect(settings).toEqual({
      organization: 'o1',
      project: 'p1',
      environment: 'e',
      firstAdmin: 'h@example.com',
      edge: { port: 8443 },
      health: { port: 8080 },
      database: {
        host: 'env-db.e.soorma.internal',
        port: 5432,
        name: 'soorma_env',
        user: 'soorma_env_app',
      },
      organizationLevel: { host: 'org-gateway.soorma.internal', port: 9443 },
    });
    expect(secrets.databasePassword).toBe('app-e');
    expect(secrets.verifyKeys).toEqual([
      { name: 'e-signing-key-1', pem: Buffer.from('SIGNING-e') },
    ]);
    expect(secrets.signing).toBe('e-signing-key-1');
    expect(secrets.callerKey.toString()).toBe('CALLER-e');
    expect(JSON.stringify(secrets)).not.toContain('migrator-e');
    expect(JSON.stringify(secrets)).not.toContain('-e2');
  });

  it('{env}-migrate loads the migrator password and the CA, nothing else', () => {
    const m = loadEnvironmentMigrator(setup(), E);
    expect(m.database.user).toBe('soorma_env_migrator');
    expect(m.databasePassword).toBe('migrator-e');
    expect(m.databaseCa.toString()).toBe('CA');
  });

  it("lists each environment's secrets for stack:init, by who reads them", () => {
    const names = listSecrets(setup());
    const e = names.environments.find((x) => x.environment === 'e')!;
    expect(e.controlGateway).not.toContain('e-db-migrator-password');
    expect(e.migrator).toEqual(['e-db-migrator-password', 'stack-ca-cert']);
    expect(e.ed25519).toEqual(['e-signing-key-1', 'e-caller-key']);
    expect(e.callerPublic).toEqual(['env-e-caller-key']);
  });

  it('the organization level loads unchanged beside the environment parts', () => {
    expect(loadOrganization(setup()).settings.environments).toEqual(['e', 'e2']);
  });
});

describe('TC-EHA-036: S2 refuses to start on a bad part', () => {
  it.each([
    [
      'a signing key that is not a verify key',
      (c: Record<string, any>) => (env(c, 0).controlGateway.keys.signing = 'e-other-key'),
      'keys/signing: names no verify key',
    ],
    [
      'a verify key listed twice',
      (c: Record<string, any>) => {
        env(c, 0).controlGateway.keys.verify.push('e-signing-key-1');
      },
      'e-signing-key-1 is listed twice',
    ],
    [
      "a secret named by another environment's part",
      (c: Record<string, any>) => (env(c, 1).controlGateway.keys.caller = 'e-caller-key'),
      'e-caller-key is also named by environment e',
    ],
    [
      'an organization-level secret',
      (c: Record<string, any>) =>
        (env(c, 0).controlGateway.keys.logPseudonym = 'org-log-pseudonym-key'),
      'org-log-pseudonym-key is an organization-level secret',
    ],
  ])('refuses %s', (_name, change, message) => {
    const config = tenancy();
    change(config);
    expect(problems(() => loadControlGateway(setup(config), E)).join('\n')).toContain(message);
  });

  it('refuses an unconfigured environment, and one with no controlGateway', () => {
    expect(
      problems(() => loadControlGateway(setup(), { project: 'p1', environment: 'e9' })),
    ).toEqual(['environment p1/e9 is not configured']);
    const config = tenancy();
    delete (env(config, 0) as Record<string, unknown>).controlGateway;
    expect(problems(() => loadControlGateway(setup(config), E))).toEqual([
      'environment p1/e has no controlGateway',
    ]);
  });

  it('refuses a missing secret and a short log-pseudonym key, naming each and no value', () => {
    const secrets: Record<string, string> = { ...gatewaySecrets, 'e-log-pseudonym-key': 'c2hvcnQ' };
    delete secrets['e-caller-key'];
    const found = problems(() => loadControlGateway(setup(tenancy(), secrets), E));
    expect(found).toEqual([
      'secret e-caller-key cannot be read',
      'secret e-log-pseudonym-key must hold at least 256 bits',
    ]);
  });
});
