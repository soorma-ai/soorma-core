// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U7's own Compose assertions (Infrastructure Design §1, §4, §8, §14;
// D-ID-ET-01, 02, 06, 14, 17), over `docker compose config` rendered with
// every profile, beside U4's rules (compose-model.test.ts): TC-ET-065 (one
// S4 per environment, no replicas), S4's memory limit, its secrets, its
// network, and its variables.
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
  mem_limit?: string | number;
  scale?: number;
  deploy?: { replicas?: number } | null;
  user?: string;
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
const PORTS = { e: '8446', e2: '8447' } as const;
const MEM_LIMIT = 512 * 1024 * 1024;

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

describe('TC-ET-065: one S4 per environment, no replicas', () => {
  it.each(ENVIRONMENTS)('%s: exactly one event-ingest service, never scaled', (env) => {
    const s4 = Object.keys(services).filter((n) => n === `${env}-event-ingest`);
    expect(s4).toEqual([`${env}-event-ingest`]);
    const s = services[`${env}-event-ingest`]!;
    expect(s.deploy?.replicas ?? 1).toBe(1);
    expect(s.scale ?? 1).toBe(1);
  });

  it('no other service runs S4’s image, and no third S4 exists', () => {
    const running = Object.entries(services)
      .filter(([, s]) => s.image === 'soorma/event-ingest:local')
      .map(([n]) => n)
      .sort();
    expect(running).toEqual(['e-event-ingest', 'e2-event-ingest']);
  });
});

describe('D-ID-ET-17: each S4’s memory limit is the recorded 512m', () => {
  it.each(ENVIRONMENTS)('%s', (env) => {
    expect(Number(services[`${env}-event-ingest`]?.mem_limit)).toBe(MEM_LIMIT);
  });
});

describe('D-ID-ET-06: S4’s secrets', () => {
  it.each(ENVIRONMENTS)('%s: event-ingest/ holds exactly S4’s five secrets', (env) => {
    expect(copies(env)['event-ingest']?.sort()).toEqual(
      [
        `${env}-event-ingest-tls`,
        'stack-ca-cert',
        `${env}-db-ingest-password`,
        `${env}-agent-verify-key-1`,
        `${env}-seal-key-1`,
      ].sort(),
    );
    expect(subpathOf(services[`${env}-event-ingest`])).toBe('event-ingest');
  });

  it.each(ENVIRONMENTS)(
    '%s: seal keys and verify halves only in this environment’s event-ingest/',
    (env) => {
      for (const level of ENVIRONMENTS)
        for (const [dir, names] of Object.entries(copies(level)))
          for (const n of names)
            if (n.startsWith(`${env}-seal-key-`) || n.startsWith(`${env}-agent-verify-key-`)) {
              expect(level, n).toBe(env);
              expect(dir, n).toBe('event-ingest');
            }
    },
  );

  it.each(ENVIRONMENTS)(
    '%s: no signing key, human ring, caller key, log-pseudonym key, or other role’s password',
    (env) => {
      const ig = copies(env)['event-ingest'] ?? [];
      for (const n of ig) {
        expect(n, n).not.toMatch(/-agent-signing-key-|-signing-key-/);
        expect(n, n).not.toMatch(/-caller-key|-log-pseudonym-key|-bootstrap-counter-secret/);
      }
      for (const n of [
        `${env}-db-app-password`,
        `${env}-db-migrator-password`,
        `${env}-db-data-password`,
        `${env}-db-superuser-password`,
      ])
        expect(ig).not.toContain(n);
    },
  );
});

describe('D-ID-ET-01, 02: S4’s network, edge, hardening, and variables', () => {
  it.each(ENVIRONMENTS)('%s: on its own network only, never org-internal', (env) => {
    expect(Object.keys(services[`${env}-event-ingest`]?.networks ?? {})).toEqual([env]);
  });

  it.each(ENVIRONMENTS)(
    '%s: published on its own loopback port only; hardened; never waits for S1, S2, or S3',
    (env) => {
      const s = services[`${env}-event-ingest`]!;
      expect(
        (s.ports ?? []).map((p) => `${p.host_ip ?? '0.0.0.0'}:${p.published ?? ''}->${p.target}`),
      ).toEqual([`127.0.0.1:${PORTS[env]}->8443`]);
      expect(s.read_only).toBe(true);
      expect(s.cap_drop).toEqual(['ALL']);
      expect(s.security_opt).toEqual(['no-new-privileges:true']);
      expect(Object.keys(s.depends_on ?? {}).sort()).toEqual(
        [`${env}-migrate`, `${env}-secrets-init`].sort(),
      );
    },
  );

  it('S4 reads only its allowlisted variables', () => {
    const allowed = ['SOORMA_ENVIRONMENT', 'SOORMA_HEALTH_PORT', 'SOORMA_PROJECT'];
    for (const env of ENVIRONMENTS)
      expect(Object.keys(services[`${env}-event-ingest`]?.environment ?? {}).sort()).toEqual(
        allowed,
      );
    const src = join(root, 'services/event-ingest/src');
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

  it("tenancy.yaml's eventIngest parts name soorma_env_ingest, their own secrets, and no time value", () => {
    const tenancy = readFileSync(join(local, 'config/tenancy.yaml'), 'utf8');
    for (const env of ENVIRONMENTS) {
      const part = tenancy.slice(
        tenancy.indexOf(`edge: { port: 8443, tls: ${env}-event-ingest-tls }`),
      );
      const block = part.slice(0, part.indexOf('agentVerify:') + 60);
      expect(block).toContain('user: soorma_env_ingest');
      expect(block).toContain(`password: ${env}-db-ingest-password`);
      expect(block).toContain(`agentVerify: [${env}-agent-verify-key-1]`);
      expect(block).not.toMatch(/bound|ttl|propagation|interval|seconds/i);
      expect(tenancy).toContain(`{ id: s1, secret: ${env}-seal-key-1 }`);
    }
  });
});
