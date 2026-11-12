<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# data-gateway (S3)

An environment's data face for agent credentials. One runs in each environment (`e` and `e2` on
the local stack). An agent instance exchanges its logical agent's **registration secret** for a
short-lived **agent credential** for this environment only, and renews it. Its operations are
defined in [`contract/data-gateway.openapi.yaml`](../../contract/data-gateway.openapi.yaml):

| Operation              | Request                                   | What it does                                                                                                                                                                                                                                     |
| ---------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `exchangeBootstrap`    | `POST /agent-credentials`                 | With `{ agent, secret, instance }` and no credential header: an active secret of a registered, unrevoked agent gets a credential naming the agent, the environment, and the asserted instance. Every failure is the same `authentication_failed` |
| `renewAgentCredential` | `POST /agent-credentials/current/renewal` | With the credential and no body: a new token for the same credential, expiring 15 minutes from now but never past 24 hours from its bootstrap. Refused once the credential or its agent is revoked                                               |

**A credential works only in the environment that issued it.** It is signed with that
environment's own **agent** key ring (never the key ring S2 uses for humans), carries its
organization, project, and environment, and is checked against its record and the environment's
revocation state on every renewal. Neither operation carries an envelope. S3 never calls the
organization level: it starts and serves with S1 stopped.

## Running it

S3 runs as part of the local stack; see
[`services/org-gateway/README.md`](../org-gateway/README.md#running-the-local-stack) for the
prerequisites. `pnpm stack:init` generates each environment's S3 secrets (its agent signing key
and that key's verify half, the bound's counter secret, its database role's password, and its
TLS certificate, all named `{env}-…`), and `pnpm stack:up` starts S3 beside S2.

| Environment | Edge                     | Database role     |
| ----------- | ------------------------ | ----------------- |
| `e`         | `https://localhost:8444` | `soorma_env_data` |
| `e2`        | `https://localhost:8445` | `soorma_env_data` |

Each edge is on the host's loopback only, with a certificate from the local CA. S3 joins its own
environment's network only, connects to the store as its own role, `soorma_env_data`, which holds
only what S3's statements need, and sees only its own secrets: never S2's passwords, the
migrator's, the human key ring, the caller key, or a log-pseudonym key. Its image holds no
organization-level code, no human identity resolution, no evaluator, and no migrations
(`{env}-migrate` applies them).

`pnpm stack:smoke` registers an agent through S2 in each environment, bootstraps and renews it at
that environment's S3, and checks that E's credential is refused at E2's S3. `pnpm stack:outage`
shows S3 serving both operations with S1 stopped (Case 3).

## Operations

### Rotating E's agent key

S3 signs with `dataGateway.keys.signing` and accepts any key in `keys.verify`. A token lives at
most 15 minutes, so the old key must keep verifying that long:

1. Generate the new key (`pnpm stack:init` writes `{env}-agent-signing-key-{n}` and its verify
   half for a new name), add it to E's `keys.verify` (and, from U7, its verify half to S4's
   agent verify keys), and restart every S3 of E.
2. Make the new key E's `keys.signing`, and restart every S3 of E.
3. Wait at least 15 minutes after step 2: the longest a token signed by the old key can live.
   Then remove the old key from `keys.verify` (and from S4's), and restart.

S3 refuses to start if `keys.verify` does not include `keys.signing`, lists a name twice, or names
a secret S2's part or another environment's part names.

### The bound's counter secret

The bootstrap bound counts attempts per agent in slots keyed by `{env}-bootstrap-counter-secret`.
To replace it, write a new file and restart S3: the slots re-key, so every agent's window starts
empty. Replacing it only ever forgets attempts; it never admits a secret.

### The lockout residual

The bound is keyed on the presented agent identifier, so an outsider who knows an agent's
identifier can stop its new instances from bootstrapping while an attack lasts, and for at most
60 seconds after it stops. Running instances renew unaffected: renewal is outside the bound. The
first hosted deployment counts an attempt carrying a real secret id against that secret record
instead, so legitimate restarts are not blocked.

### When the store is down

Both operations answer `503` with `Retry-After: 5`, and nothing is written. A revocation that
cannot be read is never treated as no revocation.

### When the organization level is down

Nothing changes: S3 has no dependency on S1, and starts without it.

### The fixed values

The propagation bound (60 seconds), a credential's lifetime (15 minutes), and a lineage's
maximum age (24 hours) are code constants in `@soorma/credentials`, not configuration. The
contract publishes them in
[`contract/conventions/credentials.md`](../../contract/conventions/credentials.md#revocation-and-lifetimes).

### Upgrading a local stack to U6

The store's roles are created when it first starts, so a store initialised before U6 has no
`soorma_env_data`, and migration `0003` fails at its first grant. Re-create the stack once:
`pnpm stack:down -v`, `pnpm stack:init`, `pnpm stack:up`. CI always starts fresh.

## What it keeps, and what it does not

- A credential record per bootstrap (its lineage), whose expiry renewal moves, and an attribution
  record for each operation, in the environment's own store, written in one transaction. Records
  are never deleted, and `soorma_env_data` holds no `DELETE` anywhere
- No token and no secret: a registration secret is compared with its stored digest, in constant
  time, whether or not a record exists
- Failed bootstrap attempts, recorded off the response path, only for an agent registered here
- Logs are JSON on stdout, naming the agent, the instance, and the environment, never a secret,
  its id, its digest, a token, or a human
- At most 64 requests in flight; beyond that, `503` with `Retry-After: 5`

## Layout

| Path                 | What it is                                                                                               |
| -------------------- | -------------------------------------------------------------------------------------------------------- |
| `src/main.ts`        | S3: configuration, the agent key ring, the store as `soorma_env_data`, the attempt writer, two listeners |
| `src/healthcheck.ts` | The Compose healthcheck (the image has no shell)                                                         |
| `src/edge/`          | The two operations, in the check order                                                                   |
| `src/throttle.ts`    | The request limit                                                                                        |
| `Dockerfile`         | The image: built on `node:26.13.0`, run on distroless, both pinned by digest; S3's closure only          |
| `test/`              | Tests                                                                                                    |

The domain lives in the workspace packages: `@soorma/credentials` (P5),
`@soorma/agent-identity` (P6's agent half), `@soorma/abuse-bound` (P8),
`@soorma/registry` (P4), `@soorma/attribution` (P7), `@soorma/env-store`,
`@soorma/service-kit`, `@soorma/perimeter` (P1), and `@soorma/config` (P9).
