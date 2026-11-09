// SPDX-License-Identifier: FSL-1.1-ALv2
// The org store, its roles, and the migration runner: TC-OI-022, TC-OI-051;
// NFR-OI-15 to 18; D-CG-OI-15 (amendment 2).
import { cpSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { MigrationError, MIGRATIONS_DIR, migrate } from '../src/store/migrations.ts';
import { testDatabase, type TestDatabase } from './harness/database.ts';
import { checkRoleAttributes, runRolesSql } from './harness/roles.ts';

let db: TestDatabase;
const scratch: string[] = [];

beforeAll(async () => {
  db = await testDatabase();
});

afterAll(async () => {
  await db?.drop();
  for (const d of scratch) rmSync(d, { recursive: true, force: true });
});

const H = ['o1', 'h@example.com'];

async function code(promise: Promise<unknown>): Promise<string | undefined> {
  try {
    await promise;
    return undefined;
  } catch (error) {
    return (error as { code?: string }).code;
  }
}

describe('roles.sql (D-CG-OI-15, amendment 2)', () => {
  it('runs twice, and twice concurrently, leaving the same roles and grants', async () => {
    const su = await db.superuser();
    const other = await db.superuser();
    try {
      await runRolesSql(su, db.name);
      await runRolesSql(su, db.name);
      await Promise.all([runRolesSql(su, db.name), runRolesSql(other, db.name)]);
      const { rows } = await su.query<{ n: string }>(
        "SELECT count(*) AS n FROM pg_roles WHERE rolname IN ('soorma_org_migrator', 'soorma_org_app')",
      );
      expect(rows[0]!.n).toBe('2');
      await checkRoleAttributes(su);
      const acl = await su.query<{ datacl: string }>(
        'SELECT datacl::text FROM pg_database WHERE datname = $1',
        [db.name],
      );
      expect(acl.rows[0]!.datacl).toContain('soorma_org_app=c/');
      expect(acl.rows[0]!.datacl).not.toMatch(/(^|[{,])=[^,}]*c/);
    } finally {
      await su.end();
      await other.end();
    }
  });

  it('requires the database parameter, and refuses one naming another database', async () => {
    const su = await db.superuser();
    try {
      await su.query("SELECT set_config('soorma.target_database', 'elsewhere', false)");
      await expect(
        su.query(
          (await import('node:fs')).readFileSync(
            new URL('../../../deploy/local/db/roles.sql', import.meta.url),
            'utf8',
          ),
        ),
      ).rejects.toThrow('is not the connected database');
    } finally {
      await su.end();
    }
    const fresh = await db.superuser();
    try {
      await expect(fresh.query("SELECT current_setting('soorma.target_database')")).rejects.toThrow(
        'unrecognized configuration parameter',
      );
    } finally {
      await fresh.end();
    }
  });

  it('the attribute check fails on a role with CREATEDB, and never alters it', async () => {
    const su = await db.superuser();
    const role = `soorma_check_${Date.now()}`;
    try {
      await su.query(`CREATE ROLE ${role} LOGIN CREATEDB`);
      await expect(checkRoleAttributes(su, [role])).rejects.toThrow(`${role} has CREATEDB`);
      const { rows } = await su.query<{ rolcreatedb: boolean }>(
        'SELECT rolcreatedb FROM pg_roles WHERE rolname = $1',
        [role],
      );
      expect(rows[0]!.rolcreatedb).toBe(true);
    } finally {
      await su.query(`DROP ROLE IF EXISTS ${role}`);
      await su.end();
    }
  });
});

describe('TC-OI-051: S1 holds only the app role, with exactly its privileges', () => {
  it('the app role can insert into every table, the identity sequence included', async () => {
    const app = await db.app();
    try {
      await app.query(
        `INSERT INTO principals (organization, principal, state, registered_at, registered_by_environment)
         VALUES ($1, $2, 'pending', now(), 'e')`,
        H,
      );
      await app.query(
        `INSERT INTO materials (id, organization, principal, class, state, verifier, enrolled_at, enrolled_by)
         VALUES ('m1', $1, $2, 'K', 'enrollment', '$argon2id$x', now(), 'configuration')`,
        H,
      );
      await app.query(
        `INSERT INTO pending_second_factors (organization, principal, id, authenticator_type, seed, expires_at)
         VALUES ($1, $2, 'p1', 'totp', '{}', now())`,
        H,
      );
      await app.query(
        `INSERT INTO sign_ins (id, organization, principal, authenticated_at, classes, expires_at, state)
         VALUES ('s1', $1, $2, now(), ARRAY['K'], now(), 'live')`,
        H,
      );
      const fa = await app.query<{ id: string }>(
        `INSERT INTO failed_attempts (organization, principal, surface, at, refused_by_bound)
         VALUES ($1, $2, 'authenticate', now(), false) RETURNING id`,
        H,
      );
      expect(Number(fa.rows[0]!.id)).toBeGreaterThan(0);
      await app.query('INSERT INTO attempt_slots (slot) VALUES (7)');
      await app.query('DELETE FROM failed_attempts');
      await app.query('DELETE FROM sign_ins');
      await app.query('DELETE FROM pending_second_factors');
    } finally {
      await app.end();
    }
  });

  it('the app role has no DDL, and cannot read the migrations table', async () => {
    const app = await db.app();
    try {
      expect(await code(app.query('CREATE TABLE x (y int)'))).toBe('42501');
      expect(await code(app.query('DROP TABLE principals'))).toBe('42501');
      expect(await code(app.query('SELECT * FROM schema_migrations'))).toBe('42501');
    } finally {
      await app.end();
    }
  });
});

describe('TC-OI-022: no operation deletes a human principal (the database enforces it)', () => {
  it('the app role has no DELETE on principals, materials, or attempt slots', async () => {
    const app = await db.app();
    try {
      expect(await code(app.query('DELETE FROM principals'))).toBe('42501');
      expect(await code(app.query('DELETE FROM materials'))).toBe('42501');
      expect(await code(app.query('DELETE FROM attempt_slots'))).toBe('42501');
      expect(await code(app.query('TRUNCATE principals'))).toBe('42501');
    } finally {
      await app.end();
    }
  });

  it('the store refuses two current records of one class for a principal', async () => {
    const app = await db.app();
    try {
      await app.query(
        `INSERT INTO principals (organization, principal, state, registered_at, registered_by_environment)
         VALUES ('o1', 'g@example.com', 'pending', now(), 'e')`,
      );
      const insert = (id: string) =>
        app.query(
          `INSERT INTO materials (id, organization, principal, class, state, verifier, enrolled_at, enrolled_by)
           VALUES ($1, 'o1', 'g@example.com', 'K', 'enrollment', 'v', now(), 'configuration')`,
          [id],
        );
      await insert('g1');
      expect(await code(insert('g2'))).toBe('23505');
      expect(
        await code(
          app.query("UPDATE materials SET state = 'retired', retired_at = now() WHERE id = 'g1'"),
        ),
      ).toBe('23514');
    } finally {
      await app.end();
    }
  });
});

describe('TC-OI-051: migrations run once, as the migrator, and never change once applied', () => {
  async function emptyStore(): Promise<{ db: TestDatabase; dir: string }> {
    const fresh = await testDatabase({ empty: true });
    const dir = mkdtempSync(join(tmpdir(), 'soorma-migrations-'));
    scratch.push(dir);
    cpSync(MIGRATIONS_DIR, dir, { recursive: true });
    return { db: fresh, dir };
  }

  it('applies each migration once, also under concurrent runs', async () => {
    const { db: fresh, dir } = await emptyStore();
    const a = await fresh.migrator();
    const b = await fresh.migrator();
    try {
      const [ra, rb] = await Promise.all([migrate(a, dir), migrate(b, dir)]);
      expect([...ra, ...rb]).toEqual(['0001_init']);
      expect(await migrate(a, dir)).toEqual([]);
      const { rows } = await a.query<{ owner: string }>(
        "SELECT tableowner AS owner FROM pg_tables WHERE tablename = 'principals'",
      );
      expect(rows[0]!.owner).toBe('soorma_org_migrator');
    } finally {
      await a.end();
      await b.end();
      await fresh.drop();
    }
  });

  it('fails the run when an applied migration has changed, or a later one fails', async () => {
    const { db: fresh, dir } = await emptyStore();
    const m = await fresh.migrator();
    try {
      await migrate(m, dir);
      writeFileSync(join(dir, '0002_later.sql'), 'CREATE TABLE later (x int); SELECT 1/0;');
      await expect(migrate(m, dir)).rejects.toThrow(MigrationError);
      const { rows } = await m.query("SELECT to_regclass('later') AS t");
      expect(rows[0]!.t).toBeNull();
      writeFileSync(join(dir, '0002_later.sql'), 'CREATE TABLE later (x int);');
      expect(await migrate(m, dir)).toEqual(['0002_later']);
      writeFileSync(join(dir, '0001_init.sql'), '-- edited\n');
      await expect(migrate(m, dir)).rejects.toThrow('applied migration 0001_init has changed');
    } finally {
      await m.end();
      await fresh.drop();
    }
  });

  it('the app role cannot migrate', async () => {
    const { db: fresh, dir } = await emptyStore();
    const app = await fresh.app();
    try {
      await expect(migrate(app, dir)).rejects.toThrow();
    } finally {
      await app.end();
      await fresh.drop();
    }
  });
});
