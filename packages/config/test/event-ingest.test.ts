// SPDX-License-Identifier: FSL-1.1-ALv2
//
// An environment's S4 part (U7 Infrastructure Design §6; D-ID-ET-06, 07, 19):
// TC-ET-089, and the configuration half of TC-ET-030. S4 reads only its own
// environment's part, its agent verify halves, and its seal keys; a seal key,
// an agent verify key, or its database password shared with another
// environment's part, another deployable's part, or the organization level is
// refused, and so is any role but its own. No configuration holds the
// propagation bound. U2's, U4's, and U6's configuration tests are unchanged.
import { randomBytes } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stringify } from 'yaml';
import {
  ConfigurationError,
  EVENT_INGEST_ROLE,
  loadDataGateway,
  loadEventIngest,
  listSecrets,
} from '../src/index.ts';

const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

const key = (): string => randomBytes(32).toString('base64url');

const database = (env: string, user: string, password: string) => ({
  host: `env-db.${env}.soorma.internal`,
  port: 5432,
  name: 'soorma_env',
  user,
  password,
  ca: 'stack-ca-cert',
});

function environment(env: string): Record<string, any> {
  return {
    id: env,
    firstAdmin: 'h@example.com',
    sealKeys: { current: 's1', keys: [{ id: 's1', secret: `${env}-seal-key-1` }] },
    controlGateway: {
      edge: { port: 8443, tls: `${env}-control-gateway-tls` },
      health: { port: 8080 },
      database: database(env, 'soorma_env_app', `${env}-db-app-password`),
      migrator: { user: 'soorma_env_migrator', password: `${env}-db-migrator-password` },
      keys: {
        signing: `${env}-signing-key-1`,
        verify: [`${env}-signing-key-1`],
        caller: `${env}-caller-key`,
        logPseudonym: `${env}-log-pseudonym-key`,
      },
      organizationLevel: { host: 'org-gateway.soorma.internal', port: 9443, ca: 'stack-ca-cert' },
    },
    dataGateway: {
      edge: { port: 8443, tls: `${env}-data-gateway-tls` },
      health: { port: 8080 },
      database: database(env, 'soorma_env_data', `${env}-db-data-password`),
      keys: { signing: `${env}-agent-signing-key-1`, verify: [`${env}-agent-signing-key-1`] },
      bound: { counter: `${env}-bootstrap-counter-secret` },
    },
    eventIngest: {
      edge: { port: 8443, tls: `${env}-event-ingest-tls` },
      health: { port: 8080 },
      database: database(env, EVENT_INGEST_ROLE, `${env}-db-ingest-password`),
      keys: { agentVerify: [`${env}-agent-verify-key-1`] },
    },
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
    projects: [{ id: 'p1', environments: ['e', 'e2'].map(environment) }],
  };
}

