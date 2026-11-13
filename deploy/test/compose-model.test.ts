// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The Compose-model test (U4 Infrastructure Design §3, §7; TC-EHA-079,
// TC-EHA-089), over `docker compose config`, which renders without the
// generated secrets:
//  - secrets are mounted files only, and never cross a level: each service
//    mounts only its own level's volume at its own subpath, read-only; each
//    level's copier lists only that level's secrets (and the CA certificate,
//    and on the organization level, the environments' caller public keys);
//  - the only environment variables are the non-secret allowlist
//    (D-CG-EHA-23): SOORMA_PROJECT, SOORMA_ENVIRONMENT, SOORMA_HEALTH_PORT,
//    and the PostgreSQL image's POSTGRES_DB, POSTGRES_USER and
//    POSTGRES_PASSWORD_FILE (a path);
//  - no network spans two environments, and only the three edges are
//    published, on loopback.
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { textFindings } from '../../tools/checks/secrets.ts';

const root = resolve(import.meta.dirname, '../..');
const local = join(root, 'deploy/local');

interface Volume {
  type: string;
  source?: string;
  target: string;
  read_only?: boolean;
  volume?: { subpath?: string };
}
interface Service {
  environment?: Record<string, string | null> | null;
  networks?: Record<string, unknown> | null;
  network_mode?: string;
  ports?: { host_ip?: string; published?: string; target: number }[];
  secrets?: { source: string }[];
  volumes?: Volume[];
}
interface Model {
  services: Record<string, Service>;
  networks: Record<string, unknown>;
}

