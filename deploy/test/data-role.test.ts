// SPDX-License-Identifier: FSL-1.1-ALv2
// S3's own database role on the local stack (U6 D-ID-AC-07, 08): TC-AC-089's
// first part (stack:init generates {env}-db-data-password) and the files that
// create the role and admit it. The rest of TC-AC-089 (the agent keys, the
// counter secret, S3's certificate) and TC-AC-090 (the role on a running
// stack) come with S3's stack services (Group 8).
import { mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { stackInit } from '../local/scripts/stack-init.ts';

const local = join(import.meta.dirname, '../local');
const dirs: string[] = [];
afterAll(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

describe("TC-AC-089 (the data role's password): stack:init generates it per environment", () => {
  it('writes {env}-db-data-password, 0600, distinct per environment, and never overwrites it', () => {
    const dir = mkdtempSync(join(tmpdir(), 'soorma-stack-'));
    dirs.push(dir);
    const first = stackInit({ dir });
    expect(first.created).toEqual(
      expect.arrayContaining(['e-db-data-password', 'e2-db-data-password']),
    );
    const read = (n: string): string => readFileSync(join(dir, n), 'utf8');
    for (const n of ['e-db-data-password', 'e2-db-data-password']) {
      expect(statSync(join(dir, n)).mode & 0o777, n).toBe(0o600);
      expect(read(n).trim(), n).toMatch(/^[A-Za-z0-9_-]{43}$/);
    }
    expect(read('e-db-data-password')).not.toBe(read('e2-db-data-password'));
    expect(read('e-db-data-password')).not.toBe(read('e-db-app-password'));
    const before = read('e-db-data-password');
    expect(stackInit({ dir }).created).not.toContain('e-db-data-password');
    expect(read('e-db-data-password')).toBe(before);
  });
});

describe('D-ID-AC-07, 08: the files that create soorma_env_data and admit it', () => {
  it('env-roles.sql creates it with the other roles’ attributes, CONNECT, and USAGE only', () => {
    const sql = readFileSync(join(local, 'db/env-roles.sql'), 'utf8');
    expect(sql).toMatch(
      /CREATE ROLE soorma_env_data\s+LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;/,
    );
    expect(sql).toContain("GRANT CONNECT ON DATABASE %I TO soorma_env_data'");
    expect(sql).toContain('GRANT USAGE ON SCHEMA public TO soorma_env_data;');
    expect(sql).not.toMatch(/CREATE ON SCHEMA public TO soorma_env_data/);
  });

  it('the init script sets its password from {env}-db-data-password, read inside psql', () => {
    const init = readFileSync(join(local, 'db/init/10-soorma-env-roles.sh'), 'utf8');
    expect(init).toContain('--set=data_file="/run/secrets/$env-db-data-password"');
    expect(init).toContain("ALTER ROLE soorma_env_data PASSWORD :'data_password';");
  });

  it('pg_hba admits it over TLS with SCRAM, to the environment store only', () => {
    const hba = readFileSync(join(local, 'db/env-pg_hba.conf'), 'utf8');
    const lines = hba.split('\n').filter((l) => l.startsWith('hostssl'));
    expect(lines).toHaveLength(2);
    for (const l of lines)
      expect(l).toMatch(/^hostssl\s+soorma_env\s+\S*soorma_env_data\S*\s+\S+\s+scram-sha-256$/);
  });

  it('env.sh copies the password into db/ only (for the init script), in this group', () => {
    const script = readFileSync(join(local, 'secrets-init/env.sh'), 'utf8').replace(
      /\\\n\s*/g,
      ' ',
    );
    const lines = script.split('\n').filter((l) => l.includes('$env-db-data-password'));
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatch(/^copy db 999 /);
  });
});
