# Infrastructure Design: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7). The first environment-level deployables: S2
`control-gateway` and the environment store, for E and E2
**Built against**: ID @ `prd-identity-v1.0`, PF @ `prd-platform-foundations-v1.3`
**Decisions from**: the Infrastructure Design plan, Q1 to Q3 and P-01 to P-11, answered
2026-11-11T06:52:06Z (verbatim in `audit.md`). Every answer is technology (I11); no
specification gap
**Rules applied**: [shared-infrastructure.md](../../shared-infrastructure.md), U2's. Every rule
applies; **no deviation**. What U4 settles for U5 to U7 is added there (§13)
**Companion**: [deployment-architecture.md](deployment-architecture.md)

M1 is the local Compose stack (M1-NFR-05). There is no cloud provider and no IaC.

---

## 1. Component → Infrastructure

`{env}` is `e` or `e2`. Each environment has exactly the same set; nothing is shared between them.

| Logical component (NFR Design) | Infrastructure | Decision |
|---|---|---|
| S2 `control-gateway` | Compose service `{env}-control-gateway`, image `soorma/control-gateway:local` | P-01, P-10 |
| `{env}-migrate` | Compose service `{env}-migrate`: the same image, `dist/migrate.js`; runs once and exits | P-01 |
| Environment store | Compose service `{env}-db`: PostgreSQL 18.4 at U2's digest; volume `{env}-db-data` | P-01, P-04 |
| E's secrets volume and copier | Volume `{env}-secrets`; one-shot service `{env}-secrets-init` | P-02 |
| Environment network | Network `{env}`: the store, migrate, and S2 | P-05 |
| The path to the organization level | Network `org-internal-{env}` (exists): S2 and `org-gateway` only | P-05 |
| E's configuration | `{env}`'s entry in `deploy/local/config/tenancy.yaml` gains a `controlGateway` part | P-06 |
| E's key material | Secret files: signing and verify keys, caller key, log-pseudonym key | P-03 |
| E's caller public key at S1 | Secret file `{env}-caller-public-key`, mounted into `org-gateway` only | P-03; Q2 A |
| Alert rules, dashboard | `deploy/monitoring/alerts.yaml`, `dashboard.yaml` | P-08 |
| Operations notes | `## Operations` in `services/org-gateway/README.md` and `services/control-gateway/README.md` | Q3 A |

**Compose structure (Q1 A)**: one `deploy/local/compose.yaml`, with **each environment's
services, volumes, networks, and secrets written out in full**. YAML anchors carry only the
shared shape: the hardening block, the S2 service body, and the database command. **Every
service name, volume subpath, network, and secret name is literal**, so a review sees exactly
what each container mounts, and the Compose-model test (§3) reads it directly.

## 2. Images

`services/control-gateway/Dockerfile` follows U2's (shared-infrastructure.md *Images*):
- two stages, `node:26.13.0` to build and `gcr.io/distroless/nodejs26-debian13:nonroot` to run,
  both pinned by digest;
- explicit copies only (the S2 service's `dist/`, the packages it links, `env-store`'s
  `migrations/`, the contract);
- `.dockerignore` as U2's.

**The image contains no `@soorma/org-identity`.** Its production dependency closure is checked
at Code Generation (NP-EHA-15). The healthcheck is the shared Node script.

## 3. Configuration and Secrets (P-02, P-03, P-06; O-4)

### Secrets: mounted files only

**No secret value is in an environment variable, a command line, `compose.yaml`,
`tenancy.yaml`, a Dockerfile, an image, or any committed file.** `tenancy.yaml` and the Compose
file name secrets; they never hold them.

| Step | What happens |
|---|---|
| Generate | `pnpm stack:init` writes one file per secret into `deploy/local/.secrets/` (git-ignored, 0600). It never overwrites one, and it prints names only |
| Reach the level's copier | Compose `file:` secrets for E are listed **only on `e-secrets-init`** (and E2's only on `e2-secrets-init`) |
| Copy | `deploy/local/secrets-init/env.sh {env}` (the environment id is its only argument, not a secret) copies each secret into the `{env}-secrets` volume. Each goes into the subdirectory of the service that needs it, owned by that service's user, mode 0400 (directories 0500). It starts from an empty volume each run |
| Mount | Each service mounts **only its own subpath, read-only, at `/run/secrets`** |

