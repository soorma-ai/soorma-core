# Logical Components: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7)
**Companion**: [nfr-design-patterns.md](nfr-design-patterns.md) (NP-EHA-01 to 15)
**Decisions from**: the NFR Design plan, Q1 to Q4 and P-01 to P-10 (answered
2026-11-11T06:27:05Z)

Delivery is Infrastructure Design's: containers, secrets, certificates, networks, and the
values in `tenancy.yaml`. This document names the logical parts and what each holds.

---

## 1. The S2 Process

`services/control-gateway` is one Node process per S2 instance, and stateless (M1-TECH-03).

| Part | Holds | Pattern |
|---|---|---|
| Edge listener (NestJS on Fastify, TLS 1.3) | The four operations; the request semaphore in `onRequest` | NP-EHA-05, 12 |
| Health listener (`127.0.0.1`, plain HTTP) | `GET /` → 204 | NP-EHA-12 |
| E's key ring | Signing key and verify keys, as `KeyObject`s, from configuration | NP-EHA-02 |
| Verify-key cache | S1's verify keys; the 5-minute schedule; the on-demand limiter | NP-EHA-03 |
| S1 caller | The S1-call pool (8 sockets), the key-fetch pool (1 socket), E's caller key | NP-EHA-04 |
| Semaphores | Request (64, 1 s) and S1 call (8, 1 s) | NP-EHA-05 |
| Env-store pool | Connections as the app role | NP-EHA-06 |
| Security log | S2's event list; E's log-pseudonym key | NP-EHA-12 |

**Start-up order**:
1. Load E's configuration and secrets (P9).
2. Build the key ring (NP-EHA-02).
3. Open the store pool.
4. Apply the first grant (NP-EHA-08).
5. Start the verify-key cache, without blocking (NP-EHA-03).
6. Listen.

A failure in any of steps 1 to 4 stops start-up (D-EHA-28). `{env}-migrate` has already
completed successfully before S2 starts (NFR-EHA-14).

