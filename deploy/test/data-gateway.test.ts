// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U6's own Compose assertions (Infrastructure Design §1, §4, §13, §14;
// D-ID-AC-01, 02, 09, 12, 14), over `docker compose config` rendered with
// every profile, beside U4's rules (compose-model.test.ts, TC-AC-086):
// TC-AC-087 (S3's secrets, roles, networks), TC-AC-088 (the restore services'
// own subdirectory), and TC-AC-020's file half (each S3 only its own agent ring).
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

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
  ports?: { host_ip?: string; published?: string; target: number }[];
  volumes?: Volume[];
  depends_on?: Record<string, unknown>;
  read_only?: boolean;
  cap_drop?: string[];
  security_opt?: string[];
  image?: string;
}

const compose = ['compose', '-f', join(local, 'compose.yaml')];
const run = (args: string[]): string =>
  execFileSync('docker', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
const profiles = run([...compose, 'config', '--profiles'])
  .split('\n')
  .filter((p) => p.length > 0);
const services = (
  JSON.parse(
    run([...compose, ...profiles.flatMap((p) => ['--profile', p]), 'config', '--format', 'json']),
  ) as { services: Record<string, Service> }
).services;
const ENVIRONMENTS = ['e', 'e2'] as const;
const PORTS = { e: '8444', e2: '8445' } as const;

/** env.sh's `copy <subpath> <uid> <secret>...` lists, for {env}. */
function copies(env: string): Record<string, string[]> {
  const script = readFileSync(join(local, 'secrets-init/env.sh'), 'utf8').replace(/\\\n\s*/g, ' ');
  const out: Record<string, string[]> = {};
  for (const m of script.matchAll(/^copy (\S+) (\d+) (.+)$/gm))
    out[m[1]!] = m[3]!
      .trim()
      .split(/\s+/)
      .map((n) => n.replace(/"/g, '').replace('$env', env));
  return out;
}

const subpathOf = (s: Service | undefined): string | undefined =>
  (s?.volumes ?? []).find((v) => (v.source ?? '').endsWith('-secrets'))?.volume?.subpath;

describe('TC-AC-087: S3’s secrets, roles, and networks are separated as designed', () => {
  it.each(ENVIRONMENTS)('%s: data-gateway/ holds exactly S3’s five secrets', (env) => {
    expect(copies(env)['data-gateway']?.sort()).toEqual(
      [
        `${env}-data-gateway-tls`,
        'stack-ca-cert',
        `${env}-db-data-password`,
        `${env}-agent-signing-key-1`,
        `${env}-bootstrap-counter-secret`,
      ].sort(),
    );
    expect(subpathOf(services[`${env}-data-gateway`])).toBe('data-gateway');
  });

  it.each(ENVIRONMENTS)(
    '%s: S3 never gets the app or migrator password; S2 never gets the data password',
    (env) => {
      const c = copies(env);
      expect(c['data-gateway']).not.toContain(`${env}-db-app-password`);
      expect(c['data-gateway']).not.toContain(`${env}-db-migrator-password`);
      expect(c['control-gateway']).not.toContain(`${env}-db-data-password`);
      expect(c['control-gateway']).not.toContain(`${env}-bootstrap-counter-secret`);
    },
  );

  it.each(ENVIRONMENTS)(
    '%s: agent signing keys only in data-gateway/; verify halves only in event-ingest/ (U7)',
    (env) => {
      for (const [dir, names] of Object.entries(copies(env))) {
        for (const n of names) {
          if (/-agent-signing-key-/.test(n)) expect(dir, n).toBe('data-gateway');
          if (/-agent-verify-key-/.test(n)) expect(dir, n).toBe('event-ingest');
          // U7 (the user's): every verify-key name in this environment's copies is its own.
          if (/-agent-verify-key-/.test(n)) expect(n.startsWith(`${env}-`), n).toBe(true);
        }
      }
      const listed = JSON.parse(run([...compose, 'config', '--format', 'json'])) as {
        services: Record<string, { secrets?: { source: string }[] }>;
      };
      const verifyKeys = (name: string): string[] =>
        (listed.services[name]?.secrets ?? [])
          .map((x) => x.source)
          .filter((x) => /agent-verify-key/.test(x));
      expect(verifyKeys(`${env}-secrets-init`)).toEqual([`${env}-agent-verify-key-1`]);
      // U7 (the user's): no service other than {env}-secrets-init lists any of
      // this environment's verify keys; another environment's copier lists only
      // its own environment's; every other service lists none.
      for (const name of Object.keys(listed.services)) {
        if (name === `${env}-secrets-init`) continue;
        const other = ENVIRONMENTS.find((o) => o !== env && name === `${o}-secrets-init`);
        if (other)
          for (const k of verifyKeys(name))
            expect(k.startsWith(`${other}-`), `${name} ${k}`).toBe(true);
        else expect(verifyKeys(name), name).toEqual([]);
      }
    },
  );

  it.each(ENVIRONMENTS)(
    '%s: no human ring, caller key, or log-pseudonym key in data-gateway/',
    (env) => {
      const dg = copies(env)['data-gateway'] ?? [];
      for (const n of [`${env}-signing-key-1`, `${env}-caller-key`, `${env}-log-pseudonym-key`])
        expect(dg).not.toContain(n);
    },
  );

  it.each(ENVIRONMENTS)('%s: S3 is on its own network only, never org-internal', (env) => {
    const s = services[`${env}-data-gateway`];
    expect(Object.keys(s?.networks ?? {})).toEqual([env]);
  });

  it.each(ENVIRONMENTS)(
    '%s: published on its own loopback port only; hardened; never waits for S1 or S2',
    (env) => {
      const s = services[`${env}-data-gateway`]!;
      expect(
        (s.ports ?? []).map((p) => `${p.host_ip ?? '0.0.0.0'}:${p.published ?? ''}->${p.target}`),
      ).toEqual([`127.0.0.1:${PORTS[env]}->8443`]);
      expect(s.read_only).toBe(true);
      expect(s.cap_drop).toEqual(['ALL']);
      expect(s.security_opt).toEqual(['no-new-privileges:true']);
      expect(s.image).toBe('soorma/data-gateway:local');
      expect(Object.keys(s.depends_on ?? {}).sort()).toEqual(
        [`${env}-migrate`, `${env}-secrets-init`].sort(),
      );
    },
  );

  it('S3 reads only its allowlisted variables', () => {
    const allowed = ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT'];
    for (const env of ENVIRONMENTS)
      expect(Object.keys(services[`${env}-data-gateway`]?.environment ?? {}).sort()).toEqual(
        allowed,
      );
    const src = join(root, 'services/data-gateway/src');
    const read = new Set(
      readdirSync(src, { recursive: true, encoding: 'utf8' })
        .filter((f) => f.endsWith('.ts'))
        .flatMap((f) => [
          ...readFileSync(join(src, f), 'utf8').matchAll(/process\.env\.([A-Z_]+)/g),
        ])
        .map((m) => m[1]!),
    );
    // SOORMA_CONFIG and SOORMA_SECRETS_DIR are test-only path overrides, unset in Compose.
    for (const name of read)
      if (!['SOORMA_CONFIG', 'SOORMA_SECRETS_DIR'].includes(name))
        expect(allowed, name).toContain(name);
  });

  it("tenancy.yaml's dataGateway parts name soorma_env_data and only their own secrets", () => {
    const tenancy = readFileSync(join(local, 'config/tenancy.yaml'), 'utf8');
    for (const env of ENVIRONMENTS) {
      const part = tenancy.slice(
        tenancy.indexOf(`edge: { port: 8443, tls: ${env}-data-gateway-tls }`),
      );
      const block = part.slice(0, part.indexOf('counter:') + 60);
      expect(block).toContain('user: soorma_env_data');
      expect(block).toContain(`password: ${env}-db-data-password`);
      expect(block).toContain(`signing: ${env}-agent-signing-key-1`);
      expect(block).toContain(`counter: ${env}-bootstrap-counter-secret`);
    }
  });
});

describe('TC-AC-020 (the file half): each S3 mounts only its own environment’s agent ring', () => {
  it('E’s and E2’s data-gateway/ hold different signing keys, each of its own environment', () => {
    for (const env of ENVIRONMENTS) {
      const keys = (copies(env)['data-gateway'] ?? []).filter((n) => n.includes('agent-'));
      expect(keys).toEqual([`${env}-agent-signing-key-1`]);
    }
  });
});

describe('TC-AC-088: the restore services mount their own restore/ subdirectory', () => {
  it.each(ENVIRONMENTS)('%s: restore mounts restore/, backup mounts backup/', (env) => {
    expect(subpathOf(services[`${env}-restore`])).toBe('restore');
    expect(subpathOf(services[`${env}-backup`])).toBe('backup');
  });

  it('env.sh: the restore line, and the backup line unchanged', () => {
    const script = readFileSync(join(local, 'secrets-init/env.sh'), 'utf8');
    expect(script).toContain('copy restore 999 "$env-db-migrator-password" stack-ca-cert');
    expect(script).toContain('copy backup 999 "$env-db-migrator-password" stack-ca-cert');
  });
});
