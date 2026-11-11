# Tech Stack Decisions: U4 `env-human-access`

**Unit**: U4 `env-human-access` (soorma-core#7)
**Scope**: U4's selections. U1's toolchain (T-01 to T-16), U2's runtime selections (T-OI-01
to 12), and U3's (T-AE-01 to 06) apply unchanged
**Dependencies**: **U4 adds none** (P-08). `services/control-gateway` takes the same
dependencies, at the same pinned versions, as `services/org-gateway`: its register rows gain
that workspace at Code Generation

---

## Decisions

| ID | Selection | Choice | Version | Licence | Kind | Why | Source |
|---|---|---|---|---|---|---|---|
| T-EHA-01 | Framework | **NestJS 12 on Fastify 5**, as S1 (U2 T-OI-01, 02, 08, 09) | 12.3.2; `fastify` 5.12.7 | MIT | Runtime | One framework across the control face | P-08 |
| T-EHA-02 | Tokens | **`jose`**, JWS with `Ed25519` only (RFC 9864), fixed in code: E mints and verifies its own credentials, and verifies sign-ins with S1's verify keys. The credential's claims and framing are NFR Design's | 6.2.14 (in the register) | MIT | Runtime | U2 T-OI-03 | P-08 |
| T-EHA-03 | Calls to S1 | **`node:https`** with the local CA and server-name checking; a 2-second timeout; no retry (NFR-EHA-07) | Node 26.13.0 (U1 T-01) | — | Runtime, built in | No HTTP client library is needed for two signed calls and a key fetch | P-03; P-08 |
| T-EHA-04 | Cryptography | **`node:crypto`**: random ids (at least 128 bits), HMAC-SHA-256 for log pseudonyms, Ed25519 keys, `timingSafeEqual` | Node 26.13.0 | — | Runtime, built in | U2 T-OI-04 | P-08 |
| T-EHA-05 | Datastore | **PostgreSQL 18, one instance per environment** (`env-db-e`, `env-db-e2`), each with its own roles, credentials, and certificate | 18.4, the image U2 pinned by digest (`deploy/local/compose.yaml`) | PostgreSQL Licence | Server | I1; one engine across the stack | Q3 A |
| T-EHA-06 | Database access | **`pg`**, plain parameterized SQL, no ORM; the in-house migration runner, as a one-shot `{env}-migrate` service | 8.23.1 (in the register) | MIT | Runtime | U2 T-OI-07; NFR-EHA-13, 14 | P-01 |
| T-EHA-07 | Validation | **Ajv 8**, the contract's validators compiled once at start-up | 8.20.0 (in the register) | MIT | Runtime | U1 T-05; U3 T-AE-02 | P-02 |
| T-EHA-08 | Throttling | **In-house**: two counting semaphores per instance (64 requests, 8 S1 calls) with a 1-second wait, over an injected clock | — | — | — | A few dozen lines, as U2's hashing semaphore (NFR-OI-20); a rate-limiting plugin would add a dependency and per-key state that M1 does not use | Q2 A |
| T-EHA-09 | Logging | **NestJS's `ConsoleLogger` in JSON mode**, to stdout | 12.3.2 | MIT | Runtime | U2 T-OI-11 | P-06 |
| T-EHA-10 | Monitoring definitions | **Alert rules added to `deploy/monitoring/alerts.yaml`**, in U2's file format. No monitoring service runs in M1 | — | — | Configuration | SECURITY-14: not applicable in M1, by the user's decision | P-06 |

**Lifecycle scripts**: none is added, so the allowlist stays empty (U1 NFR-WC-16).

## Rejected

| Option | Reason |
|---|---|
| `@fastify/rate-limit` | A dependency for per-key limits that M1 does not build (Q2 A); the per-instance bound is a semaphore |
| An HTTP client library (`undici` as a dependency, `got`, `axios`) | `node:https` already takes the local CA and checks the server name; one fewer dependency |
| One PostgreSQL instance with a database per environment | Q3 B, not chosen: one server shared by E and E2 |

## Not Decided Here

| Selection | Decided at |
|---|---|
| The environment credential's claims, `typ`, and `soorma_ec_` framing; E's minting key ring; the verify-key cache and refetch limiter; the S1 caller's signer; the semaphores' placement; the uniqueness constraint's physical form | U4 NFR Design |
| The per-environment store instances, migrate services, secrets volumes, certificates, network, `tenancy.yaml` additions, alert rules; S1's rotation steps ("wait at least 5 minutes") in the operations notes | U4 Infrastructure Design |

## Stages for U4 After This One

| Stage | Decision | Reason |
|---|---|---|
| NFR Design | **Run** | Credential format and keys; the verify-key cache; the S1 caller; the semaphores; the uniqueness constraint; events and errors |
| Infrastructure Design | **Run** | S2 and a store per environment, migrate services, secrets, network, certificates, alert rules, the rotation wait |
| QA construction enrichment | **Run** after Infrastructure Design | qa-test-cases.md §2.6 |
| Construction Design PR gate | **Run** after enrichment | pr-checkpoint.md Section 5 |
| Code Generation | **Run** after the gate | Always |