**Per request** (Functional Design §11's check order):
1. Take a request permit.
2. Bound the body.
3. Classify the presenter (P1).
4. Verify the token (P5 or the sign-in verifier).
5. Check O3, and call `signInStatus` where the operation needs it (S1 caller, S1 permit).
   At issuance, P1 makes that one call and returns its `expiresAt` for the cap. It is never
   called twice in a request.
6. Check the contract version and body.
7. Check authority (P3 over P11 and P4's `GrantSource`).
8. Write, in one `withTransaction` (P4, P5, P7).
9. Respond, then release the permit once.

## 2. Packages

### New

| Package | Component | Holds | Depends on |
|---|---|---|---|
| `packages/service-kit` | **New: shared, organization-neutral runtime** (Q2 A) | §2.1's moved items; after the generalisation commit, `Semaphore`, `SecurityLog`, the contract validator, and the HTTP plumbing | `jose`, `pg`, `@nestjs/*`, `@soorma/jcs`, `@soorma/contract`. **No `@soorma/*` module above it**: P1 depends on service-kit, never the reverse |
| `packages/env-store` | **New: the environment store** (Q4 A) | The migration directory (`migrations/0001_init.sql`, …), the pool, `withTransaction` / `Tx`, the lock key | `service-kit` (runner, pool settings, `statement()`), `pg` |
| `packages/registry` | P4 | Grants, `heldSet` as P11's human `GrantSource`, `holdsAnyGrant`'s read, `isAcceptedIdentifier`, `createGrant`; its `src/sql.ts` | `env-store` (`Tx`), `service-kit`, `@soorma/policy-decision-seam` (the port type), `@soorma/authority` (the human-only class, BR-ACC) |
| `packages/credentials` | P5 | `mint`, `verify` (NP-EHA-01), `markEnded`, conditional renewal (NP-EHA-09), E's key ring (NP-EHA-02); its `src/sql.ts` | `env-store`, `service-kit`, `jose` |
| `packages/attribution` | P7 | `record`: the writer's BR-AT-05 checks, then one insert; its `src/sql.ts` | `env-store`, `service-kit` |
| `services/control-gateway` | S2 | Listeners, handlers, the verify-key cache, the S1 caller, the semaphores, start-up; `src/migrate.ts` for `{env}-migrate` | All of the above, `@soorma/perimeter`, `@soorma/authority`, `@soorma/policy-decision`, `@soorma/config`. **Never `@soorma/org-identity`** |

U5 and U6 extend P4 and P5. U7 extends P7's callers. None of them adds another store package.

### Reused, unchanged in role

| Package | U4's use |
|---|---|
| `@soorma/perimeter` (P1) | Presenter classification by prefix (BR-PR). **Its runtime dependency on `@soorma/org-identity` is removed in commit 2** (§2.1), so S2 links P1 without P10 |
| `@soorma/authority` (P3) | `evaluateHuman` and `holdsAnyGrant` over the seam (D-EHA-13); the human-only class |
| `@soorma/policy-decision` (P11) | `grantedSet` through the `GrantSource` port, which P4 fills; `contains` |
| `@soorma/config` (P9) | Loads E's part of `tenancy.yaml` (items in §4) |

### 2.1 The Move (NP-EHA-15)

**Commit 1, a pure move.** Files and exports move, and imports are updated. Organization-level
defaults stay in `@soorma/org-identity` and are passed in. U2's tests stay green, and S1's image
is rebuilt.

| Item | From | To |
|---|---|---|
| `SecretBytes`, `SecretText`, `Verifier`, `TotpCode`, the `as…` helpers, `secretEqual` | `org-identity/src/crypto/secret-types.ts` | `service-kit/src/crypto/secret-types.ts` |
| `canonicalJson`, `referenceJson`, `PrincipalReference` | `org-identity/src/crypto/canonical.ts` | `service-kit/src/crypto/canonical.ts` |
| `pseudonym`, `HumanPseudonym` | `org-identity/src/crypto/pseudonym.ts` | `service-kit/src/crypto/pseudonym.ts` |
| `signInternalRequest`, `verifyInternalRequest`, `bodyHash`, `internalAudience`, their constants | `org-identity/src/crypto/internal-request.ts` | `service-kit/src/crypto/internal-request.ts` |
| **Sign-in verification**: `verifySignIn`, `SIGN_IN_PREFIX`, `SIGN_IN_TYP`, `issuerOf`, `SignInClaims`, `VerifyResult`, `MaterialClass`. **`mintSignIn` and `MintInput` stay in org-identity**, importing these | `org-identity/src/crypto/sign-in-token.ts` | `service-kit/src/crypto/sign-in-verify.ts` |
| `thumbprint`, `PublicJwk`, `VerifyKey`, `CallerKey`. **`KeyRing` stays** (it holds S1's seed keys, counter secret, and callers) | `org-identity/src/crypto/key-ring.ts` | `service-kit/src/crypto/keys.ts` |
| `CLOCK`, `systemClock`, `Clock`. **`Lifetimes` stays** | `org-identity/src/clock.ts` | `service-kit/src/clock.ts` |
| `UnavailableError`, `KeyMaterialError` | `org-identity/src/errors.ts` | `service-kit/src/errors.ts` |
| `Statement`, `statement`, `migrationStatement`, and the runner's own statements. **S1's statements stay** in org-identity's `src/sql.ts` | `org-identity/src/sql.ts` | `service-kit/src/sql.ts` |
| The migration runner (`migrate`, `runMigrations`, `MigrationError`). It takes `dir` **and `lockKey`**; `MIGRATIONS_DIR` and `MIGRATION_LOCK_KEY` stay in org-identity, which passes them | `org-identity/src/store/migrations.ts` | **`service-kit/src/store/migrations.ts`** (the path U2's `isMigrationRunner` matches) |
| `poolConfig`, `ConnectionSettings`, **and `Store`, `Queryable`, `ConflictError`** (*consistency fix at U4 Code Generation, D-CG-EHA-01: the class that wraps the pool moves with it; `Store.transaction` is `env-store`'s `withTransaction`, and `Queryable` its `Tx`. Its error text takes the store's name, which S1 passes as `org`*) | `org-identity/src/store/store.ts` | `service-kit/src/store/store.ts` (*as built: one file, moved whole; was `store/pool.ts`*) |
| **Problem documents**: `CONTRACT_VERSION`, `SUPPORTED_VERSIONS`, `ProblemCode`, `PROBLEM_TABLE`, `isProblemCode`, `FieldError`, `Refusal`, `ProblemError`, `problemBody`, `problemResponse`. The module has no imports. Moving it keeps service-kit's HTTP plumbing from depending on P1, which would be a cycle | `perimeter/src/problems.ts` | `service-kit/src/http/problems.ts` |
| `createHealthServer`, `listenHealth`, `HEALTH_HOST`; the healthcheck script | `services/org-gateway/src/health.ts`, `healthcheck.ts` | `service-kit/src/http/health.ts`, `healthcheck.ts` |

*Corrected in place at U4 Code Generation (2026-11-11, D-CG-EHA-01)*: the `poolConfig` row
above gained `Store`, `Queryable`, and `ConflictError`, and the target path `store/store.ts`.

*Found while writing this stage*: `@soorma/perimeter` has a runtime dependency on `@soorma/org-identity`. It imports `SIGN_IN_PREFIX`, `verifySignIn`, and `Clock`, which move in commit 1, and the type `KeyRing`, which is fixed in commit 2. Without the fix, S2 would link P10 through P1.

**Commit 2, the generalisations.** U2's tests stay green, and S1's image is rebuilt.

| Item | Change |
|---|---|
| `HashSemaphore` | A generic `Semaphore` (permits, wait deadline, clock, FIFO, waiter removal on abort, release-once) moves to `service-kit/src/semaphore.ts`. `HashSemaphore`, `HASH_MEMORY_MIB`, `HASH_WAIT_MS`, and `defaultPermits` stay in org-identity, over it |
| `SecurityLog` | Moves to `service-kit/src/http/security-log.ts`, typed by its service's event list. S1's `SECURITY_EVENTS` stays in S1 |
| `ContractValidator` | Moves to `service-kit/src/http/contract-validator.ts`, taking its service's OpenAPI document. S1 passes `org-gateway.openapi.yaml` |
| `createAdapter`, `BODY_LIMIT`, `sendProblem`, `rawBody`, `ProblemFilter` | Move to `service-kit/src/http/http.ts`, after `SecurityLog`, which `ProblemFilter` uses |
| **`verifySignIn`: leeway** (`service-kit/src/crypto/sign-in-verify.ts`) | Takes `{ expSeconds, iatAheadSeconds? }` instead of the hard-coded `clockTolerance: 0`. `iatAheadSeconds` adds an explicit check that `iat` is at most that far ahead. **S1 passes `{ expSeconds: 0 }`** (no `iat` check, as today). **S2 passes `{ expSeconds: 30, iatAheadSeconds: 30 }`** (NFR-EHA-03) |
| **`verifySignIn`: unknown `kid`** | `VerifyResult` gains `{ status: 'unknownKey' }` for a `kid` absent from the key source. Today `JWKSNoMatchingKey` collapses into `invalid`. A missing `kid` stays `invalid`. **S1's P1 maps it to `credential_refused`**, as today. S2's P1 refetches, then verifies once more (NP-EHA-03) |
| **P1's `SignInPerimeter`: key source** (`perimeter/src/presenter.ts`) | Takes a structural **`SignInKeySource { verifyKey(kid), hasKeys() }`**, **read on every verification**, instead of `KeyRing`. S1 passes its `KeyRing`, which gains `hasKeys()`. S2 passes the verify-key cache. **`@soorma/org-identity` leaves perimeter's `dependencies`**, and stays only in its `devDependencies`, for the test fixtures that mint sign-ins |
| **P1's `SignInPerimeter`: refetch** | An optional `refetch()`. On `unknownKey`, if present, P1 awaits it and verifies **exactly once more**. If the second answer is `unknownKey` and `hasKeys()` is false, the result is `unavailable`. S1 passes none, so its behaviour is unchanged |
| **P1's `SignInPerimeter`: status callback** | `isLive(claims) → boolean` becomes **`status(claims) → SignInStatus`** (A7's type). Only `live` is accepted, and the accepted result carries `expiresAt`. **S1's callback keeps its meaning**: its O3 check from its own record, answering `live` or `ended`. **S2's is its one `signInStatus` call per request**, and `expiresAt` is kept for the cap (BR-EC-04) |

`clock.module.ts`, `apps.ts`, `runtime.ts`, `main.ts`, `migrate.ts`, and everything under `edge/`
and `internal/` stay in S1.

## 3. The Environment Store

PostgreSQL 18, **one instance per environment** (`env-db-e`, `env-db-e2`; NFR-EHA-09). It has
two roles:
- The **migrator role** owns the schema.
- The **app role** has only the privileges listed below.

Every table carries `organization`, `project`, `environment` (`text NOT NULL`), and every
statement constrains on them (D-EHA-29).

### `credentials`

| Column | Type | Rule |
|---|---|---|
| `id` | `text` PK | NP-EHA-11 |
| `organization`, `project`, `environment` | `text NOT NULL` | E |
| `principal` | `text NOT NULL` | The subject (its organization is `organization`) |
| `issued_from` | `text NOT NULL` | The sign-in's `sid` |
| `issued_at`, `expires_at` | `timestamptz NOT NULL` | `CHECK (expires_at > issued_at)` |
| `state` | `text NOT NULL` | `CHECK (state IN ('live', 'ended'))` |
| `ended_at` | `timestamptz` | |
| `ended_by` | `text` | `CHECK (ended_by IN ('self'))` |

- **A further `CHECK`**: `(state = 'ended') = (ended_at IS NOT NULL AND ended_by IS NOT NULL)`.
- **App role**: `SELECT`, `INSERT`, and **`UPDATE` on `expires_at`, `state`, `ended_at`,
  `ended_by` only**. No `DELETE` (NFR-EHA-21).

### `grants`

| Column | Type | Rule |
|---|---|---|
| `id` | `text` PK | NP-EHA-11 |
| `organization`, `project`, `environment` | `text NOT NULL` | E |
| `principal` | `text NOT NULL` | The target |
| `permissions` | `text[] NOT NULL` | `CHECK (cardinality(permissions) > 0)`. Sorted and de-duplicated by P4 (NP-EHA-10) |
| `granted_by_kind` | `text NOT NULL` | `CHECK (granted_by_kind IN ('principal', 'configuration'))` |
| `granted_by_principal`, `granted_by_credential` | `text` | Both present exactly when `granted_by_kind = 'principal'` |
| `self_grant` | `boolean NOT NULL` | `CHECK` that it is `false` for a configuration grant, and equals `granted_by_principal = principal` otherwise |
| `granted_at` | `timestamptz NOT NULL` | |

- **Indexes**: `grants_by_principal` on `(organization, project, environment, principal)`.
- **`grants_one_configuration_grant`**: a **unique** index on the same columns
  `WHERE granted_by_kind = 'configuration'` (NP-EHA-08).
- **App role**: `SELECT`, `INSERT`. No `UPDATE` or `DELETE` (M1 removes no grant).

### `attribution_records` (Q3 A; NP-EHA-07)

| Column | Type | Present for |
|---|---|---|
| `id` | `text` PK | All |
| `recorded_at` | `timestamptz NOT NULL` | All |
| `request_id` | `text` | Requests; null for the configured first grant (no request) |
| `organization`, `project`, `environment` | `text NOT NULL` | All: the scope (BR-AT-06) |
| `operation` | `text NOT NULL` | All (`issueEnvironmentCredential`, `renewEnvironmentCredential`, `endEnvironmentCredential`, `grantToHuman`, `configureFirstGrant`; U5 to U7 add theirs) |
| `actor_kind` | `text NOT NULL` | All: `human`, `configuration`, `agent` |
| `principal` | `text` | Human |
| `credential_kind`, `credential_id` | `text` | Human (`signIn`, `environmentCredential`); agent where presented (U6, U7) |
| `registration`, `instance`, `sponsor` | `text` | Agent (U6, U7) |
| `target_kind`, `target_id` | `text` | Where the operation has a target (a credential, a grant, a registration) |
| `self_grant` | `boolean NOT NULL DEFAULT false` | `grantToHuman` |
| `chain` | `jsonb` | Agent with an envelope (U7) |
| `origin` | `jsonb` | Agent with an envelope: `{ originMode, delegatingPrincipal? }` as stamped (U3) |
| `rebroadening_load_bearing` | `boolean` | Agent with an envelope |
| `rebroadening_hop` | `integer` | Exactly when load-bearing |

- **The `CHECK` constraints**: NP-EHA-07's table, one named constraint per row.
- **No index beyond the primary key**: there is no read surface in M1.
- **App role**: `SELECT`, `INSERT`. No `UPDATE` or `DELETE` (BR-AT-08).

### `schema_migrations`

The runner's own table, as U2's: version, checksum, applied at. It belongs to the migrator role,
and the app role has no privilege on it.

## 4. Configuration Items (E's part)

These are the logical names. Infrastructure Design delivers each and adds them to `tenancy.yaml`.
**Each secret is per environment. Nothing is shared between E and E2.**

| Item | Kind | Used by |
|---|---|---|
| E's identity: `organization`, `project`, `environment` | Value (exists) | NP-EHA-01, 06 |
| E's first Admin | Value (exists) | NP-EHA-08 |
| Edge port, TLS key and certificate | Value, secret | NP-EHA-12 |
| Health port | Value | NP-EHA-12 |
| Store: host, port, database, app user, app password, CA | Values, secret | NP-EHA-06 |
| Migrator: user, password | Value, secret (only `{env}-migrate` mounts it) | NFR-EHA-14 |
| E's signing key, E's verify keys | Secrets (Ed25519 PKCS #8 PEM) | NP-EHA-02 |
| E's caller key (private half); its public half in S1's `internalCallers` | Secret; S1 configuration | NP-EHA-04 |
| E's log-pseudonym key (at least 256 bits) | Secret | NP-EHA-12 |
| The organization level's internal endpoint: `org-gateway.soorma.internal`, port | Value | NP-EHA-04 |
| The local CA certificate | Secret file | NP-EHA-04, 06 |

## 5. S1's Internal Interface, as S2 Calls It

| Call | Path | Answer S2 accepts | Pool | Throttle |
|---|---|---|---|---|
| `verifyOnlyMaterial` | `GET /verify-keys` | A JWKS of Ed25519 public keys | Key-fetch (1) | None |
| `principalExists` | `GET /principals/exists?organization={o}&principal={p}` | `{ exists: boolean }` | S1-call (8) | S1 permit |
| `signInStatus` | `GET /sign-ins/{sid}/status` | **A7**: `{ status: 'live', expiresAt }`, `{ status: 'ended' }`, or `{ status: 'unknown' }` | S1-call (8) | S1 permit |

Every call is signed (U2 P-06), and every answer is checked to exactly this shape (NP-EHA-04).
**A7 changes S1's `signInStatus` answer** from `{ status }` to the shape above. That change is
applied at U4's Code Generation, with S1's image rebuilt in the gate (Functional Design §17).

## 6. Test Doubles

| Double | Stands for | Used by |
|---|---|---|
| Stub S1 | S1's internal listener, over TLS under a test CA; answers and delays scripted per test; it can check the signature | NP-EHA-03, 04 tests |
| Injected clock and scheduler | Time | Every clock test (NP-EHA-13) |
| Test environment stores | One PostgreSQL 18 database per test environment, migrated by the real runner | NP-EHA-06 to 10 |
| A second environment's key ring | E2 | NP-EHA-01, 02 cross-environment tests |

The **concurrency tests** use the real store, without a double: the two start-ups (NP-EHA-08),
renewal against end (NP-EHA-09), and the 64 aborted requests (NP-EHA-05).

## 7. Forward Obligations

Posted on each unit's issue when this stage is approved.

| To | Obligation |
|---|---|
| **U4 Infrastructure Design** | Deliver §4's items for E and E2:<br>• `env-db-e` and `env-db-e2`, with roles and the column-level privileges of §3;<br>• `e-migrate` and `e2-migrate`;<br>• each environment's secrets volume and init container;<br>• `org-internal-{env}`;<br>• certificates under the local CA;<br>• E's caller public key in S1's `internalCallers`;<br>• the alert rules in `deploy/monitoring/alerts.yaml` (NFR-EHA-19).<br>**S1's rotation steps in the operations notes say "wait at least 5 minutes"** at step 2 (NFR-EHA-08) |
| **U4 Code Generation** | **Commit 1 is the pure move, and commit 2 the generalisations, each with U2's tests green and S1's image rebuilt, before any U4 code** (NP-EHA-15). Then A7 in S1; then U4's packages and S2. `check:code` covers the new packages, with the runner at `src/store/migrations.ts` |
| **U5 (soorma-core#8)** | Registrations and secrets join `env-store`'s **one migration sequence** (D-EHA-29's three columns on every table). P4's writes take the caller's `Tx`. `registerAgent` and `issueRegistrationSecret` write attribution records through P7 (human actor) |
| **U6 (soorma-core#9)** | Agent credentials extend P5 and `credentials` (or a sibling table) in the same sequence. Agent attribution records fill `registration`, `instance`, and `sponsor`, and no envelope columns. NP-EHA-01's token shape is a working pattern for `soorma_ac_` (Functional Design is U6's) |
| **U7 (soorma-core#10)** | Publish and subscribe records fill `chain`, `origin`, `rebroadening_load_bearing`, and `rebroadening_hop` from U3's result. The `CHECK` constraints refuse an inconsistent one |
