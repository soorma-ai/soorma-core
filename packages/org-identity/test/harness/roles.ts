// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The harness's use of deploy/local/db/roles.sql, the file the stack's init
// script runs (D-CG-OI-15, amendment 2).
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import pg from 'pg';

export const ROLES_SQL = resolve(import.meta.dirname, '../../../../deploy/local/db/roles.sql');
export const MIGRATOR = 'soorma_org_migrator';
export const APP = 'soorma_org_app';

/** Runs roles.sql in the connected database, with the database name bound as the parameter. */
export async function runRolesSql(client: pg.ClientBase, database: string): Promise<void> {
  await client.query("SELECT set_config('soorma.target_database', $1, false)", [database]);
  await client.query(readFileSync(ROLES_SQL, 'utf8'));
}

/**
 * Checks each role's attributes and fails on a difference; it never corrects
 * one, because roles are server-wide and roles.sql never alters an existing role.
 */
export async function checkRoleAttributes(
  client: pg.ClientBase,
  roles: readonly string[] = [MIGRATOR, APP],
): Promise<void> {
  const { rows } = await client.query<{
    rolname: string;
    rolcanlogin: boolean;
    rolsuper: boolean;
    rolcreatedb: boolean;
    rolcreaterole: boolean;
    rolreplication: boolean;
    rolbypassrls: boolean;
  }>(
    `SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
       FROM pg_catalog.pg_roles WHERE rolname = ANY ($1)`,
    [roles],
  );
  const problems: string[] = [];
  for (const role of roles) {
    const r = rows.find((x) => x.rolname === role);
    if (!r) {
      problems.push(`${role} does not exist`);
      continue;
    }
    if (!r.rolcanlogin) problems.push(`${role} cannot log in`);
    for (const [flag, on] of [
      ['SUPERUSER', r.rolsuper],
      ['CREATEDB', r.rolcreatedb],
      ['CREATEROLE', r.rolcreaterole],
      ['REPLICATION', r.rolreplication],
      ['BYPASSRLS', r.rolbypassrls],
    ] as const) {
      if (on) problems.push(`${role} has ${flag}`);
    }
  }
  if (problems.length > 0)
    throw new Error(`role attributes differ from roles.sql: ${problems.join('; ')}`);
}
