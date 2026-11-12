// SPDX-License-Identifier: FSL-1.1-ALv2
//
// An environment's S3 part (U6 Infrastructure Design §6; D-ID-AC-07, 09, 10):
// S3 reads only its own environment's part and secrets, through its own role;
// its part shares no secret with S2's, another environment's, or the
// organization level's, other than the CA certificate. No configuration holds
// the propagation bound or a lifetime (NP-AC-01; NFR-AC-01, 04).
import { randomBytes } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stringify } from 'yaml';
import { ConfigurationError, loadControlGateway, loadDataGateway } from '../src/index.ts';

const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

const key = (): string => randomBytes(32).toString('base64url');

function controlPart(env: string): Record<string, any> {
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

function dataPart(env: string): Record<string, any> {
  return {
    edge: { port: 8443, tls: `${env}-data-gateway-tls` },
    health: { port: 8080 },
    database: {
      host: `env-db.${env}.soorma.internal`,
      port: 5432,
      name: 'soorma_env',
      user: 'soorma_env_data',
      password: `${env}-db-data-password`,
      ca: 'stack-ca-cert',
    },
    keys: { signing: `${env}-agent-signing-key-1`, verify: [`${env}-agent-signing-key-1`] },
    bound: { counter: `${env}-bootstrap-counter-secret` },
  };
}

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
    },
    projects: [
      {
        id: 'p1',
        environments: ['e', 'e2'].map((id) => ({
          id,
          firstAdmin: 'h@example.com',
          controlGateway: controlPart(id),
          dataGateway: dataPart(id),
        })),
      },
    ],
  };
}

const envSecrets = (env: string): Record<string, string> => ({
  [`${env}-control-gateway-tls`]: `TLS-${env}`,
  [`${env}-db-app-password`]: `app-${env}`,
  [`${env}-db-migrator-password`]: `migrator-${env}`,
  [`${env}-signing-key-1`]: `SIGNING-${env}`,
  [`${env}-caller-key`]: `CALLER-${env}`,
  [`${env}-log-pseudonym-key`]: key(),
  [`${env}-data-gateway-tls`]: `DATA-TLS-${env}`,
  [`${env}-db-data-password`]: `data-${env}`,
  [`${env}-agent-signing-key-1`]: `AGENT-SIGNING-${env}`,
  [`${env}-bootstrap-counter-secret`]: key(),
});

const secrets: Record<string, string> = {
  'stack-ca-cert': 'CA',
  ...envSecrets('e'),
  ...envSecrets('e2'),
};