const compose = ['compose', '-f', join(local, 'compose.yaml')];
const run = (args: string[]): string =>
  execFileSync('docker', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
/** Every profile the stack lists (U6 D-ID-AC-13): the model holds every service. */
const profiles = run([...compose, 'config', '--profiles'])
  .split('\n')
  .filter((p) => p.length > 0);
const model = JSON.parse(
  run([...compose, ...profiles.flatMap((p) => ['--profile', p]), 'config', '--format', 'json']),
) as Model;
const services = model.services;
const ENVIRONMENTS = ['e', 'e2'] as const;

/** The level a service belongs to: `org`, or an environment id. */
const level = (name: string): string => /^(org|e2|e)-/.exec(name)?.[1] ?? '';
/** Its role within the level: `db`, `migrate`, `gateway`, `control-gateway`, `secrets-init`. */
const role = (name: string): string => name.slice(level(name).length + 1);

/** The secrets volume mounts of a service. */
const secretMounts = (s: Service): Volume[] =>
  (s.volumes ?? []).filter((v) => v.type === 'volume' && (v.source ?? '').endsWith('-secrets'));
const listed = (name: string): string[] => (services[name]?.secrets ?? []).map((x) => x.source);

/** The copier's `copy <subpath> <uid> <secret>...` lists, from env.sh, for {env}. */
function envCopies(env: string): Record<string, string[]> {
  const script = readFileSync(join(local, 'secrets-init/env.sh'), 'utf8').replace(/\\\n\s*/g, ' ');
  const out: Record<string, string[]> = {};
  for (const m of script.matchAll(/^copy (\S+) \d+ (.+)$/gm))
    out[m[1]!] = m[2]!
      .trim()
      .split(/\s+/)
      .map((n) => n.replace(/"/g, '').replace('$env', env));
  return out;
}

describe('TC-EHA-079: secrets are mounted files only, and never cross a level', () => {
  it('the model has every service, under every profile, and only the copiers list secrets', () => {
    expect(Object.keys(services).sort()).toEqual(
      ['org', ...ENVIRONMENTS]
        .flatMap((l) =>
          l === 'org'
            ? ['org-db', 'org-gateway', 'org-migrate', 'org-secrets-init']
            : [
                'backup',
                'control-gateway',
                'data-gateway',
                'db',
                'event-ingest',
                'migrate',
                'restore',
                'secrets-init',
              ].map((r) => `${l}-${r}`),
        )
        .sort(),
    );
    for (const [name, s] of Object.entries(services))
      if (role(name) !== 'secrets-init') expect(s.secrets ?? [], name).toEqual([]);
  });

  it("each service mounts only its own level's volume, at its own subpath, read-only", () => {
    for (const [name, s] of Object.entries(services)) {
      const mounts = secretMounts(s);
      expect(mounts, name).toHaveLength(1);
      const [mount] = mounts;
      expect(mount?.source, name).toBe(`${level(name)}-secrets`);
      if (role(name) === 'secrets-init') {
        expect(mount?.target, name).toBe('/out');
        continue;
      }
      const subpath = level(name) === 'org' ? name : role(name);
      expect(mount, name).toMatchObject({
        target: '/run/secrets',
        read_only: true,
        volume: { subpath },
      });
    }
  });

  it("each environment's copier lists only its own secrets and the CA certificate", () => {
    for (const env of ENVIRONMENTS) {
      const names = listed(`${env}-secrets-init`);
      expect(names.sort()).toEqual(
        [
          'stack-ca-cert',
          `${env}-caller-key`,
          `${env}-control-gateway-tls`,
          `${env}-db-app-password`,
          `${env}-db-data-password`,
          `${env}-db-ingest-password`,
          `${env}-db-migrator-password`,
          `${env}-db-superuser-password`,
          `${env}-db-tls`,
          `${env}-log-pseudonym-key`,
          `${env}-signing-key-1`,
          `${env}-data-gateway-tls`,
          `${env}-agent-signing-key-1`,
          `${env}-bootstrap-counter-secret`,
          `${env}-event-ingest-tls`,
          `${env}-agent-verify-key-1`,
          `${env}-seal-key-1`,
        ].sort(),
      );
      for (const n of names) expect(n === 'stack-ca-cert' || n.startsWith(`${env}-`), n).toBe(true);
    }
  });

  it("the organization's copier lists only org- secrets, the CA, and the caller PUBLIC keys", () => {
    const names = listed('org-secrets-init');
    for (const n of names)
      expect(
        n.startsWith('org-') || n === 'stack-ca-cert' || /^(e|e2)-caller-public-key$/.test(n),
        n,
      ).toBe(true);
    expect(names).toEqual(expect.arrayContaining(['e-caller-public-key', 'e2-caller-public-key']));
    expect(names.filter((n) => /^(e|e2)-/.test(n)).sort()).toEqual([
      'e-caller-public-key',
      'e2-caller-public-key',
    ]);
  });

  it('TC-EHA-022: org-signing-key is listed on the organization level only', () => {
    for (const name of Object.keys(services))
      if (name !== 'org-secrets-init') expect(listed(name), name).not.toContain('org-signing-key');
  });

  it("{env}-control-gateway's subpath holds no migrator password, and no other level's secret", () => {
    for (const env of ENVIRONMENTS) {
      const copies = envCopies(env);
      // U5's backup/ (D-CG-AR-19): the migrator password and the CA, for the backup services.
      expect(Object.keys(copies).sort()).toEqual([
        'backup',
        'control-gateway',
        'data-gateway',
        'db',
        'event-ingest',
        'migrate',
        'restore',
      ]);
      expect(copies['control-gateway']).not.toContain(`${env}-db-migrator-password`);
      expect(copies.migrate?.sort()).toEqual([`${env}-db-migrator-password`, 'stack-ca-cert']);
      for (const n of Object.values(copies).flat())
        expect(listed(`${env}-secrets-init`)).toContain(n);
    }
  });
});

describe('TC-EHA-079 / D-CG-EHA-23: the only environment variables are non-secret', () => {
  const POSTGRES = ['POSTGRES_DB', 'POSTGRES_PASSWORD_FILE', 'POSTGRES_USER'];
  const allowed: Record<string, string[]> = {
    'org-db': POSTGRES,
    'org-gateway': ['SOORMA_HEALTH_PORT'],
    'org-migrate': [],
    'org-secrets-init': [],
    ...Object.fromEntries(
      ENVIRONMENTS.flatMap((env) => [
        [`${env}-db`, [...POSTGRES, 'SOORMA_ENVIRONMENT']],
        [`${env}-migrate`, ['SOORMA_ENVIRONMENT', 'SOORMA_PROJECT']],
        [`${env}-control-gateway`, ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT']],
        [`${env}-secrets-init`, []],
        [`${env}-data-gateway`, ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT']],
        [`${env}-event-ingest`, ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT']],
        [`${env}-backup`, ['PGPASSFILE']],
        [`${env}-restore`, ['PGPASSFILE']],
      ]),
    ),
  };

  it("each service's variables are exactly its allowlist", () => {
    for (const [name, s] of Object.entries(services))
      expect(Object.keys(s.environment ?? {}).sort(), name).toEqual(
        [...(allowed[name] ?? ['?'])].sort(),
      );
  });

  it('no value matches the secret pattern; a secret-like name is only a _FILE path', () => {
    for (const [name, s] of Object.entries(services))
      for (const [key, value] of Object.entries(s.environment ?? {})) {
        expect(textFindings(`${name}.${key}`, `${key}=${value ?? ''}`), `${name}.${key}`).toEqual(
          [],
        );
        if (
          /(PASSWORD|KEY|SECRET|TOKEN)$/.test(key.replace(/_FILE$/, '')) ||
          key.endsWith('_FILE')
        ) {
          expect(key.endsWith('_FILE'), `${name}.${key}`).toBe(true);
          expect(value ?? '', `${name}.${key}`).toMatch(
            new RegExp(`^/run/secrets/${level(name)}-`),
          );
        }
      }
  });

  it('each environment service names its own environment and project', () => {
    for (const env of ENVIRONMENTS)
      for (const r of ['db', 'migrate', 'control-gateway', 'data-gateway', 'event-ingest']) {
        const vars = services[`${env}-${r}`]?.environment ?? {};
        expect(vars.SOORMA_ENVIRONMENT, `${env}-${r}`).toBe(env);
        if (r !== 'db') expect(vars.SOORMA_PROJECT, `${env}-${r}`).toBe('p1');
      }
  });

  it('the init script and S2 read the same names (one set, D-CG-EHA-23)', () => {
    const init = readFileSync(join(local, 'db/init/10-soorma-env-roles.sh'), 'utf8');
    expect(init).toContain('SOORMA_ENVIRONMENT');
    expect(init).not.toMatch(/SOORMA_ENV\b/);
    const src = join(root, 'services/control-gateway/src');
    const read = new Set(
      readdirSync(src)
        .filter((f) => f.endsWith('.ts'))
        .flatMap((f) => [
          ...readFileSync(join(src, f), 'utf8').matchAll(/process\.env\.([A-Z_]+)/g),
        ])
        .map((m) => m[1]!),
    );
    // SOORMA_CONFIG and SOORMA_SECRETS_DIR are optional path overrides for
    // tests, unset in Compose; everything else S2 reads is on the allowlist.
    for (const name of read)
      if (!['SOORMA_CONFIG', 'SOORMA_SECRETS_DIR'].includes(name))
        expect(allowed['e-control-gateway'], name).toContain(name);
    expect(read).toContain('SOORMA_PROJECT');
    expect(read).toContain('SOORMA_ENVIRONMENT');
  });
});

describe('TC-EHA-089: no network spans two environments; only the edges are published, on loopback', () => {
  const members = (network: string): string[] =>
    Object.entries(services)
      .filter(([, s]) => Object.keys(s.networks ?? {}).includes(network))
      .map(([n]) => n)
      .sort();

  it('each network holds exactly its members', () => {
    expect(Object.keys(model.networks).sort()).toEqual(
      ['e', 'e2', 'org', 'org-internal-e', 'org-internal-e2'].sort(),
    );
    expect(members('org')).toEqual(['org-db', 'org-gateway', 'org-migrate']);
    for (const env of ENVIRONMENTS) {
      expect(members(env)).toEqual(
        [
          `${env}-control-gateway`,
          `${env}-db`,
          `${env}-migrate`,
          `${env}-data-gateway`,
          `${env}-event-ingest`,
          `${env}-backup`,
          `${env}-restore`,
        ].sort(),
      );
      expect(members(`org-internal-${env}`)).toEqual(
        [`${env}-control-gateway`, 'org-gateway'].sort(),
      );
    }
  });

  it('no network holds services of two environments, and no store is on an org-internal network', () => {
    for (const network of Object.keys(model.networks)) {
      const envs = new Set(
        members(network)
          .map(level)
          .filter((l) => l !== 'org'),
      );
      expect(envs.size, network).toBeLessThanOrEqual(1);
      if (network.startsWith('org-internal-'))
        expect(
          members(network).some((n) => role(n) === 'db'),
          network,
        ).toBe(false);
    }
  });

  it('the copiers have no network', () => {
    for (const name of Object.keys(services))
      if (role(name) === 'secrets-init') expect(services[name]?.network_mode, name).toBe('none');
  });

  it('published: 127.0.0.1:8441 to 8445 only, each an edge; no store port', () => {
    const published = Object.entries(services).flatMap(([name, s]) =>
      (s.ports ?? []).map(
        (p) => `${name} ${p.host_ip ?? '0.0.0.0'}:${p.published ?? ''}->${p.target}`,
      ),
    );
    expect(published.sort()).toEqual(
      [
        'e-control-gateway 127.0.0.1:8442->8443',
        'e2-control-gateway 127.0.0.1:8443->8443',
        'org-gateway 127.0.0.1:8441->8443',
        'e-data-gateway 127.0.0.1:8444->8443',
        'e2-data-gateway 127.0.0.1:8445->8443',
        'e-event-ingest 127.0.0.1:8446->8443',
        'e2-event-ingest 127.0.0.1:8447->8443',
      ].sort(),
    );
  });
});