**Secrets per environment** (E shown; E2's carry `e2-`):

| Secret | Generated as | Copied into | Never in |
|---|---|---|---|
| `e-control-gateway-tls` | ECDSA P-256 key and certificate (§5) | `control-gateway` | Any other service |
| `e-db-tls` | ECDSA P-256 key and certificate | `db` | Any other service |
| `e-db-superuser-password` | 256 bits, base64url | `db` | migrate, S2 |
| `e-db-app-password` | 256 bits, base64url | `db`, `control-gateway` | migrate |
| `e-db-migrator-password` | 256 bits, base64url | `db`, `migrate` | **S2** (NFR-EHA-14) |
| `e-signing-key-1` | Ed25519 PKCS #8 PEM | `control-gateway` | — |
| `e-caller-key` | Ed25519 PKCS #8 PEM | `control-gateway` | **Every organization-level container** |
| `e-log-pseudonym-key` | 256 bits, base64url | `control-gateway` | — |
| `stack-ca-cert` | The local CA's certificate (public) | `db`, `migrate`, `control-gateway` | — |

**The one value that crosses levels** is `e-caller-public-key`. `stack:init` derives it from
`e-caller-key` as SPKI PEM. It is listed **only on `org-secrets-init`**, which copies it into
`org-gateway`'s subdirectory. It is a public key; the private half never leaves `e-secrets`.

**No E secret reaches an E2 or organization-level container, and no E2 or organization-level
secret reaches an E container** (ID §6; I1). `org-signing-key` stays organization-only: S2 gets
the verify keys by fetching them, never by file.

The PostgreSQL image's `POSTGRES_PASSWORD_FILE` holds a **path**. Role passwords are set inside
`psql` from the files (`\set … \`cat …\``), as U2's init script does, so no value is ever on a
command line or in the environment. The only environment variables on these services are
non-secret:

| Service | Environment variables |
|---|---|
| `{env}-control-gateway` | `SOORMA_PROJECT` and `SOORMA_ENVIRONMENT` (which part of `tenancy.yaml` is its own), `SOORMA_HEALTH_PORT` |
| `{env}-migrate` | `SOORMA_PROJECT`, `SOORMA_ENVIRONMENT` |
| `{env}-db` | `SOORMA_ENVIRONMENT` (the environment id, for the init script), and the PostgreSQL image's `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD_FILE` (a path) |

*Corrected in place at U4 Code Generation (2026-11-11, D-CG-EHA-23, the user's decision at the
S2 review)*: this section named only `SOORMA_ENV` and `SOORMA_HEALTH_PORT`. S2 and
`{env}-migrate` learn their environment from `SOORMA_PROJECT` and `SOORMA_ENVIRONMENT`
(D-CG-EHA-20), and the init script reads `SOORMA_ENVIRONMENT` in place of `SOORMA_ENV`, so one
set holds across Compose, the init script, and the Compose-model test's allowlist. All are
non-secret; the rule above is unchanged.

**The Compose-model test** (`deploy/test/`, run in CI) reads `docker compose config` and asserts
that:
- each service mounts only its own level's volume, at its own subpath;
- each `{env}-secrets-init` lists only `{env}-` secrets and `stack-ca-cert`;
- `org-secrets-init` lists only `org-` secrets, `stack-ca-cert`, and the `-caller-public-key`
  files;
- no service's `environment` has a value matching the secret pattern, or a name ending in
  `PASSWORD`, `KEY`, `SECRET`, or `TOKEN`, other than the `_FILE` path variables;
- each service's environment variables are within the table above (*added in place,
  D-CG-EHA-23*);
- `{env}-control-gateway` has no migrator password.

The secret-pattern check runs over the repository and each built image, as U2's CI does.

### `tenancy.yaml` (P-06)

Each environment entry gains a `controlGateway` part. It **names** secrets only:

```yaml
projects:
  - id: p1
    environments:
      - id: e
        firstAdmin: h@example.com
        controlGateway:
          edge: { port: 8443, tls: e-control-gateway-tls }
          health: { port: 8080 }
          database:
            host: env-db.e.soorma.internal
            port: 5432
            name: soorma_env
            user: soorma_env_app
            password: e-db-app-password
            ca: stack-ca-cert
          migrator: { user: soorma_env_migrator, password: e-db-migrator-password }
          keys:
            signing: e-signing-key-1
            verify: [e-signing-key-1]
            caller: e-caller-key
            logPseudonym: e-log-pseudonym-key
          organizationLevel:
            host: org-gateway.soorma.internal
            port: 9443
            ca: stack-ca-cert
```

