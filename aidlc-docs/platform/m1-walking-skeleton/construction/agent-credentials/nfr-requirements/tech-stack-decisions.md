# Tech Stack Decisions: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9)
**Scope**: U6's selections. U1's toolchain (T-01 to T-16), U2's runtime selections (T-OI-01 to
12), U3's (T-AE-01 to 06), U4's (T-EHA-01 to 10), and U5's (T-AR-01 to 05) apply unchanged
**Dependencies**: **U6 adds none** (NFR-AC-25). It adds workspaces (`services/data-gateway`,
`packages/agent-identity`) whose dependencies are all already in the register at their locked
versions

---

## 1. Decisions

| ID | Selection | Choice | Version | Licence | Kind | Why | Source |
|---|---|---|---|---|---|---|---|
| T-AC-01 | Framework and adapter for S3 | **NestJS 12 on Fastify 5**, as S1 and S2 | 12.3.2; `fastify` 5.12.7 | MIT | Runtime | One framework across the deployables (U2 T-OI-01, 02; U4 T-EHA-01) | NFR-AC-12 to 14 |
| T-AC-02 | Agent credential tokens | **`jose`**, JWS with `Ed25519` only (RFC 9864), fixed in code; `typ` `soorma-ac+jwt` | as locked (U2 T-OI-03) | MIT | Runtime | U4's token pattern (T-EHA-02), with its own key ring (D-AC-03) | NFR-AC-18, 19 |
| T-AC-03 | Cryptography | **`node:crypto`**: Ed25519 keys; HMAC-SHA-256 for the bound's slots; SHA-256 and `timingSafeEqual` through `registry`'s secret functions; `randomBytes` for ids | Node 26.13.0 (U1 T-01) | — | Runtime, built in | As U2, U4, U5 (T-OI-04, T-EHA-04, T-AR-01, 02) | NFR-AC-09, 20 |
| T-AC-04 | The bound's store | **PostgreSQL**: a fixed table of 2^20 slots in E's store, admission as one atomic statement per slot | PostgreSQL 18.4 (U4 T-EHA-05) | PostgreSQL Licence | Runtime, built in | U2's mechanism (NFR-OI-05, 06), moved per environment; no process memory (M1-TECH-03) | NFR-AC-06 to 09 |
| T-AC-05 | The revocation cache | **In-house**, a bounded map keyed on (E, target) with the read's issue time, over an injected clock | — | — | Runtime | A few dozen lines; its rules (age from issue, failures never cached, `revoked` kept, safe eviction) are the design, which a general cache library would obscure | NFR-AC-01, 15, 16 |
| T-AC-06 | Datastore, access, migrations, validation, logging, throttling, monitoring definitions | **Unchanged**: PostgreSQL 18 per environment; `pg` with parameterized SQL through service-kit's `statement()`; `env-store`'s one migration sequence; Ajv 8; NestJS's JSON logger; service-kit's semaphore; `deploy/monitoring/alerts.yaml` | As U4 (T-EHA-05 to 10) | As U4 | Runtime | U6 adds tables, routes, and rules, not mechanisms | NFR-AC-12, 22 to 24 |
| T-AC-07 | Benchmark | **`pnpm bench:revocation`** in P5, on Vitest's bench mode, as U3's `bench:admit` | as locked (U1) | MIT | Development | Reported, not gated (Q5 A) | NFR-AC-16 |

**Lifecycle scripts**: none is added, so the allowlist stays empty (U1 NFR-WC-16).

## 2. Rejected

| Option | Reason |
|---|---|
| One key ring for both credential kinds | Plan Q3 B at Functional Design, not chosen: S2 and S3 could each mint both kinds (D-AC-03) |
| A general-purpose cache library (an LRU package) | A new dependency for a structure whose rules are the security property; T-AC-05 |
| Gating CI on the cache's latency | Q5 B, not chosen: a timing test in CI, where the other units report |
| U2's bound values unchanged (10 per 15 minutes; backoff capped at 15 minutes) | Q4 A, not chosen: a 256-bit secret cannot be guessed at any rate, and the lockout would last 15 minutes or more |
| A window with no backoff | Q4 C, not chosen: consecutive failures should still slow |
| Publishing L and M as fixed values clients rely on | The user's precision on P-08: they are upper bounds, so they can change without a contract break (NFR-AC-05) |

## 3. Not Decided Here

| Selection | Decided at |
|---|---|
| Table layouts, indexes, privileges, and the new migration carrying D-AC-33's CHECK; the cache's entry bound and code shape; `packages/agent-identity`'s interface; P8's generalisation; how B, L, M are configured and checked; the agent key ring's loading | U6 NFR Design |
| S3's Compose services, network, port, health, and migrations; the two new secrets per environment and their delivery; the configuration files carrying B, L, M | U6 Infrastructure Design |

## 4. Stages for U6 After This One

| Stage | Decision | Reason |
|---|---|---|
| NFR Design | **Run** | Tables, privileges, the new migration, the cache, the packages, the configuration and its start-up check |
| Infrastructure Design | **Run** | A new deployable (S3, per environment) and two new secrets per environment (the agent key ring; the bound's counter secret); the user's rule: U4's Compose-model rules checked against S3's services, including any under a profile |
| QA construction enrichment | **Run** after Infrastructure Design | qa-test-cases.md §2.6 |
| Construction Design PR gate | **Run** after enrichment | pr-checkpoint.md Section 5 |
| Code Generation | **Run** after the gate | Always |
