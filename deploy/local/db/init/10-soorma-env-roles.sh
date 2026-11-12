#!/bin/sh
# SPDX-License-Identifier: FSL-1.1-ALv2
#
# Runs once, at an environment store's first start (the postgres image's init
# hook), as the superuser: creates the roles from env-roles.sql, with the
# grants for this database, then sets their passwords from this environment's
# secret files. SOORMA_ENVIRONMENT names the environment (not a secret; U4
# D-CG-EHA-23). The passwords are read inside psql (\set with a backquoted
# cat), so they are never on a command line or in the environment.
set -eu

env=${SOORMA_ENVIRONMENT:?SOORMA_ENVIRONMENT names the environment of this store}
case $env in
  *[!a-z0-9-]* | '') echo "not an environment id" >&2; exit 2 ;;
esac

psql -v ON_ERROR_STOP=1 --no-psqlrc --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=target_database="$POSTGRES_DB" \
  --set=migrator_file="/run/secrets/$env-db-migrator-password" \
  --set=app_file="/run/secrets/$env-db-app-password" \
  --set=data_file="/run/secrets/$env-db-data-password" <<'SQL'
SELECT set_config('soorma.target_database', :'target_database', false);
\i /soorma/db/env-roles.sql
\set migrator_password `cat :migrator_file`
\set app_password `cat :app_file`
\set data_password `cat :data_file`
ALTER ROLE soorma_env_migrator PASSWORD :'migrator_password';
ALTER ROLE soorma_env_app PASSWORD :'app_password';
ALTER ROLE soorma_env_data PASSWORD :'data_password';
SQL
