<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# org-gateway (S1)

The organization level's control face. It holds the organization's human principals and
their authentication material, and issues the **organization sign-in**. Its operations are
defined in [`contract/org-gateway.openapi.yaml`](../../contract/org-gateway.openapi.yaml):

| Operation           | Request                          | What it does                                                                                  |
| ------------------- | -------------------------------- | --------------------------------------------------------------------------------------------- |
| `firstAuthenticate` | `POST /first-authentication`     | A configured first Admin sets their own secret (K), presenting single-use enrollment material |
| `authenticate`      | `POST /sign-ins`                 | Sign in with K, or K and a TOTP code once a second factor (P) is enrolled                     |
| `renewSignIn`       | `POST /sign-ins/current/renewal` | A new token for the same sign-in, never past 12 hours after authentication                    |
| `endSignIn`         | `POST /sign-ins/current/end`     | The logout                                                                                    |
| `changeMaterial`    | `POST /material-changes`         | Replace K, or begin and confirm P, presenting the current material. Ends every live sign-in   |

It also serves a separate **internal listener** for environments (verify-only keys, whether a
principal exists, a sign-in's status), where every call is a signed request from a configured
environment key. That interface is not published, and nothing on it is unauthenticated.

## Running the local stack

Prerequisites: **Docker Engine 26 or later** and **Docker Compose 2.26.0 or later** (the stack
mounts each service's own subpath of a secrets volume; `pnpm stack:up` checks both and refuses
to start otherwise), Node 26.13.0, pnpm 12.18.0, and the OpenSSL CLI.

```sh
pnpm install --frozen-lockfile
pnpm stack:init     # every secret, into deploy/local/.secrets/ (mode 0600; never overwritten)
pnpm stack:up       # build the images, migrate the stores, start S1 and each environment's S2
pnpm stack:smoke    # optional: the smoke test CI runs
pnpm stack:down     # pnpm stack:down -v also removes the store's data and the secret copies
```

**How secrets reach the containers.** The files in `deploy/local/.secrets/` are read only by a
one-shot `org-secrets-init` container, which copies each into the `org-secrets` Docker volume,
one subdirectory per service, owned by that service's user, mode 0400. Each service mounts only
its own subdirectory, read-only, at `/run/secrets`. The copies sit in Docker's volume storage on
the same host as `.secrets/`; `pnpm stack:down -v` removes them. Secrets never pass through an
environment variable.

`stack:init` prints the path of a **one-time handover file**,
`deploy/local/.secrets/handover/first-admin-1.txt`, holding the first Admin's enrollment
material. Use it once, at first authentication, then delete the file. Once used, the material
never verifies again.

The edge listens on **`https://localhost:8441`**, on the host's loopback only. Its certificate
is issued by a local CA that `stack:init` creates, name-constrained to `localhost`,
`soorma.internal`, and the loopback addresses. **Pass the CA explicitly; never install it in
the system trust store:**

```sh
curl --cacert deploy/local/.secrets/stack-ca.pem \
  -H 'content-type: application/json' -H 'soorma-contract-version: 0.1.0' \
  --data @first-authentication.json https://localhost:8441/first-authentication
```

`pnpm stack:certs` reissues the service certificates (they are valid 90 days).

## What it keeps, and what it does not

- K and enrollment material only as Argon2id verifiers (64 MiB, 3 passes, the full
  NFKC-normalized input); TOTP seeds encrypted with AES-256-GCM, bound to their row
- No key material in the store: every key comes from configuration, delivered as a Compose
  secret file, never an environment variable
- Logs are JSON on stdout and never carry a secret or a human identifier: a human is named by
  a keyed pseudonym (`hp_…`)
- Principals and material are never deleted; the app role has no `DELETE` on them

**At rest:** the org store is not encrypted at rest in M1 (by decision; carried to the first
hosted deployment). On a workstation, use host full-disk encryption.

## Operations

### Rotating the signing key

S1 signs sign-ins with `keys.signing` and accepts any key in `keys.verify` (in
`deploy/local/config/tenancy.yaml`). Every environment's S2 verifies sign-ins with the keys it
fetches from S1, so a rotation has three steps:

1. Generate the new key, add it to `keys.verify`, and restart S1. It is published as a verify key
   but signs nothing yet.
2. **Wait at least 5 minutes**, then make the new key `keys.signing` and restart S1.
3. Once every token the old key signed has expired (15 minutes after step 2), remove the old key
   from `keys.verify`, and restart S1.

**Why at least 5 minutes:** every environment's S2 refreshes S1's verify keys every 5 minutes.
The wait lets each S2 hold the new key before the first sign-in it signs reaches it. An S2 whose
refresh failed or ran late still recovers: a sign-in under a key it does not hold makes it fetch
again, at most once every 30 seconds. "No valid sign-in is refused during a rotation" depends on
both the wait and that fetch.

### Internal callers

Each environment's S2 calls S1's internal listener with requests signed by its own **caller
key**. S1 holds only the public half, named in `organizationLevel.internalCallers`:

```yaml
internalCallers:
  - environment: e
    publicKeys: [e-caller-public-key]
```

`pnpm stack:init` derives `{env}-caller-public-key` from the environment's `{env}-caller-key`;
the private half never leaves that environment's secrets.

**Adding an environment:** add its entry, run `pnpm stack:init`, and restart S1.

**Rotating an environment's caller key**, with no window in which its calls are refused:

1. Add the new public key to the environment's `publicKeys`, and restart S1.
2. Switch the environment's `controlGateway.keys.caller` to the new private key, and restart
   that environment's S2.
3. Remove the old public key, and restart S1.

**S1 refuses to start** when a caller could be attributed to the wrong environment: an
environment listed twice; a secret name listed twice; or a key, by `kid` (its RFC 7638
thumbprint), that appears twice within one environment or in more than one environment. The
`kid` checks run on the loaded keys, so two files holding the same key are caught.

## Layout

| Path                  | What it is                                                                   |
| --------------------- | ---------------------------------------------------------------------------- |
| `src/main.ts`         | S1: configuration, the key ring, the store, the first Admin, three listeners |
| `src/migrate.ts`      | `org-migrate`: the one-shot migration run, as the migrator role              |
| `src/healthcheck.ts`  | The Compose healthcheck (the image has no shell)                             |
| `src/edge/`           | The five operations, in U1's check order                                     |
| `src/internal/`       | The internal listener and its signed-request check                           |
| `Dockerfile`          | The image: built on `node:26.13.0`, run on distroless, both pinned by digest |
| `test/`, `test/perf/` | Tests; the latency and timing measurements (`pnpm test:perf`)                |

The domain lives in the workspace packages: `@soorma/org-identity` (principals, material,
sign-ins, keys, the store), `@soorma/abuse-bound`, `@soorma/identity-resolution`,
`@soorma/perimeter`, and `@soorma/config`.
