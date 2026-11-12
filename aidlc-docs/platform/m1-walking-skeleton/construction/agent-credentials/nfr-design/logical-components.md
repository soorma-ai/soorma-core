# Logical Components: U6 `agent-credentials`

**Unit**: U6 `agent-credentials` (soorma-core#9). Data face, environment level
**Patterns**: [nfr-design-patterns.md](nfr-design-patterns.md) (NP-AC-01 to 13)
**Requirements**: [../nfr-requirements/nfr-requirements.md](../nfr-requirements/nfr-requirements.md)

---

## 1. S3 `data-gateway`: A New Deployable

```text
+------------------------------------------------------------+
| services/data-gateway (S3), one per environment            |
|   throttle (64 in flight) -> routes                        |
|   POST /agent-credentials                                  |
|     P8 SlotBound (agent key, agent limits)                 |
|     -> agent-identity (one read) -> Tx: registration,      |
|        revocation (direct), agent_credentials, P7 -> mint  |
|   POST /agent-credentials/current/renewal                  |
|     P1 checkAgentRequest (verify, revocation in the Tx)    |
|     -> Tx: record, registration, renew, P7 -> mint         |
|   reads and writes E's store only; no S1 address           |
+------------------------------------------------------------+
```

*Text alternative*: S3 runs one per environment. Every request takes a throttle slot first.
Bootstrap passes P8's bound (keyed on the agent, with the agent limits), then the agent half of
identity resolution (one read), then one transaction holding the registration's state, the
agent's revocation read directly, the credential record, and the attribution record; then the
token is minted. Renewal runs P1's `checkAgentRequest` with a revocation read bound to its
transaction, then reads the record and the registration, moves the expiry, and writes the
attribution record in the same transaction; then mints. S3 talks to E's store only.

| Route | Operation | Scheme | Body |
|---|---|---|---|
| `POST /agent-credentials` | `exchangeBootstrap` | none | `{ agent, secret, instance }`, closed |
| `POST /agent-credentials/current/renewal` | `renewAgentCredential` | `agentCredential` | none |

**Never in S3**: `@soorma/org-identity`, `@soorma/identity-resolution`, `@soorma/authority`
(NP-AC-10); any S1 address; the human key ring; any configuration key for B, L, or M (NP-AC-01).

## 2. Packages

| Package | Change | Owner | Depends on (production) |
|---|---|---|---|
| `services/data-gateway` | **New** (S3) | U6 | `service-kit`, `config`, `contract`, `perimeter`, `credentials`, `agent-identity`, `abuse-bound`, `attribution`, `env-store`, `registry`, `policy-decision-seam`, NestJS, Fastify (as S2) |
| `packages/agent-identity` | **New** (P6's agent half) | U6 | `identity-resolution-seam`, `registry`, `env-store`, `service-kit` |
| `seams/identity-resolution` | **Extended**: `src/agent.ts`, the agent half's types; the human half unchanged | U2 (human), U6 (agent) | — |
| `packages/credentials` | **Extended**: `lifetimes.ts` (the three constants), `agent-token.ts`, `agent-records.ts`, `revocation.ts` (the direct source and the cache), statements in `sql.ts`; U4's `token.ts`, `records.ts`, `key-ring.ts` unchanged | U4, U6 | unchanged |
| `packages/abuse-bound` | **Generalised**: `SlotBound`, `slotOfKey`, `BatchWriter<T>`, `agentSlotKey`, `AGENT_BOOTSTRAP_LIMITS`; U2's exports kept, built on them; `@soorma/org-identity` to `devDependencies`; `@soorma/jcs` added | U2, U6 | `service-kit`, `jcs` |
| `packages/perimeter` | **Extended**: `checkAgentRequest` (callbacks) and S3's presenter (`soorma_ac_` only) | U2, U4, U6 | unchanged (`service-kit`) |
| `packages/attribution` | **Extended**: the envelope-free agent operations and the writer's refusal (D-AC-33) | U4, U6 | unchanged |
| `packages/env-store` | **Extended**: `0003_agent_credentials.sql`, `0004_attribution_envelope_free.sql`; the test harness's owner fixture for revocation seeding | U4, U6 | unchanged |
| `packages/config` | **Extended**: an environment's `dataGateway` part, naming S3's secrets (the agent key ring, the bound's counter secret) and listener settings, as `controlGateway`; no B, L, or M | U2, U4, U6 | unchanged |
| `contract` | **Extended**: `data-gateway.openapi.yaml`; `credentials.md`'s *Revocation and Lifetimes*; `errors.md`'s `authentication_failed`; `identifiers.md`'s instance sentence; regenerated types | U1, U6 | — |
| `tools/checks` | **Extended**: `image-packages` (NP-AC-10); two secret patterns (NP-AC-12, class 2) | U1, U2, U6 | — |

## 3. The Environment Store: What U6 Adds

| Table | Migration | Rows | App role |
|---|---|---|---|
| `agent_credentials` | `0003` | One per bootstrap (a lineage) | `SELECT`, `INSERT`, `UPDATE (expires_at)` |
| `credential_revocations` | `0003` | Test-seeded only in M1 | `SELECT` |
| `agent_revocations` | `0003` | Test-seeded only in M1 | `SELECT` |
| `attempt_slots` | `0003` | At most 2^20 | `SELECT`, `INSERT`, `UPDATE` |
| `failed_bootstrap_attempts` | `0003` | One per failed attempt on an existing registration | `INSERT` (and its sequence's `USAGE`) |
| `attribution_records` (U4's) | `0004` | — | unchanged; a new CHECK (D-AC-33) |

`0001` and `0002` are untouched. No `DELETE` is granted on any U6 table.

## 4. The Three Numbers

| Constant | Value | Read by |
|---|---|---|
| `PROPAGATION_BOUND_MS` | 60,000 | P5's cache (S4, from U7); **U3's term cache, passed by U7** |
| `AGENT_CREDENTIAL_LIFETIME_MS` | 900,000 | S3 (bootstrap, renewal) |
| `LINEAGE_MAX_AGE_MS` | 86,400,000 | S3 (bootstrap) |

Exported from `@soorma/credentials`; published in `credentials.md` (B as the platform's bound;
L and M as upper bounds, with the client rules), and tested against these constants.

## 5. CI

| Job | Steps U6 adds |
|---|---|
| Build, check, and test | S3's tests, `agent-identity`'s, P5's and P8's new tests, the store's privilege and constraint tests; the docs tests |
| Images, image secret scans, stack smoke test, and the S1-stopped demonstration | Build S3's image; its secret scan; **`image-packages` on S3's image** (forbid `org-identity`, `identity-resolution`); **`image-packages` on S2's image** (forbid `org-identity`; the user's addition, class 2); the positive control on S1's image; S3 in the stack smoke test (Infrastructure Design); the e2e proof of *done when* 2 |

## 6. Test Doubles and Harness

| Double | Use |
|---|---|
| A fake `AgentIdentityResolver` | S3's unit tests, each rejection reason |
| A failing direct revocation source | The cache's outage tests; S3's `unavailable` |
| The injected `Clock` | L, M, B, the bound's window and backoff (NP-AC-13) |
| The owner fixture (`packages/env-store/test/harness`) | Revocation seeding in database tests (NP-AC-06) |
| `e2e/support`'s seeding helper | Revocation seeding on the running stack, through `docker compose exec` as the migrator (NP-AC-06) |

## 7. Forward Obligations

| To | Obligation |
|---|---|
| **U6 Infrastructure Design** | `{env}-data-gateway` for E and E2: image, network (E's own), port, health, TLS; two new secrets per environment (the agent key ring; the bound's counter secret), mounted as files, named in the `dataGateway` configuration part; `{env}-migrate` runs `0003` and `0004` (the env-store migrations already ship in S2's image; whether S3's image carries them too is Infrastructure Design's); **U4's Compose-model rules applied to S3's services, rendering with every profile** (the user's rule); the S1-stopped case for S3 (TC-AC-017). **U5's backup and restore e2e** (`e2e/agent-registration.test.ts`) stops `e-control-gateway` and `e-db` by name before emptying the store; with S3 also connected to `e-db`, that list gains `e-data-gateway` (an item added, class 1), checked at Code Generation |
| **U6 Code Generation** | The diffs to earlier units' tests, each with its class: TC-EHA-068's migration list (class 1, NP-AC-02); the image check on S2 (class 2, NP-AC-10); the secret patterns (class 2, NP-AC-12); U5's restore e2e service list (class 1, above). **Stop conditions**: any change to U2's P8 tests or canonical vectors (Q4 A); any change to U4's `token.ts` tests (NP-AC-09) |
| **U7 (soorma-core#10)** | **Pass `PROPAGATION_BOUND_MS` to U3's term cache** (`createCachingAgentFacts`'s `ttl`; the user's instruction) and to S4's revocation cache (NP-AC-05), with a test that both use it and no configuration key exists; S4 loads the agent ring's verify halves only (a loader variant); S4's closure and image checks in NP-AC-10's pattern. Posted on #10 when this stage is approved |
| **QA construction enrichment** | Test cases for NP-AC-01 to 13, alongside the Functional Design and NFR Requirements targets |