`organizationLevel.internalCallers` becomes:

```yaml
internalCallers:
  - environment: e
    publicKeys: [e-caller-public-key]
  - environment: e2
    publicKeys: [e2-caller-public-key]
```

`packages/config`'s JSON Schema, its loader, and `listSecrets` grow to match, so `stack:init`
generates every name. **S2 reads only its own environment's part**, selected by its configured
environment id, and validates it at start-up, refusing to start on any error (BR-CFG). The
validation also requires that `verify` includes `signing`, that no name appears twice in
`verify`, and that no `controlGateway` secret is named by another environment's part.

## 4. S1's Caller Keys (Q2 A, with the user's addition)

**`internalCallers[].publicKey` becomes `publicKeys`, a non-empty list.** S1 already finds a
caller by `kid` (`KeyRing.callerByKid`, U2 P-06), so a list needs no new lookup.

**The user's addition: no `kid` may name more than one environment's key**, so `callerByKid` can
never attribute one environment's call to another (I1). S1 refuses to start (BR-CFG) on any of
these:

| Refusal | Where | Message |
|---|---|---|
| An environment listed twice | `packages/config/src/tenancy.ts` (kept from U2) | `/organizationLevel/internalCallers: environment {env} appears twice` |
| A secret name listed twice, within one environment's `publicKeys` or across two | `tenancy.ts`, over the names | `…/publicKeys/{i}: {name} is listed more than once` |
| **A key, by `kid` (RFC 7638 thumbprint), that appears twice within one environment** | Where the keys are loaded and thumbprinted (`KeyRing`'s caller loading, U2 `packages/org-identity`) | `internal caller key {kid} appears twice for environment {env}` |
| **A key, by `kid`, that appears in more than one environment** | Same | `internal caller key {kid} is configured for environments {env1} and {env2}` |

The `kid` checks are made on the loaded keys, so two different files holding the same key are
caught.

**Tests**: each refusal, including two distinct secret files that hold one key, configured for
E and E2. Also tested: E's call signed with either of E's two listed keys is attributed to E;
E2's key never is.

**Carried to Code Generation**: with S1's image rebuilt in the gate, as for A7. This lands in
U4's S1 changes, after the move commits (NP-EHA-15).

**Rotation** (in the operations notes, §10):
1. Add the new public key to E's `publicKeys`, and restart S1.
2. Switch E's `caller` to the new private key, and restart E's S2.
3. Remove the old public key, and restart S1.

There is no window where E's calls are refused.

## 5. TLS and the Local CA (P-07)

`pnpm stack:certs` adds two leaves per environment under the existing CA (ECDSA P-256, 90 days,
`serverAuth`; the CA's name constraints already permit them):

| Secret | Names |
|---|---|
| `e-control-gateway-tls` | `control-gateway.e.soorma.internal`, `localhost`, IP `127.0.0.1` |
| `e-db-tls` | `env-db.e.soorma.internal` |
| `e2-control-gateway-tls`, `e2-db-tls` | The same, with `e2` |

TLS 1.3 on S2's edge, on the store (`ssl_min_protocol_version=TLSv1.3`), from S2 to the store
(`verify-full`), and from S2 to S1 (the local CA only; the server name
`org-gateway.soorma.internal`, NP-EHA-04).

## 6. The Environment Stores (P-01, P-04; O-2, O-5, O-6)

One PostgreSQL 18.4 instance per environment, at U2's digest: `{env}-db`, aliased
`env-db.{env}.soorma.internal`, on network `{env}` only, and published nowhere. It runs with
`ssl=on`, `ssl_min_protocol_version=TLSv1.3`, `synchronous_commit=on`, and its own `hba_file`.

| File | Holds |
|---|---|
| `deploy/local/db/env-pg_hba.conf` | `local all postgres peer`; `hostssl soorma_env soorma_env_migrator,soorma_env_app` with `scram-sha-256` (IPv4 and IPv6). Nothing else |
| `deploy/local/db/env-roles.sql` | Creates `soorma_env_migrator` and `soorma_env_app` if absent (`LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS`); `REVOKE ALL ON DATABASE` from `PUBLIC`; `CONNECT` to both; schema `public`: `CREATE` revoked from `PUBLIC`, `USAGE, CREATE` to the migrator, `USAGE` to the app. Safe to run twice, as U2's |
| `deploy/local/db/init/10-soorma-env-roles.sh` | At first start, runs `env-roles.sql` and sets the two passwords from `/run/secrets/${SOORMA_ENVIRONMENT}-db-…-password` inside `psql` (*corrected in place, D-CG-EHA-23: was `SOORMA_ENV`*) |

**Role and database names are the same in every environment** (`soorma_env`,
`soorma_env_migrator`, `soorma_env_app`), because `env-store`'s migrations are shared and grant
to fixed names. **Isolation is by instance, password, certificate, and network**. No
environment's credentials or network reach another environment's store.

**Table and column privileges are in `env-store`'s `migrations/0001_init.sql`** (O-2), made by
the migrator, which owns the tables:

| Table | `soorma_env_app` has | It does not have |
|---|---|---|
| `credentials` | `SELECT`, `INSERT`, **`UPDATE (expires_at, state, ended_at, ended_by)`** | `UPDATE` of any other column; `DELETE` |
| `grants` | `SELECT`, `INSERT` | `UPDATE`, `DELETE` |
| `attribution_records` | `SELECT`, `INSERT` | `UPDATE`, `DELETE` (append-only, BR-AT-08) |
| `schema_migrations` | Nothing | Any access |

`REVOKE ALL … FROM PUBLIC` precedes each grant. U5 and U6 grant their tables the same way, in
their own migrations.

**The privilege test** (in `env-store`'s tests, against a real instance, connected as
`soorma_env_app`). Each of the following is refused with `insufficient_privilege`:
- `UPDATE credentials SET principal …`
- `UPDATE credentials SET issued_from …`
- `UPDATE credentials SET organization …`
- `DELETE FROM credentials`
- `UPDATE` and `DELETE` on `grants`, and on `attribution_records`
- `SELECT` on `schema_migrations`

`UPDATE credentials SET state …` succeeds.

**`{env}-migrate`**:
- runs `env-store`'s migrations as `soorma_env_migrator`, under the environment's advisory lock
  (NP-EHA-06), and exits;
- holds only the migrator password and the CA;
- `{env}-control-gateway` starts only after it `completed_successfully`.

## 7. Networks and Ports (P-05; O-7)

| Network | Members | Never |
|---|---|---|
| `{env}` (new) | `{env}-db`, `{env}-migrate`, `{env}-control-gateway` | Another environment's services; the organization level |
| `org-internal-{env}` (exists) | `{env}-control-gateway`, `org-gateway` (alias `org-gateway.soorma.internal`) | Another environment's S2; any store |
| none | `{env}-secrets-init` | — |

| Port | Where | Published |
|---|---|---|
| E's S2 edge, 8443 | `127.0.0.1:8442` on the host | Loopback only |
| E2's S2 edge, 8443 | `127.0.0.1:8443` on the host | Loopback only |
| S2 health, 8080 | `127.0.0.1` inside the container | Nowhere |
| Each store, 5432 | Network `{env}` | Nowhere |

S1 stays at `127.0.0.1:8441`. Nothing binds the host's `0.0.0.0`.

## 8. Hardening and Resources (P-10)

`{env}-control-gateway` and `{env}-migrate` follow shared-infrastructure.md *Hardening* exactly:
- non-root (distroless `nonroot`, 65532);
- a read-only root with a `tmpfs` `/tmp`;
- every capability dropped, and `no-new-privileges`.

`{env}-control-gateway` has `mem_limit: 256m`, since it has no Argon2id and holds at most
64 × 16 KiB of bodies. `{env}-db` is as `org-db` (999).

`{env}-secrets-init` is the documented exception, as `org-secrets-init`:
- root, `cap_drop: ALL` plus only `CHOWN`, `DAC_OVERRIDE`, `FOWNER`;
- `network_mode: none`, a read-only root, and it exits.

## 9. Monitoring (P-08; O-3)

`deploy/monitoring/alerts.yaml` adds S2's ten events to `events`:
`credential.issued`, `credential.renewed`, `credential.ended`, `credential.refused`,
`grant.made`, `grant.denied`, `first_grant.applied`, `orglevel.unavailable`,
`store.unavailable`, `throttle.refused`.

It also adds these rules:

| Rule id | Event | Group by | Threshold | Severity |
|---|---|---|---|---|
| `credential-refused-repeated` | `credential.refused` | pseudonym | 5 in 15 minutes | warning |
| `grant-denied` | `grant.denied` | pseudonym | 1 in 15 minutes | warning |
| `orglevel-unavailable` | `orglevel.unavailable` | environment | 1 in 5 minutes | critical |
| `env-store-unavailable` | `store.unavailable` | environment | 1 in 5 minutes | critical |
| `throttle-refused` | `throttle.refused` | environment | 1 in 5 minutes | warning |

`dashboard.yaml` gains a panel per S2 event, grouped by environment. The files' schemas and
their test must pass. **Nothing evaluates them in M1** (SECURITY-14, the user's decision;
NFR-EHA-20).

## 10. Operations Notes (Q3 A; O-1, P-11)

**Each service's README gains an `## Operations` section**, written at Code Generation:

| README | Section | Content |
|---|---|---|
| `services/org-gateway/README.md` | *Rotating the signing key* | (1) Add the new key as a verify key, and restart S1. (2) **Wait at least 5 minutes**, then make it the signing key and restart S1. (3) Once every token the old key signed has expired (15 minutes), remove the old verify key, and restart. **Why 5 minutes**: every environment's S2 refreshes the verify keys every 5 minutes (NFR-EHA-08). The wait covers the normal case. An S2 whose refresh failed, or ran late, fetches on an unknown `kid` (NP-EHA-03). "No valid sign-in is refused" depends on both |
| | *Internal callers* | Adding an environment's caller key, and rotating it (§4). The `kid` uniqueness rules |
| `services/control-gateway/README.md` (new) | *Rotating E's minting key* | P-11 / NP-EHA-02: add a verify key, and restart every S2 of E; make it the signing key, and restart; remove the old one after 15 minutes |
| | *Rotating E's caller key* | §4's three steps, from E's side |
| | *When the organization level is down* | What fails and what keeps working (Functional Design §16, D-EHA-23), and §11's two cases |

**A docs test** asserts that `services/org-gateway/README.md` contains "wait at least 5
minutes" in its rotation section, so the note cannot drift silently.

## 11. The S1-Stopped Demonstration (P-09, as changed; O-13)

This is scripted as `deploy/local/scripts/s1-outage.ts` and run at Build and Test. Both cases
use `docker compose stop org-gateway` and `docker compose start org-gateway`.

**Case 1: S1 stops while E's S2 is running and holds the verify keys.**

| While S1 is stopped | Expected |
|---|---|
| Issuance, renewal, `grantToHuman` | 503, `Retry-After: 5`; `orglevel.unavailable` logged |
| Ending a credential | Succeeds (no S1 call) |
| A live credential at any operation | Passes O1 to O4 (it then fails at its S1 call, if the operation has one) |
| An ended, expired, or E2 credential | Refused, exactly as with S1 running |
| **After `start org-gateway`** | **Issuance recovers as soon as S1 answers.** S2 kept its verify keys, because a failed fetch keeps the keys held (NP-EHA-03). The next request's `signInStatus` call succeeds, with no fetch needed |

**Case 2: E's S2 starts while S1 is stopped** (`stop org-gateway`, then `restart
e-control-gateway`).

| While S1 is stopped | Expected |
|---|---|
| Issuance | **503, `Retry-After: 5`**: no verify keys are loaded (BR-IS-02; NP-EHA-03, `unknownKey` with no keys held) |
| A credential issued **before the restart** | **Still passes O1 to O4**, because E's own key ring comes from configuration (NP-EHA-02), and **it can be ended** |
| **After `start org-gateway`** | **Issuance recovers on the next fetch**: the scheduled refresh, or the on-demand fetch an issuance triggers, subject to the 30-second limit |

## 12. CI

As U2's (shared-infrastructure.md *CI*), extended:
- `env-store`'s, P4's, P5's, and P7's tests against a PostgreSQL service container, including
  the privilege test (§6) and NFR Design's concurrency tests;
- the S2 image built, and the secret-pattern check over it;
- the Compose-model test (§3);
- the configuration tests for S1's caller-key refusals (§4);
- the stack smoke test extended: sign in at S1, then issue, renew, and end a credential at E's
  S2, and grant at E. An E credential is refused at E2.

## 13. Shared Infrastructure Updated

[shared-infrastructure.md](../../shared-infrastructure.md) gains what U4 settles for U5 to U7:
- the Compose structure (Q1 A);
- the environment store and its role names;
- privileges in migrations;
- per-environment secrets naming and the one cross-level value;
- caller-key uniqueness;
- the `{env}` network and the port plan;
- each service's operations notes.

Each change is marked as U4's.

## 14. Obligations Discharged

| # | Obligation | Discharged in |
|---|---|---|
| O-1 | S1's rotation note: "wait at least 5 minutes" | §10, with its docs test |
| O-2 | Column-level privileges | §6, with the privilege test |
| O-3 | Alert rules | §9 |
| O-4 | Secrets as mounted files only, never in environment variables, source, or IaC | §3, with the Compose-model test |
| O-5 | One PostgreSQL 18 instance per environment | §6 |
| O-6 | `e-migrate`, `e2-migrate` | §6 |
| O-7 | `org-internal-{env}` | §7 |
| O-8 | Secrets volume and init container per environment | §3, §8 |
| O-9 | E's caller key pair; the public half at S1 | §3, §4 |
| O-10 | E's minting, verify, and log-pseudonym keys | §3 |
| O-11 | `tenancy.yaml` additions, validated | §3 |
| O-12 | Certificates | §5 |
| O-13 | The S1-stopped demonstration | §11 |

## 15. Carried Forward

| To | Item |
|---|---|
| **Code Generation (U4)** | After the two move commits (NP-EHA-15): **S1's caller keys (§4: `publicKeys`, the four refusals, their tests)** and **A7**, each with S1's image rebuilt in the gate. Then everything in §1 to §12. The S1 README's Operations section (§10) |
| **Build and Test** | §11's two cases; the Compose-model, privilege, and docs tests; the performance figures (NFR-EHA-15); the residuals and the user's SECURITY decisions (NFR Requirements §4) |
| **First hosted deployment** | As shared-infrastructure.md lists, plus per-principal and per-source limits on S2 (NFR-EHA-06) |

---

## 16. Security Compliance at Infrastructure Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit; **at rest not applicable in M1, by the user's decision** | TLS 1.3 everywhere, `verify-full` (§5, §6) |
| SECURITY-02 | N/A | No load balancer or API gateway in M1 (access logging at a fronting gateway is carried to the first hosted deployment) |
| SECURITY-03 | Compliant, **except the centralized log service: not applicable in M1, by the user's decision** | JSON to stdout; E's own log-pseudonym key (§3) |
| SECURITY-04 | N/A | No HTML |
| SECURITY-05 | Compliant | Unchanged from NFR Design |
| SECURITY-06 | Compliant | Least privilege: the app role's column-level `UPDATE`, no `DELETE` (§6); each service mounts only its own secrets (§3) |
| SECURITY-07 | Compliant | Loopback-only edges; the store on its environment's network only; `org-internal-{env}` holds two services; no network spans environments (§7) |
| SECURITY-08 | Compliant | Unchanged |
| SECURITY-09 | Compliant | Hardened containers; no default credentials; images pinned by digest; no unauthenticated endpoint but loopback health (§2, §8) |
| SECURITY-10 | Compliant | No new dependency; images pinned |
| SECURITY-11 | Compliant | Unchanged (NFR-EHA-04 to 06, with the user's instance-flood residual) |
| SECURITY-12 | Compliant | **Secrets as mounted files only** (§3, O-4); every key generated per environment; rotation for each key documented (§4, §10) |
| SECURITY-13 | Compliant | Checksummed migrations; images by digest; the secret check over images |
| SECURITY-14 | **Not applicable in M1, by the user's decision** | Rules and the dashboard as files (§9) |
| SECURITY-15 | Compliant | S2 starts and serves without S1, failing closed per operation (§11) |

**Security findings**: none blocking.

## 17. Invariant Compliance at Infrastructure Design

| Code | Status | Note |
|---|---|---|
| I1 | Covered | Per environment: a store, secrets, keys, a network, and certificates. No secret crosses environments. **No `kid` may name two environments' caller keys** (§4) |
| I2, I4 to I7, I9 | No change | |
| I3 | Covered | S1 trusts S2 by its signed request, and S2 trusts S1 by its certificate. No network membership or address is an identity input |
| I8 | Covered | Everything in soorma-core, `deploy/` under FSL-1.1-ALv2 |
| I10 | Covered | Nothing reads a host, container, or network name for scope; tenancy is configured (P9) |
| I11 | N/A | Construction is where technology is selected |

**Invariant findings**: none blocking.