function setup(
  config: Record<string, any> = tenancy(),
  values: Record<string, string> = secrets,
): { configPath: string; secretsDir: string } {
  const dir = mkdtempSync(join(tmpdir(), 'soorma-config-'));
  dirs.push(dir);
  const configPath = join(dir, 'tenancy.yaml');
  writeFileSync(configPath, stringify(config));
  for (const [name, value] of Object.entries(values)) writeFileSync(join(dir, name), value);
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

const part = (config: Record<string, any>, i: number): Record<string, any> =>
  (config.projects as { environments: Record<string, any>[] }[])[0]!.environments[i]!;

const E = { project: 'p1', environment: 'e' };

describe("S3 loads only its own environment's part (D-ID-AC-09, 10)", () => {
  it("loads E's settings and secrets as soorma_env_data, and none of S2's or E2's", () => {
    const { settings, secrets: loaded } = loadDataGateway(setup(), E);
    expect(settings).toEqual({
      organization: 'o1',
      project: 'p1',
      environment: 'e',
      edge: { port: 8443 },
      health: { port: 8080 },
      database: {
        host: 'env-db.e.soorma.internal',
        port: 5432,
        name: 'soorma_env',
        user: 'soorma_env_data',
      },
    });
    expect(loaded.databasePassword).toBe('data-e');
    expect(loaded.edgeTls.toString()).toBe('DATA-TLS-e');
    expect(loaded.databaseCa.toString()).toBe('CA');
    expect(loaded.verifyKeys).toEqual([
      { name: 'e-agent-signing-key-1', pem: Buffer.from('AGENT-SIGNING-e') },
    ]);
    expect(loaded.signing).toBe('e-agent-signing-key-1');
    expect(loaded.counterSecret.length).toBe(32);
    const all = JSON.stringify(loaded);
    for (const other of ['app-e', 'migrator-e', 'SIGNING-e"', 'CALLER-e', '-e2'])
      expect(all).not.toContain(other);
  });

  it('S3 starts with only its own files present: no S2 secret is read', () => {
    const own = Object.fromEntries(
      [
        'stack-ca-cert',
        'e-data-gateway-tls',
        'e-db-data-password',
        'e-agent-signing-key-1',
        'e-bootstrap-counter-secret',
      ].map((n) => [n, secrets[n]!]),
    );
    expect(() => loadDataGateway(setup(tenancy(), own), E)).not.toThrow();
  });

  it("S2 loads unchanged beside S3's part", () => {
    expect(loadControlGateway(setup(), E).settings.database.user).toBe('soorma_env_app');
  });

  it('holds no propagation bound and no lifetime: the configuration has nowhere to put one', () => {
    const settings = JSON.stringify(loadDataGateway(setup(), E).settings);
    expect(settings).not.toMatch(/ttl|lifetime|propagation|maxAge|lineage|expir/i);
  });
});

describe('S3 refuses to start on a bad part', () => {
  it.each([
    [
      'a signing key that is not a verify key',
      (c: Record<string, any>) => (part(c, 0).dataGateway.keys.signing = 'e-other-key'),
      'dataGateway/keys/signing: names no verify key',
    ],
    [
      'a verify key listed twice',
      (c: Record<string, any>) => {
        (part(c, 0).dataGateway.keys.verify as string[]).push('e-agent-signing-key-1');
      },
      'e-agent-signing-key-1 is listed twice',
    ],
    [
      "S2's role (D-ID-AC-07)",
      (c: Record<string, any>) => (part(c, 0).dataGateway.database.user = 'soorma_env_app'),
      'dataGateway/database/user: soorma_env_app is not S3',
    ],
    [
      'the migrator role',
      (c: Record<string, any>) => (part(c, 0).dataGateway.database.user = 'soorma_env_migrator'),
      'dataGateway/database/user: soorma_env_migrator is not S3',
    ],
    [
      "S2's app password",
      (c: Record<string, any>) => (part(c, 0).dataGateway.database.password = 'e-db-app-password'),
      'dataGateway: e-db-app-password is also named by environment e',
    ],
    [
      "S2's human key ring (the separate agent ring, D-AC-03)",
      (c: Record<string, any>) => {
        part(c, 0).dataGateway.keys = {
          signing: 'e-signing-key-1',
          verify: ['e-signing-key-1'],
        };
      },
      'e-signing-key-1 is also named by environment e',
    ],
    [
      "another environment's counter secret",
      (c: Record<string, any>) =>
        (part(c, 1).dataGateway.bound.counter = 'e-bootstrap-counter-secret'),
      'e-bootstrap-counter-secret is also named by environment e (dataGateway)',
    ],
    [
      'an organization-level secret',
      (c: Record<string, any>) => (part(c, 0).dataGateway.bound.counter = 'org-counter-secret'),
      'org-counter-secret is an organization-level secret',
    ],
  ])('refuses %s', (_name, change, message) => {
    const config = tenancy();
    change(config);
    expect(problems(() => loadDataGateway(setup(config), E)).join('\n')).toContain(message);
  });

  it('refuses a field for a bound or a lifetime: the part is closed', () => {
    const config = tenancy();
    part(config, 0).dataGateway.revocationTtlMs = 1000;
    expect(problems(() => loadDataGateway(setup(config), E)).join('\n')).toContain(
      'must NOT have additional properties',
    );
  });

  it('refuses an unconfigured environment, and one with no dataGateway', () => {
    expect(problems(() => loadDataGateway(setup(), { project: 'p1', environment: 'e9' }))).toEqual([
      'environment p1/e9 is not configured',
    ]);
    const config = tenancy();
    delete part(config, 0).dataGateway;
    expect(problems(() => loadDataGateway(setup(config), E))).toEqual([
      'environment p1/e has no dataGateway',
    ]);
  });

  it('refuses a missing secret and a short counter secret, naming each and no value', () => {
    const values: Record<string, string> = {
      ...secrets,
      'e-bootstrap-counter-secret': 'c2hvcnQ',
    };
    delete values['e-db-data-password'];
    expect(problems(() => loadDataGateway(setup(tenancy(), values), E))).toEqual([
      'secret e-db-data-password cannot be read',
      'secret e-bootstrap-counter-secret must hold at least 256 bits',
    ]);
  });
});

describe('no configuration schema defines a bound or a TTL (NP-AC-01; NFR-AC-01)', () => {
  it('tenancy.schema.json has no such property anywhere', () => {
    const schema = JSON.parse(
      readFileSync(join(import.meta.dirname, '../schema/tenancy.schema.json'), 'utf8'),
    ) as unknown;
    const names: string[] = [];
    const walk = (node: unknown): void => {
      if (Array.isArray(node)) node.forEach(walk);
      else if (node !== null && typeof node === 'object') {
        const o = node as Record<string, unknown>;
        if (o.properties && typeof o.properties === 'object')
          names.push(...Object.keys(o.properties));
        Object.values(o).forEach(walk);
      }
    };
    walk(schema);
    expect(names.length).toBeGreaterThan(0);
    expect(names.filter((n) => /ttl|lifetime|propagation|maxage|lineage|expir/i.test(n))).toEqual(
      [],
    );
  });
});
