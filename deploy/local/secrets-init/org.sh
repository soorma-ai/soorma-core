#!/bin/sh
# SPDX-License-Identifier: FSL-1.1-ALv2
#
# org-secrets-init: the organization level's one-shot secrets copy
# (Infrastructure Design §3, §7, amended at Code Generation, Q-CG-4 B).
#
# Runs as root with only CHOWN, DAC_OVERRIDE, and FOWNER, no network, and a
# read-only root. Reads this level's Compose file: secrets from /run/secrets
# (host files, 0600) and copies each into the org-secrets volume (/out), one
# subdirectory per consuming service, with that service's owner and mode 0400
# (directories 0500). Each service mounts only its own subdirectory, read-only.
# Every run starts from an empty volume, so a removed or rotated secret never
# lingers. It prints names only, never a value.
set -eu

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

# The org store (postgres, 999).
copy org-db 999 \
  org-db-tls org-db-superuser-password org-db-app-password org-db-migrator-password

# org-migrate (distroless nonroot, 65532): the migrator password and the CA only.
copy org-migrate 65532 \
  org-db-migrator-password stack-ca-cert

# org-gateway (distroless nonroot, 65532): never the migrator password.
copy org-gateway 65532 \
  org-gateway-tls stack-ca-cert org-db-app-password org-signing-key org-seed-key \
  org-counter-secret org-log-pseudonym-key org-enrollment-1
