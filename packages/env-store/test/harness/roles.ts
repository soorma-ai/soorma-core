// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The harness's use of deploy/local/db/env-roles.sql, the file each
// environment's init script runs (U4 Infrastructure Design §6; D-CG-EHA-07).
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type pg from 'pg';
import { checkRoleAttributes } from '../../../org-identity/test/harness/roles.ts';

export const ENV_ROLES_SQL = resolve(
  import.meta.dirname,
  '../../../../deploy/local/db/env-roles.sql',
);
export const ENV_MIGRATOR = 'soorma_env_migrator';
export const ENV_APP = 'soorma_env_app';

/** Runs env-roles.sql in the connected database, with the database name bound as the parameter. */
export async function runEnvRolesSql(client: pg.ClientBase, database: string): Promise<void> {
  await client.query("SELECT set_config('soorma.target_database', $1, false)", [database]);
  await client.query(readFileSync(ENV_ROLES_SQL, 'utf8'));
}

/** The environment roles' attributes, as env-roles.sql creates them. */
export function checkEnvRoleAttributes(client: pg.ClientBase): Promise<void> {
  return checkRoleAttributes(client, [ENV_MIGRATOR, ENV_APP]);
}
