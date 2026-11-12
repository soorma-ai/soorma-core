// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U5's backup and restore on the local stack (NFR-AR-09, 10; NP-AR-08, 09):
//
// - TC-AR-057: the four one-shot services, rendered with --profile backup.
//   `docker compose config` with no profile leaves them out, so U4's
//   per-service Compose-model rules (compose-model.test.ts) never reach them;
//   this test applies those rules to them too (D-CG-AR-21, class 2), beside
//   U5's own checks
// - TC-AR-056: a backup file is 0600 in a 0700 directory, opened so it never
//   exists with another mode, and the path is git- and docker-ignored
// - TC-AR-060 (the function): the archive check refuses a file without the
//   PGDMP magic before reading it, and refuses one the full read refuses
import { execFileSync } from 'node:child_process';
import { closeSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { textFindings } from '../../tools/checks/secrets.ts';
import {
  ARCHIVE_MAGIC,
  checkArchive,
  hasArchiveMagic,
  openBackupFile,
} from '../local/scripts/backup-archive.ts';

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
  ports?: unknown[];
  secrets?: { source: string }[];
  volumes?: Volume[];
  profiles?: string[];
  user?: string;
  read_only?: boolean;
  cap_drop?: string[];
  security_opt?: string[];
  image?: string;
  entrypoint?: string[];
  command?: string[] | null;
  tmpfs?: string[];
}

