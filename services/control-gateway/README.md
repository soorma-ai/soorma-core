<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# control-gateway (S2)

An environment's control face. One runs in each environment (`e` and `e2` on the local stack).
It turns a human's **organization sign-in** from S1 into an **environment credential** for its
own environment only, and records the grants that give a human permissions there. It also
registers logical agents and issues their registration secrets (U5). Its operations are defined
in
[`contract/control-gateway.openapi.yaml`](../../contract/control-gateway.openapi.yaml):

| Operation                    | Request                                         | What it does                                                                                                                                                                                                                                                                                                                               |
| ---------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `issueEnvironmentCredential` | `POST /environment-credentials`                 | Presenting a live S1 sign-in, a human who holds a grant in this environment gets a credential for it (15 minutes, never past the sign-in's expiry)                                                                                                                                                                                         |
| `renewEnvironmentCredential` | `POST /environment-credentials/current/renewal` | A new token for the same credential, while the sign-in it came from is still live                                                                                                                                                                                                                                                          |
| `endEnvironmentCredential`   | `POST /environment-credentials/current/end`     | Ends the credential: every token for it is refused from then on                                                                                                                                                                                                                                                                            |
| `grantToHuman`               | `POST /grants`                                  | A human holding `grant:human` here grants accepted permissions to a principal of the same organization (a self-grant is allowed, and recorded)                                                                                                                                                                                             |
| `registerAgent`              | `POST /registrations`                           | A human holding `agent:register` here registers a logical agent they sponsor: its standing set must lie within what they hold, with no human-only permission, and its re-broadening declaration within the standing set. What they held is recorded as the ceiling snapshot. The identifier is the client's, unique here, and never reused |
| `issueRegistrationSecret`    | `POST /registration-secrets`                    | The agent's sponsor, or an Admin here (`grant:human` and `human:manage`), holding `agent:register`, gets a registration secret, returned once (`Cache-Control: no-store`). At most 10 are active per registration                                                                                                                          |

**A credential works only in the environment that issued it.** It is signed with that
environment's own key, carries its organization, project, and environment, and is checked
against its record in that environment's store on every use. Another environment's credential
is refused.

The configured first Admin receives the environment's first grant when S2 starts. S2 asks S1
whether a sign-in is live, and whether a principal exists, over S1's internal listener, with
requests signed by the environment's caller key. It verifies sign-ins with S1's published keys,
which it fetches every 5 minutes.

## Running it

S2 runs as part of the local stack; see
[`services/org-gateway/README.md`](../org-gateway/README.md#running-the-local-stack) for the
prerequisites. `pnpm stack:init` generates each environment's secrets (its signing key, caller
key, log-pseudonym key, and passwords, all named `{env}-…`), and `pnpm stack:up` starts, per
environment, a store, a one-shot migration, and S2.

| Environment | Edge                     | Store                                      |
| ----------- | ------------------------ | ------------------------------------------ |
| `e`         | `https://localhost:8442` | `env-db.e.soorma.internal`, not published  |
| `e2`        | `https://localhost:8443` | `env-db.e2.soorma.internal`, not published |

Each edge is on the host's loopback only, with a certificate from the local CA (pass
`--cacert deploy/local/.secrets/stack-ca.pem`). Each environment has its own network and its own
secrets volume; nothing of one environment reaches another, and no organization secret reaches
an environment. S2 does not hold the migrator's password.

