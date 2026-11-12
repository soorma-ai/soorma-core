-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- An environment store's roles and their database-level privileges (U4
-- Infrastructure Design §6), as deploy/local/db/roles.sql does for the org
-- store (D-CG-OI-15, amendment 2). The same role names in every environment's
-- instance, because the migrations are shared and grant to fixed names;
-- isolation is by instance, password, certificate, and network. Run as the
-- server's superuser by:
--   - the stack's init script, once, against the stack's database
--   - the test harness, against its template database, then against each
--     database cloned from it (PostgreSQL copies no database-level privilege
--     from a template)
--
-- Safe to run twice, and concurrently: each role is created only if absent,
-- and an existing role is never altered, so a re-run writes nothing to the
-- server-wide catalog. Passwords are never in this file: the caller sets them.
--
-- Concurrent runs are serialized (U4 D-CG-EHA-15): the whole file is one
-- explicit transaction that first takes a transaction-level advisory lock, so
-- two runs never grant or revoke on the same catalog row at once ("tuple
-- concurrently updated"). The block is explicit because psql's \i commits
-- each statement on its own; a bare transaction-level lock would be released
-- at once. The key, 3602168843343665555, is the first 63 bits of
-- SHA-256("soorma.env.roles"), derived as the migration lock's is.
--
-- Parameter: the session setting soorma.target_database, the database the
-- grants are for. The caller sets it before running this file (psql: :'name';
-- the harness: a bound query parameter). current_setting fails when it is
-- unset, and it must name the connected database.

BEGIN;
SELECT pg_advisory_xact_lock(3602168843343665555);

DO $roles$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'soorma_env_migrator') THEN
    BEGIN
      CREATE ROLE soorma_env_migrator
        LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    EXCEPTION WHEN duplicate_object OR unique_violation THEN
      NULL; -- created by a concurrent run
    END;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'soorma_env_app') THEN
    BEGIN
      CREATE ROLE soorma_env_app
        LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    EXCEPTION WHEN duplicate_object OR unique_violation THEN
      NULL; -- created by a concurrent run
    END;
  END IF;
  -- S3's own role (U6 D-ID-AC-07, the user's decision): least privilege per
  -- deployable. Its table grants are in env-store's 0003 only.
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'soorma_env_data') THEN
    BEGIN
      CREATE ROLE soorma_env_data
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
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO soorma_env_migrator, soorma_env_app', target);
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO soorma_env_data', target);
END
$database$;

-- Schema privileges, in the connected database: the migrator creates the
-- tables (and owns them); the app role only uses them, with the table grants
-- the migrations make.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO soorma_env_migrator;
GRANT USAGE ON SCHEMA public TO soorma_env_app;
GRANT USAGE ON SCHEMA public TO soorma_env_data;

COMMIT;