const render = (profile: boolean): Record<string, Service> =>
  (
    JSON.parse(
      execFileSync(
        'docker',
        [
          'compose',
          '-f',
          join(local, 'compose.yaml'),
          ...(profile ? ['--profile', 'backup'] : []),
          'config',
          '--format',
          'json',
        ],
        { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
      ),
    ) as { services: Record<string, Service> }
  ).services;

const withProfile = render(true);
const withoutProfile = render(false);
const ENVIRONMENTS = ['e', 'e2'] as const;
const BACKUP = ENVIRONMENTS.flatMap((env) => [`${env}-backup`, `${env}-restore`]);
const level = (name: string): string => /^(org|e2|e)-/.exec(name)?.[1] ?? '';

describe('TC-AR-057: the backup and restore services', () => {
  it('exist only under the backup profile: stack:up never starts them', () => {
    for (const name of BACKUP) {
      expect(withProfile[name], name).toBeDefined();
      expect(withoutProfile[name], name).toBeUndefined();
      expect(withProfile[name]?.profiles, name).toEqual(['backup']);
    }
  });

  // U4's per-service rules (compose-model.test.ts, TC-EHA-079, 089), applied
  // to the four services it cannot see (D-CG-AR-21).
  it("U4's rule: they list no secret", () => {
    for (const name of BACKUP) expect(withProfile[name]?.secrets ?? [], name).toEqual([]);
  });

  it("U4's rule: only their own level's volume, at their own subpath, read-only", () => {
    for (const name of BACKUP) {
      const mounts = (withProfile[name]?.volumes ?? []).filter(
        (v) => v.type === 'volume' && (v.source ?? '').endsWith('-secrets'),
      );
      expect(mounts, name).toHaveLength(1);
      expect(mounts[0], name).toMatchObject({
        source: `${level(name)}-secrets`,
        target: '/run/secrets',
        read_only: true,
        volume: { subpath: name.endsWith('-restore') ? 'restore' : 'backup' },
      });
      // U5: and no other mount at all; the pgpass file is on a tmpfs.
      expect(withProfile[name]?.volumes, name).toHaveLength(1);
      expect(withProfile[name]?.tmpfs, name).toEqual(['/tmp']);
    }
  });

  it("U4's rule: no secret-looking value, and no secret-named variable but a _FILE path", () => {
    for (const name of BACKUP)
      for (const [key, value] of Object.entries(withProfile[name]?.environment ?? {})) {
        expect(textFindings(`${name}.${key}`, `${key}=${value ?? ''}`), `${name}.${key}`).toEqual(
          [],
        );
        if (/(PASSWORD|KEY|SECRET|TOKEN)$/.test(key.replace(/_FILE$/, '')) || key.endsWith('_FILE'))
          expect(key.endsWith('_FILE'), `${name}.${key}`).toBe(true);
      }
  });

  it("U4's rule: networks within their own environment, and nothing published", () => {
    for (const name of BACKUP) {
      expect(Object.keys(withProfile[name]?.networks ?? {}), name).toEqual([level(name)]);
      expect(withProfile[name]?.ports ?? [], name).toEqual([]);
    }
  });

  it('U5: PGPASSFILE is the only variable; no password in the environment, entrypoint, or command', () => {
    const secretsDir = join(local, '.secrets');
    // The generated passwords, where stack:init has run; the structural checks hold either way.
    const values = ENVIRONMENTS.flatMap((env) => {
      try {
        return [readFileSync(join(secretsDir, `${env}-db-migrator-password`), 'utf8').trim()];
      } catch {
        return [];
      }
    }).filter((v) => v.length > 0);
    for (const name of BACKUP) {
      const s = withProfile[name]!;
      expect(s.environment, name).toEqual({ PGPASSFILE: '/tmp/pgpass' });
      const text = JSON.stringify([s.environment, s.entrypoint, s.command]);
      expect(text, name).not.toMatch(/PGPASSWORD/);
      for (const v of values) expect(text, name).not.toContain(v);
      const script = (s.entrypoint ?? []).join('\n');
      expect(script, name).toContain(`/run/secrets/${level(name)}-db-migrator-password`);
      expect(script, name).toContain('sslmode=verify-full');
      expect(script, name).toContain('sslrootcert=/run/secrets/stack-ca-cert');
      expect(script, name).toContain('--no-password');
      expect(script, name).toContain('umask 077');
    }
  });

  it('U5: hardened, as the pinned PostgreSQL image, user 999', () => {
    for (const name of BACKUP) {
      const s = withProfile[name]!;
      expect(s.user, name).toBe('999:999');
      expect(s.read_only, name).toBe(true);
      expect(s.cap_drop, name).toEqual(['ALL']);
      expect(s.security_opt, name).toEqual(['no-new-privileges:true']);
      expect(s.image, name).toMatch(/^postgres:18\.4@sha256:[0-9a-f]{64}$/);
    }
  });

  it('U5: backup dumps custom format; restore refuses a non-empty database, in one transaction', () => {
    for (const env of ENVIRONMENTS) {
      const b = (withProfile[`${env}-backup`]?.entrypoint ?? []).join('\n');
      expect(b).toContain('exec pg_dump --format=custom');
      const r = (withProfile[`${env}-restore`]?.entrypoint ?? []).join('\n');
      expect(r).toContain('the database is not empty');
      expect(r).toContain('exec pg_restore --exit-on-error --single-transaction');
    }
  });

  it('U5: env.sh copies backup/ as 999, with the migrator password and the CA only', () => {
    const script = readFileSync(join(local, 'secrets-init/env.sh'), 'utf8');
    expect(script).toMatch(/^copy backup 999 "\$env-db-migrator-password" stack-ca-cert$/m);
  });
});

describe('TC-AR-056: a backup file is 0600 in a 0700 directory, and never committed', () => {
  const dirs: string[] = [];
  afterAll(() => {
    for (const d of dirs) rmSync(d, { recursive: true, force: true });
  });

  it('the directory is 0700, the file 0600, and an existing name is refused', () => {
    const parent = mkdtempSync(join(tmpdir(), 'soorma-backups-'));
    dirs.push(parent);
    const dir = join(parent, '.backups');
    const { path, fd } = openBackupFile(dir, 'e-x.dump');
    closeSync(fd);
    expect(statSync(dir).mode & 0o777).toBe(0o700);
    expect(statSync(path).mode & 0o777).toBe(0o600);
    expect(() => openBackupFile(dir, 'e-x.dump')).toThrow();
  });

  it('deploy/local/.backups/ is git-ignored and docker-ignored', () => {
    expect(
      execFileSync('git', ['check-ignore', 'deploy/local/.backups/e-x.dump'], {
        cwd: root,
        encoding: 'utf8',
      }).trim(),
    ).toBe('deploy/local/.backups/e-x.dump');
    expect(readFileSync(join(root, '.dockerignore'), 'utf8')).toMatch(
      /^deploy\/local\/\.backups$/m,
    );
  });
});

describe('TC-AR-060: the archive check (the function)', () => {
  const dir = mkdtempSync(join(tmpdir(), 'soorma-archive-'));
  afterAll(() => rmSync(dir, { recursive: true, force: true }));

  it('refuses a file without the magic before reading it; refuses what the full read refuses', async () => {
    const good = join(dir, 'good.dump');
    writeFileSync(good, Buffer.concat([ARCHIVE_MAGIC, Buffer.from('rest')]));
    const bad = join(dir, 'bad.dump');
    writeFileSync(bad, Buffer.concat([Buffer.from('notice\n'), ARCHIVE_MAGIC]));
    expect(hasArchiveMagic(good)).toBe(true);
    expect(hasArchiveMagic(bad)).toBe(false);
    let reads = 0;
    const read = (code: number) => () => {
      reads += 1;
      return Promise.resolve(code);
    };
    expect(await checkArchive(bad, read(0))).toEqual({ ok: false, reason: 'magic' });
    expect(reads).toBe(0);
    expect(await checkArchive(good, read(1))).toEqual({ ok: false, reason: 'read' });
    expect(await checkArchive(good, read(0))).toEqual({ ok: true });
  });
});
