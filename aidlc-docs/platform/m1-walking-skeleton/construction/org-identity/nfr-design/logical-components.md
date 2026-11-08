# Logical Components: U2 `org-identity`

**Unit**: U2 `org-identity` (soorma-core#5). Control face, organization level
**Patterns**: [nfr-design-patterns.md](nfr-design-patterns.md) (P-01 to P-17)
**Layout**: the approved Application Design (unit-of-work.md, *Code Organization*). Module
names P1 to P11 are Application Design's

---

## 1. The S1 Process

```text
+-------------------------------------------------------------------+
| org-gateway process (stateless; any number of instances)          |
|                                                                   |
|  Edge listener (contract)        Internal listener (not published)|
|  NestJS app + Fastify            NestJS app + Fastify             |
|  5 operations                    3 operations, signed requests    |
|      |                                |                           |
|      +--------------+-----------------+                           |
|                     v                                             |
|  Shared modules: org-identity (P10), identity-resolution (P6),    |
|  abuse-bound (P8), config (P9), perimeter (P1, sign-in checks),   |
|  key ring, token service, TOTP, secret policy, hash semaphore,    |
|  clock, logger                                                    |
|                     |                                             |
|  Workers: Failed Attempt writer; daily pruner                     |
+---------------------|---------------------------------------------+
                      v
             org store (PostgreSQL 18)
```

The edge and internal listeners are **two NestJS applications in one process** (P-07). They
share module instances, never routes. A **third, health listener** is bound to `127.0.0.1`
inside the container only (P-07, amended at Infrastructure Design). **Migrations run in a
separate one-shot service, `org-migrate`**, before S1 starts (NFR-OI-18, amended).

## 2. Components

| Component | Package | Responsibility | Patterns |
|---|---|---|---|
| **Edge app** | `services/org-gateway` | `firstAuthenticate`, `authenticate`, `renewSignIn`, `endSignIn`, `changeMaterial`; the check order (business-logic-model §1); its exception filter | P-07, P-08 |
| **Internal app** | `services/org-gateway` | `verifyOnlyMaterial`, `principalExists`, `signInStatus`; the signed-request guard; its own exception filter | P-06, P-07 |
| **Signed-request guard** | `services/org-gateway` | Verifies the internal JWS: key → environment, `typ`, `aud`, times, and `htm`, `tgt`, `bsh` against the raw request | P-06 |
| **Perimeter, sign-in checks** (P1) | `packages/perimeter` | Presenter classification at S1: no credential on the three unauthenticated operations (D-OI-26); exactly one `soorma_si_` on the two sign-in operations; O1 to O3 | P-01; BR-RF-06 |
| **Org identity** (P10) | `packages/org-identity` | Principals, material, pending P enrollments, sign-ins; every state change in one transaction; `ensureFirstAdmin` | P-12, P-13 |
| **Identity resolution, human half** (P6) | `packages/identity-resolution`, behind `seams/identity-resolution` | Verifies K, P, and enrollment material against a principal; returns a reference or a rejection; decoy when absent | P-09, P-10; BR-SEAM |
| **Abuse bound** (P8) | `packages/abuse-bound` | `admit`, `settleFailure`, `settleSuccess` over the slot table; `Retry-After` | P-04, P-05 |
| **Config** (P9, organization half) | `packages/config` | Loads and validates the organization's part; refuses to start on any error | P-02; BR-CFG |
| **Key ring** | `packages/org-identity` | Holds the signing key, verify keys (JWKS), seed keys, counter secret, log-pseudonym key, environment caller keys, from config | P-02 |
| **Token service** | `packages/org-identity` | Mints and verifies sign-in tokens (`jose`, `Ed25519`) | P-01 |
| **TOTP** | `packages/org-identity` | RFC 6238 generation and checking; the seed cipher | P-03, P-12 |
| **Secret policy** | `packages/org-identity` | NFKC, length, control characters, the breached list (loaded once and digest-checked), context words, `reused` | BR-K |
| **Hash semaphore** | `packages/org-identity` | Bounds concurrent Argon2id work | P-09 |
| **Clock** | `packages/org-identity` (a token other packages can use) | Time | P-14 |
| **Logger** | `services/org-gateway` | JSON lines; the fixed event list; no parameter for secrets or identifiers; humans named by log pseudonym only | P-17 |
| **Failed Attempt writer** | `packages/abuse-bound` | The bounded queue and batched inserts | P-11 |
| **Pruner** | `packages/org-identity` | Daily retention, under an advisory lock | P-16 |
| **Store access** | `packages/org-identity`, `packages/abuse-bound` | `pg` Pool as the app role, parameterized SQL. Migrations: the one-shot `org-migrate` runner, as the migrator role, under an advisory lock | P-15 |

Every injected dependency uses an **explicit token** (T-OI-08). Each NestJS package compiles
to JavaScript through its own `tsconfig.build.json` (T-OI-09).

## 3. The Org Store

Logical tables. Column types, indexes, and the migration files are Code Generation's. Every
table is organization-scoped, so the organization is in every key (ID §6).

| Table | Key | Holds | Pruned |
|---|---|---|---|
| `principals` | (organization, principal) | state, registered-at and -by, activated-at | **Never** |
| `materials` | id; (organization, principal, class) where state is not `retired` is unique | class, state, enrolled-at and -by, established-at and -by, retired-at, the verifier (Argon2id PHC string for K; the encrypted seed and the last accepted step for P) | **Never**; the verifier is set to null on retirement |
| `pending_second_factors` | (organization, principal) | id, type, encrypted setup state, expires-at | On confirmation, replacement, material change, or expiry |
| `sign_ins` | id | subject, authenticated-at, classes, expires-at, state, ended-at, ended-by | 90 days after ending or expiry |
| `failed_attempts` | id | principal, surface, at, refused-by-bound | 90 days |
| `attempt_slots` | slot (0 to 2^20 − 1) | window entries (id, at), consecutive failures, next-allowed-at | Never; at most 2^20 rows by construction |
| `schema_migrations` | version | checksum, applied-at | Never |

**Secrets in the store**: the K verifiers (one-way, so not recoverable) and the TOTP seeds
(AES-256-GCM, P-03). **No key material**, no plaintext secret, and no token is stored.

## 4. Configuration Items (organization part)

Logical items. Their format and delivery are Infrastructure Design's (M1-TECH-06).

| Item | Kind | Notes |
|---|---|---|
| Organization identifier | value | Never inferred (BR-CFG-01) |
| Projects, environments, and membership; each environment's first Admin identifier | value | The tenancy tree (D-OI-12) |
| Second-factor required | boolean | BR-CFG-06 |
| Enrollment material, per first Admin identifier | **secret** | Organization part only (BR-CFG-02); used only when the principal does not exist (BR-CFG-04) |
| Signing key; verify keys | **secret**; public | P-02 |
| Seed-encryption keys (current, and older ones still in use) | **secret** | P-02, R-3 |
| Counter secret | **secret** | Rotated only deliberately (R-2) |
| Log-pseudonym key | **secret** | Separate from the counter secret (NFR-OI-22, amended) |
| Environment caller public keys, per environment | public | P-06 |
| Store connection (app role only; the migrator credential goes to `org-migrate`, never to S1) | **secret** | P-15; D-ID-OI-02 |
| Edge and internal listener addresses and TLS material | value; **secret** | Infrastructure Design |
| Hash memory budget (default 512 MiB); permit override | value | P-09 |

## 5. The Internal Interface

| Operation | Method and target | Response |
|---|---|---|
| `verifyOnlyMaterial` | `GET /verify-keys` | A JWKS of the verify keys (public only) |
| `principalExists` | `GET /principals/exists?organization={o}&principal={p}` (encoded) | `{ exists: true \| false }` |
| `signInStatus` | `GET /sign-ins/{id}/status` | `{ status: "live" \| "ended" \| "unknown" }` |

Each call carries the signed request of P-06 in `Authorization: Bearer`. Any failure is a
refusal with no detail, logged as `internal.call_refused`. The interface is not in the
published contract, and its shapes may change with U4 without a contract version change.
