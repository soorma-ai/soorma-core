#!/bin/sh
# SPDX-License-Identifier: FSL-1.1-ALv2
#
# Runs once, at the org store's first start (the postgres image's init
# hook), as the superuser: creates the roles from roles.sql, with the grants
# for this database, then sets their passwords from the Compose secret files.
# The passwords are read inside psql (\set with a backquoted cat), so they are
# never on a command line or in the environment.
set -eu

psql -v ON_ERROR_STOP=1 --no-psqlrc --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=target_database="$POSTGRES_DB" <<'SQL'
SELECT set_config('soorma.target_database', :'target_database', false);
\i /soorma/db/roles.sql
\set migrator_password `cat /run/secrets/org-db-migrator-password`
\set app_password `cat /run/secrets/org-db-app-password`
ALTER ROLE soorma_org_migrator PASSWORD :'migrator_password';
ALTER ROLE soorma_org_app PASSWORD :'app_password';
SQL