`pnpm stack:smoke` signs in at S1, then issues, renews, grants, and ends at E, and checks that
E's credential is refused at E2. `pnpm stack:outage`, on a freshly started stack, runs the two
cases in [When the organization level is down](#when-the-organization-level-is-down).

## Operations

### Rotating E's minting key

S2 mints with `controlGateway.keys.signing` and accepts any key in `keys.verify`. Only S2
instances of the same environment verify its credentials, so no other service waits on this:

1. Generate the new key, add it to E's `keys.verify`, and restart every S2 of E.
2. Make the new key E's `keys.signing`, and restart every S2 of E.
3. Once every credential the old key minted has expired (15 minutes after step 2), remove the
   old key from `keys.verify`, and restart.

S2 refuses to start if `keys.verify` does not include `keys.signing`, lists a name twice, or
names a secret another environment's part names.

### Rotating E's caller key

From E's side of S1's [internal callers](../org-gateway/README.md#internal-callers), with no
window in which E's calls are refused:

1. Generate the new key, derive its public half (`pnpm stack:init` does both for a new name),
   add the public half to E's `publicKeys` in `organizationLevel.internalCallers`, and restart
   S1.
2. Switch E's `controlGateway.keys.caller` to the new private key, and restart E's S2.
3. Remove the old public key from E's `publicKeys`, and restart S1.

### When the organization level is down

S2 starts and serves without S1, and fails closed per operation:

| While S1 is down                                                                      | Result                                                                                  |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Issuance and renewal (each asks S1 whether the sign-in is live)                       | `503 unavailable`, `Retry-After: 5`; `orglevel.unavailable` is logged                   |
| `grantToHuman` (it asks S1 whether the target principal exists)                       | `503 unavailable`, `Retry-After: 5`                                                     |
| Ending a credential                                                                   | Works: it never calls S1                                                                |
| Checking a presented credential (its key, signature, expiry, environment, and record) | Unchanged: none of it calls S1. An ended, expired, or E2 credential is refused as usual |

Nothing is issued, renewed, or granted on state S2 could not read. Two cases differ in how
they recover:

- **S1 stops while S2 is running.** S2 keeps the verify keys it holds, because a failed fetch
  never discards them. Issuance recovers as soon as S1 answers.
- **S2 starts while S1 is down.** S2 holds no verify keys, so issuance is refused. Credentials
  issued before the restart still verify, because S2's own keys come from its configuration,
  and can be ended. Once S1 is back, issuance recovers at the next fetch: an issuance triggers
  one, at most once every 30 seconds, and the scheduled refresh runs every 5 minutes.

### Backing up and restoring the environment's store

```sh
pnpm stack:backup e            # writes deploy/local/.backups/e-{time}.dump
pnpm stack:restore e <file>    # into e's store, which must be empty
```

**A dump contains human identifiers**: sponsors, secret issuers, and the actors of attribution
records. It is written only to `deploy/local/.backups/`, which is git-ignored and
docker-ignored, **with mode `0600`** in a directory with mode `0700`, from the moment the file
is opened. **It never goes into the repository.** Delete a dump when you no longer need it.

- Each environment has a one-shot `{env}-backup` and `{env}-restore` service, under the Compose
  profile `backup`, so `stack:up` never starts them. Each runs as the store's migrator role, on
  the environment's own network (the store is not published), and mounts only its `backup/`
  secrets subdirectory. The password reaches `pg_dump` and `pg_restore` only through a pgpass
  file built inside the container from `/run/secrets`; `PGPASSFILE`, its path, is the only
  variable. The connection is `verify-full` against the stack CA
- The backup is a custom-format dump streamed to the host (`docker compose run --rm -T`, so no
  terminal alters it). After every backup, the archive is checked: it must begin with `PGDMP`,
  and a full read (`pg_restore --file=/dev/null`) must succeed; otherwise the file is deleted
  and the command fails
- The restore refuses a database that is not empty, then restores in one transaction, stopping
  at the first error. To restore over an environment: stop `{env}-control-gateway` and
  `{env}-db`, remove the `{env}-db-data` volume, start `{env}-db` alone, run
  `pnpm stack:restore`, then run `{env}-migrate` (it applies nothing to a current dump) and
  start `{env}-control-gateway`
- Replication, point-in-time recovery, and off-host, encrypted backups are not part of the local
  stack; they belong to the first hosted deployment

## What it keeps, and what it does not

- Credential records, grants, registrations, registration secrets, and an attribution record
  for each, in the environment's own store, written in one transaction per operation. Grants,
  registrations, and secrets are never updated or deleted, and the app role has only the column
  privileges each operation needs
- A registration secret only as a 32-byte digest, never the secret itself
- No sign-in, no password, and no organization key: S2 verifies sign-ins with S1's public keys
- Logs are JSON on stdout and never carry a token, a key, or a human identifier: a human is
  named by a pseudonym under the environment's own key, so it differs per environment
- At most 64 requests in flight, and at most 8 concurrent calls to S1 (each with a 2-second
  deadline); beyond that, `503` with `Retry-After: 5`

## Layout

| Path                  | What it is                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| `src/main.ts`         | S2: configuration, the key ring, the store, the first grant, the verify-key cache, two listeners |
| `src/migrate.ts`      | `{env}-migrate`: the one-shot migration run, as the migrator role                                |
| `src/healthcheck.ts`  | The Compose healthcheck (the image has no shell)                                                 |
| `src/edge/`           | The six operations, in the check order                                                           |
| `src/org-level.ts`    | The calls to S1's internal listener: signed, over TLS 1.3, to the local CA only                  |
| `src/verify-keys.ts`  | S1's verify keys: fetched every 5 minutes, and on an unknown key at most once every 30 seconds   |
| `src/throttle.ts`     | The request limit                                                                                |
| `Dockerfile`          | The image: built on `node:26.13.0`, run on distroless, both pinned by digest; no `org-identity`  |
| `test/`, `test/perf/` | Tests; the latency measurements (`pnpm test:perf:s2`)                                            |

The domain lives in the workspace packages: [`@soorma/credentials`](../../packages/credentials/README.md)
(P5), [`@soorma/registry`](../../packages/registry/README.md) (P4),
[`@soorma/attribution`](../../packages/attribution/README.md) (P7),
[`@soorma/env-store`](../../packages/env-store/README.md),
[`@soorma/service-kit`](../../packages/service-kit/README.md), `@soorma/authority` (P3),
`@soorma/perimeter` (P1), and `@soorma/config` (P9).
