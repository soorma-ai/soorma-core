// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The statement brand, and the statements of the shared transaction helper and
// migration runner (D-CG-OI-04; NFR-OI-17). Moved from @soorma/org-identity (U4
// NP-EHA-15). Every package keeps its own statements in its own src/sql.ts. Each is a
// constant string with $n placeholders; values are always bound parameters,
// never interpolated. The `sql` check (tools/checks) fails on a query whose
// statement is not from this module, and on a template literal with a
// substitution here.
declare const statementBrand: unique symbol;

/** A statement from this module. The store's query methods accept nothing else. */
export type Statement = string & { readonly [statementBrand]: true };

/**
 * Declares a statement. Called only in a package's src/sql.ts (the `sql` check
 * enforces it), with a constant string.
 */
export const statement = (text: string): Statement => text as Statement;
const sql = statement;

/**
 * A migration file's text, run by the migration runner only. Migration files
 * are SQL source in the repository, reviewed like code, with no parameters.
 */
export function migrationStatement(fileText: string): Statement {
  return fileText as Statement;
}

export const SQL = {
  begin: sql('BEGIN'),
  commit: sql('COMMIT'),
  rollback: sql('ROLLBACK'),

  // The migration runner (NFR-OI-18): one session lock for the whole run.
  migrationLock: sql('SELECT pg_advisory_lock($1::bigint)'),
  migrationUnlock: sql('SELECT pg_advisory_unlock($1::bigint)'),
  createMigrationsTable: sql(
    `CREATE TABLE IF NOT EXISTS schema_migrations (
       version text PRIMARY KEY,
       checksum text NOT NULL,
       applied_at timestamptz NOT NULL DEFAULT now()
     )`,
  ),
  appliedMigrations: sql('SELECT version, checksum FROM schema_migrations ORDER BY version'),
  recordMigration: sql('INSERT INTO schema_migrations (version, checksum) VALUES ($1, $2)'),
};
