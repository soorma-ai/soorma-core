// SPDX-License-Identifier: FSL-1.1-ALv2
// tenancy.yaml and the organization level's secrets: TC-OI-019, TC-OI-048.
import { randomBytes } from 'node:crypto';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterAll, describe, expect, it } from 'vitest';
import { stringify } from 'yaml';
import {
  ConfigurationError,
  loadMigrator,
  loadOrganization,
  loadSealKeys,
  loadSettings,
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
      internalCallers: [{ environment: 'e', publicKeys: ['env-e-caller-key'] }],
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

describe('TC-OI-019: organization identity comes from configuration only', () => {
  it('loads the tenancy tree and the first Admins, each once, named by the first environment', () => {
    const { settings, secrets } = loadOrganization(setup());
    expect(settings.organization).toBe('o1');
    expect(settings.environments).toEqual(['e', 'e2']);
    expect(settings.firstAdmins).toEqual([{ principal: 'h@example.com', registeredBy: 'e' }]);
    expect(secrets.enrollment).toEqual([{ principal: 'h@example.com', material: MATERIAL }]);
    expect(settings.hashing).toEqual({ budgetMiB: 512 });
  });

  it('ignores the host name and the process environment', () => {
    const paths = setup();
    const before = loadSettings(paths);
    const saved = { ...process.env };
    try {
      process.env.HOSTNAME = 'org-other.soorma.internal';
      process.env.SOORMA_ORGANIZATION = 'o-other';
      process.env.ORGANIZATION = 'o-other';
      expect(loadSettings(paths)).toEqual(before);
    } finally {
      process.env = saved;
    }
  });
});

describe('TC-OI-048: configuration errors stop start-up, and no environment part carries material', () => {
  it('refuses material in an environment part: the part has no such field (BR-CFG-02)', () => {
    const config = tenancy();
    config.projects[0].environments[0].enrollmentMaterial = MATERIAL;
    const found = problems(() => loadOrganization(setup(config)));
    expect(found).toContain('/projects/0/environments/0: must NOT have additional properties');
    expect(found.join('\n')).not.toContain(MATERIAL);
  });

  it.each([
    ['an unknown top-level field', (c: any) => (c.region = 'eu')],
    ['a missing organization', (c: any) => delete c.organization],
    ['an invalid organization', (c: any) => (c.organization = '-o1')],
    ['a project with no environment', (c: any) => (c.projects[0].environments = [])],
    ['a secret name with a path', (c: any) => (c.organizationLevel.keys.counter = '../etc/x')],
  ])('refuses %s', (_name, change) => {
    const config = tenancy();
    change(config);
    expect(problems(() => loadOrganization(setup(config))).length).toBeGreaterThan(0);
  });

  it.each([
    [
      'a repeated environment',
      (c: any) => {
        (c.projects as unknown[]).push({
          id: 'p2',
          environments: [{ id: 'e', firstAdmin: 'x@y' }],
        });
      },
      'environment e appears twice',
    ],
    [
      'material for a principal no environment names',
      (c: any) => {
        (c.organizationLevel.enrollment as unknown[]).push({
          principal: 'z@example.com',
          secret: 'org-seed-key',
        });
      },
      'no environment names this principal as first Admin',
    ],
    [
      'a current seed key that is not configured',
      (c: any) => (c.organizationLevel.keys.seed.current = 's9'),
      'names no configured seed key',
    ],
    [
      'an internal caller for an unconfigured environment',
      (c: any) => (c.organizationLevel.internalCallers[0].environment = 'e9'),
      'environment e9 is not configured',
    ],
  ])('refuses %s', (_name, change, message) => {
    const config = tenancy();
    change(config);
    expect(problems(() => loadOrganization(setup(config))).join('\n')).toContain(message);
  });

  it('refuses unparseable YAML', () => {
    const { configPath, secretsDir } = setup();
    writeFileSync(configPath, 'organization: [o1');
    expect(problems(() => loadOrganization({ configPath, secretsDir }))).toHaveLength(1);
  });

  it('refuses a missing secret, naming it and never another secret', () => {
    const rest = { ...gatewaySecrets };
    delete rest['org-counter-secret'];
    const found = problems(() => loadOrganization(setup(tenancy(), rest)));
    expect(found).toEqual(['secret org-counter-secret cannot be read']);
  });

  it('refuses malformed enrollment material without echoing it', () => {
    const bad = 'not-enrollment-material-SECRET';
    const found = problems(() =>
      loadOrganization(setup(tenancy(), { ...gatewaySecrets, 'org-enrollment-1': bad })),
    );
    expect(found).toEqual([
      'secret org-enrollment-1 is not enrollment material (soorma_em_…, at most 256)',
    ]);
    expect(found.join('\n')).not.toContain(bad);
  });

  it('refuses a short key, a seed key that is not 256 bits, and a reused counter secret', () => {
    const shared = key();
    const found = problems(() =>
      loadOrganization(
        setup(tenancy(), {
          ...gatewaySecrets,
          'org-seed-key': randomBytes(48).toString('base64url'),
          'org-counter-secret': shared,
          'org-log-pseudonym-key': shared,
        }),
      ),
    );
    expect(found).toEqual([
      'secret org-seed-key must hold exactly 256 bits',
      'the log-pseudonym key must differ from the counter secret (NFR-OI-22)',
    ]);
    expect(
      problems(() =>
        loadOrganization(
          setup(tenancy(), {
            ...gatewaySecrets,
            'org-counter-secret': randomBytes(16).toString('base64url'),
          }),
        ),
      ),
    ).toEqual(['secret org-counter-secret must hold at least 256 bits']);
  });

  it('S1 never reads the migrator password, and org-migrate reads only its own secrets', () => {
    expect(() => loadOrganization(setup())).not.toThrow();
    const migratorOnly = setup(tenancy(), {
      'org-db-migrator-password': 'migrator-password',
      'stack-ca-cert': 'CA',
    });
    expect(loadMigrator(migratorOnly).secrets.databasePassword).toBe('migrator-password');
    expect(problems(() => loadOrganization(migratorOnly))).toContain(
      'secret org-signing-key cannot be read',
    );
  });
});

describe("TC-AE-033 step 1: an environment's seal keys, in the seed keys' shape (U3 NP-02)", () => {
  function sealed(sealKeys: unknown): Record<string, any> {
    const config = tenancy();
    config.projects[0].environments[0].sealKeys = sealKeys;
    return config;
  }
  const ring = { current: 'k1', keys: [{ id: 'k1', secret: 'env-e-seal-k1' }] };
  const where = { project: 'p1', environment: 'e' };

  it('loads each key through SecretReader.key(secret, true): exactly 256 bits', () => {
    const k1 = randomBytes(32);
    const k2 = randomBytes(32);
    const two = {
      current: 'k2',
      keys: [
        { id: 'k1', secret: 'env-e-seal-k1' },
        { id: 'k2', secret: 'env-e-seal-k2' },
      ],
    };
    const loaded = loadSealKeys(
      setup(sealed(two), {
        'env-e-seal-k1': k1.toString('base64url'),
        'env-e-seal-k2': `${k2.toString('base64url')}\n`,
      }),
      where,
    );
    expect(loaded).toEqual({
      current: 'k2',
      keys: [
        { id: 'k1', key: k1 },
        { id: 'k2', key: k2 },
      ],
    });
  });

  it('reads only the seal-key secrets: none of the organization level', () => {
    expect(() =>
      loadSealKeys(setup(sealed(ring), { 'env-e-seal-k1': key() }), where),
    ).not.toThrow();
  });

  it.each([
    ['a missing secret', {}, 'secret env-e-seal-k1 cannot be read'],
    ['an empty secret', { 'env-e-seal-k1': '' }, 'secret env-e-seal-k1 is empty'],
    [
      'text that is not base64url',
      { 'env-e-seal-k1': 'not+base64/url=' },
      'secret env-e-seal-k1 is not base64url text',
    ],
    [
      'a 128-bit key',
      { 'env-e-seal-k1': randomBytes(16).toString('base64url') },
      'secret env-e-seal-k1 must hold exactly 256 bits',
    ],
    [
      'a 512-bit key',
      { 'env-e-seal-k1': randomBytes(64).toString('base64url') },
      'secret env-e-seal-k1 must hold exactly 256 bits',
    ],
  ])('refuses start-up for %s', (_, secrets, problem) => {
    expect(problems(() => loadSealKeys(setup(sealed(ring), secrets), where))).toEqual([problem]);
  });

  it('refuses an unknown environment, and one without sealKeys', () => {
    const paths = setup(sealed(ring), { 'env-e-seal-k1': key() });
    expect(problems(() => loadSealKeys(paths, { project: 'p1', environment: 'e9' }))).toEqual([
      'environment p1/e9 is not configured',
    ]);
    expect(problems(() => loadSealKeys(paths, { project: 'p1', environment: 'e2' }))).toEqual([
      'environment p1/e2 has no sealKeys',
    ]);
  });

  it('refuses, as for the seed keys: an unknown current, a duplicate id, an id outside KeyId, a secret naming a path', () => {
    const at = '/projects/0/environments/0/sealKeys';
    expect(problems(() => loadSettings(setup(sealed({ ...ring, current: 'k9' }))))).toEqual([
      `${at}/current: names no configured seal key`,
    ]);
    expect(
      problems(() =>
        loadSettings(
          setup(
            sealed({
              current: 'k1',
              keys: [
                { id: 'k1', secret: 'env-e-seal-k1' },
                { id: 'k1', secret: 'env-e-seal-k2' },
              ],
            }),
          ),
        ),
      ),
    ).toEqual([`${at}: key id k1 appears twice`]);
    for (const id of ['k.1', 'Seal_1', 'K1'])
      expect(
        problems(() =>
          loadSettings(setup(sealed({ current: id, keys: [{ id, secret: 'env-e-seal-k1' }] }))),
        ).length,
      ).toBeGreaterThan(0);
    expect(
      problems(() =>
        loadSettings(
          setup(sealed({ current: 'k1', keys: [{ id: 'k1', secret: '../org-signing-key' }] })),
        ),
      ).length,
    ).toBeGreaterThan(0);
  });

  it("the U2 stack's tenancy.yaml still validates, with no sealKeys", () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const stack = join(here, '../../../deploy/local/config/tenancy.yaml');
    expect(loadSettings({ configPath: stack }).environments.length).toBeGreaterThan(0);
  });
});
