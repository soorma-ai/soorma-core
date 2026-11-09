-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- The org store's roles and their database-level privileges (Infrastructure
-- Design §5; D-CG-OI-15, amendment 2). Run as the server's superuser by:
--   - the stack's init script, once, against the stack's database
--   - the test harness, against its template database, then against each
--     database cloned from it (PostgreSQL copies no database-level privilege
--     from a template)
--
-- Safe to run twice, and concurrently: each role is created only if absent,
-- and an existing role is never altered, so a re-run writes nothing to the
-- server-wide catalog. Passwords are never in this file: the caller sets them.
--
-- Parameter: the session setting soorma.target_database, the database the
-- grants are for. The caller sets it before running this file (psql: :'name';
-- the harness: a bound query parameter). current_setting fails when it is
-- unset, and it must name the connected database.

DO $roles$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'soorma_org_migrator') THEN
    BEGIN
      CREATE ROLE soorma_org_migrator
        LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    EXCEPTION WHEN duplicate_object OR unique_violation THEN
      NULL; -- created by a concurrent run
    END;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'soorma_org_app') THEN
    BEGIN
      CREATE ROLE soorma_org_app
        LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    EXCEPTION WHEN duplicate_object OR unique_violation THEN
      NULL; -- created by a concurrent run
    END;
  END IF;
END
$roles$;

DO $database$
DECLARE
  target text := current_setting('soorma.target_database');
BEGIN
  IF target IS DISTINCT FROM current_database() THEN
    RAISE EXCEPTION 'soorma.target_database (%) is not the connected database (%)',
      target, current_database();
  END IF;
  EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', target);
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO soorma_org_migrator, soorma_org_app', target);
END
$database$;

-- Schema privileges, in the connected database: the migrator creates the
-- tables (and owns them); the app role only uses them, with the table grants
-- the migrations make.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO soorma_org_migrator;
GRANT USAGE ON SCHEMA public TO soorma_org_app;
