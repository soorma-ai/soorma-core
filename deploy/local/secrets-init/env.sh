#!/bin/sh
# SPDX-License-Identifier: FSL-1.1-ALv2
#
# An environment's one-shot secrets copy (U4 Infrastructure Design §3; U2
# Q-CG-4 B). Its only argument is the environment id, which is not a secret.
# Compose mounts only that environment's `file:` secrets here, and the CA
# certificate (public). Each is copied into the {env}-secrets volume, in one
# subdirectory per consuming service, owned by that service's user, mode 0400
# (directories 0500). Each service mounts only its own subdirectory, read-only.
# Every run starts from an empty volume, so a removed or rotated secret never
# lingers. It prints names only, never a value.
set -eu

env=${1:?usage: env.sh <environment>}
case $env in
  *[!a-z0-9-]* | '') echo "not an environment id" >&2; exit 2 ;;
esac

copy() { # copy <service> <uid> <secret>...
  service=$1 uid=$2
  shift 2
  install -d -o "$uid" -g "$uid" -m 0500 "/out/$service"
  for name in "$@"; do
    install -o "$uid" -g "$uid" -m 0400 "/run/secrets/$name" "/out/$service/$name"
  done
  echo "$service: $*"
}

find /out -mindepth 1 -delete

# The environment store (postgres, 999).
copy db 999 \
  "$env-db-tls" "$env-db-superuser-password" "$env-db-app-password" \
  "$env-db-migrator-password" "$env-db-data-password"

# {env}-migrate (distroless nonroot, 65532): the migrator password and the CA only.
copy migrate 65532 \
  "$env-db-migrator-password" stack-ca-cert

# {env}-backup and {env}-restore (postgres, 999; U5 NP-AR-08): the migrator
# password and the CA only, in their own subdirectory, since migrate/ is owned
# by 65532 and unreadable by 999.
copy backup 999 "$env-db-migrator-password" stack-ca-cert

# {env}-restore (postgres, 999; U6 D-ID-AC-14): the migrator password and the CA
# only, in its own subdirectory.
copy restore 999 "$env-db-migrator-password" stack-ca-cert

# {env}-control-gateway (distroless nonroot, 65532): never the migrator password.
copy control-gateway 65532 \
  "$env-control-gateway-tls" stack-ca-cert "$env-db-app-password" \
  "$env-signing-key-1" "$env-caller-key" "$env-log-pseudonym-key"

# {env}-data-gateway (distroless nonroot, 65532; U6 D-ID-AC-09): its own role's
# password, never the app or migrator password; the agent ring, never the human
# one; the bound's counter secret.
copy data-gateway 65532 \
  "$env-data-gateway-tls" stack-ca-cert "$env-db-data-password" \
  "$env-agent-signing-key-1" "$env-bootstrap-counter-secret"