const envSecrets = (env: string): Record<string, string> => ({
  [`${env}-event-ingest-tls`]: `INGEST-TLS-${env}`,
  [`${env}-db-ingest-password`]: `ingest-${env}`,
  [`${env}-agent-verify-key-1`]: `AGENT-VERIFY-${env}`,
  [`${env}-seal-key-1`]: key(),
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

function problems(fn: () => unknown): string {
  try {
    fn();
  } catch (error) {
    if (error instanceof ConfigurationError) return error.problems.join('\n');
    throw error;
  }
  throw new Error('expected a ConfigurationError');
}

const env = (config: Record<string, any>, i: number): Record<string, any> =>
  (config.projects as { environments: Record<string, any>[] }[])[0]!.environments[i]!;
const E = { project: 'p1', environment: 'e' };

describe("S4 loads only its own environment's part (D-ID-ET-06, 07)", () => {
  it("loads E's settings, its own role, its verify halves, and its seal keys; none of S2's, S3's, or E2's", () => {
    const loaded = loadEventIngest(setup(), E);
    expect(loaded.settings).toEqual({
      organization: 'o1',
      project: 'p1',
      environment: 'e',
      edge: { port: 8443 },
      health: { port: 8080 },
      database: {
        host: 'env-db.e.soorma.internal',
        port: 5432,
        name: 'soorma_env',
        user: 'soorma_env_ingest',
      },
    });
    expect(loaded.secrets.databasePassword).toBe('ingest-e');
    expect(loaded.secrets.agentVerifyKeys).toEqual([
      { name: 'e-agent-verify-key-1', pem: Buffer.from('AGENT-VERIFY-e') },
    ]);
    expect(loaded.secrets.sealKeys.current).toBe('s1');
    expect(loaded.secrets.sealKeys.keys[0]!.key).toHaveLength(32);
  });

  it('S4 starts with only its own files present: no S2 or S3 secret is read', () => {
    const own = Object.fromEntries(
      [
        'stack-ca-cert',
        'e-event-ingest-tls',
        'e-db-ingest-password',
        'e-agent-verify-key-1',
        'e-seal-key-1',
      ].map((n) => [n, secrets[n]!]),
    );
    expect(() => loadEventIngest(setup(tenancy(), own), E)).not.toThrow();
  });

  it("S3 loads unchanged beside S4's part", () => {
    expect(loadDataGateway(setup(), E).settings.database.user).toBe('soorma_env_data');
  });

  it("lists S4's secrets for stack:init", () => {
    const e = listSecrets(setup()).environments.find((x) => x.environment === 'e')!;
    expect(e.eventIngest).toEqual({
      secrets: [
        'e-event-ingest-tls',
        'stack-ca-cert',
        'e-db-ingest-password',
        'e-agent-verify-key-1',
        'e-seal-key-1',
      ],
      tls: 'e-event-ingest-tls',
      agentVerify: ['e-agent-verify-key-1'],
      sealKeys: ['e-seal-key-1'],
      databasePassword: 'e-db-ingest-password',
    });
  });

  it('refuses an unconfigured environment, one with no eventIngest, and one with no sealKeys', () => {
    expect(problems(() => loadEventIngest(setup(), { project: 'p1', environment: 'e9' }))).toBe(
      'environment p1/e9 is not configured',
    );
    const noPart = tenancy();
    delete env(noPart, 0).eventIngest;
    expect(problems(() => loadEventIngest(setup(noPart), E))).toBe(
      'environment p1/e has no eventIngest',
    );
    const noSeal = tenancy();
    delete env(noSeal, 0).sealKeys;
    expect(problems(() => loadEventIngest(setup(noSeal), E))).toBe(
      'environment p1/e has no sealKeys',
    );
  });

  it('refuses a missing verify half and a short seal key, naming each and no value', () => {
    const values: Record<string, string> = { ...secrets, 'e-seal-key-1': 'c2hvcnQ' };
    delete values['e-agent-verify-key-1'];
    expect(problems(() => loadEventIngest(setup(tenancy(), values), E))).toBe(
      [
        'secret e-agent-verify-key-1 cannot be read',
        'secret e-seal-key-1 must hold exactly 256 bits',
      ].join('\n'),
    );
  });
});

describe('TC-ET-089: loadEventIngest refuses a shared secret or another role (D-ID-ET-19)', () => {
  type Change = (c: Record<string, any>) => void;
  const seal = (c: Record<string, any>, name: string): void => {
    env(c, 0).sealKeys.keys[0].secret = name;
  };
  const verify = (c: Record<string, any>, name: string): void => {
    env(c, 0).eventIngest.keys.agentVerify = [name];
  };
  const password = (c: Record<string, any>, name: string): void => {
    env(c, 0).eventIngest.database.password = name;
  };
  // Each kind of S4 secret, shared with each other owner: another
  // environment's part (E2's S4), S2's part, S3's part, the organization level.
  const cases: [string, Change, string][] = [
    ['a seal key shared with E2', (c) => seal(c, 'e2-seal-key-1'), 'e2-seal-key-1'],
    [
      "a seal key shared with S2's part",
      (c) => seal(c, 'e-log-pseudonym-key'),
      'e-log-pseudonym-key',
    ],
    [
      "a seal key shared with S3's part",
      (c) => seal(c, 'e-bootstrap-counter-secret'),
      'e-bootstrap-counter-secret',
    ],
    [
      'a seal key shared with the organization level',
      (c) => seal(c, 'org-counter-secret'),
      'org-counter-secret',
    ],
    [
      'a verify key shared with E2',
      (c) => verify(c, 'e2-agent-verify-key-1'),
      'e2-agent-verify-key-1',
    ],
    ["a verify key shared with S2's part", (c) => verify(c, 'e-caller-key'), 'e-caller-key'],
    [
      "a verify key shared with S3's part",
      (c) => verify(c, 'e-agent-signing-key-1'),
      'e-agent-signing-key-1',
    ],
    [
      'a verify key shared with the organization level',
      (c) => verify(c, 'org-signing-key'),
      'org-signing-key',
    ],
    [
      'the database password shared with E2',
      (c) => password(c, 'e2-db-ingest-password'),
      'e2-db-ingest-password',
    ],
    [
      "the database password shared with S2's part",
      (c) => password(c, 'e-db-app-password'),
      'e-db-app-password',
    ],
    [
      "the database password shared with S3's part",
      (c) => password(c, 'e-db-data-password'),
      'e-db-data-password',
    ],
    [
      'the database password shared with the organization level',
      (c) => password(c, 'org-db-app-password'),
      'org-db-app-password',
    ],
  ];

  it.each(cases)('refuses %s, naming the secret', (_name, change, secret) => {
    const config = tenancy();
    change(config);
    const found = problems(() => loadEventIngest(setup(config), E));
    expect(found).toContain(secret);
    expect(found).toMatch(/is also named by environment|is an organization-level secret/);
  });

  it.each([
    ["S2's role", 'soorma_env_app'],
    ["S3's role", 'soorma_env_data'],
    ["the migrator's role", 'soorma_env_migrator'],
  ])('refuses %s as its database user', (_name, user) => {
    const config = tenancy();
    env(config, 0).eventIngest.database.user = user;
    expect(problems(() => loadEventIngest(setup(config), E))).toContain(
      `eventIngest/database/user: ${user} is not S4's own role (soorma_env_ingest)`,
    );
  });

  it('the CA certificate is the one name several parts may share', () => {
    expect(() => loadEventIngest(setup(), E)).not.toThrow();
  });

  it("accepts the stack's committed tenancy.yaml once it has S4's part (Group 8)", () => {
    const stack = join(import.meta.dirname, '../../../deploy/local/config/tenancy.yaml');
    const text = readFileSync(stack, 'utf8');
    if (!text.includes('eventIngest')) return;
    expect(() =>
      loadEventIngest({ configPath: stack, secretsDir: setup().secretsDir }, E),
    ).not.toThrow(ConfigurationError);
  });
});

describe('TC-ET-030 (the configuration half): no key for the bound', () => {
  it("S4's schema part and settings name no bound, TTL, or propagation key", () => {
    const schema = JSON.parse(
      readFileSync(join(import.meta.dirname, '../schema/tenancy.schema.json'), 'utf8'),
    ) as { $defs: Record<string, unknown> };
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
    walk(schema.$defs.EventIngest);
    expect(names.length).toBeGreaterThan(0);
    expect(names.filter((n) => /bound|ttl|propagation/i.test(n))).toEqual([]);
    const settings = loadEventIngest(setup(), E).settings;
    expect(JSON.stringify(Object.keys(settings))).not.toMatch(/bound|ttl|propagation/i);
  });
});
