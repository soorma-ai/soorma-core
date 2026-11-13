# Logical Components: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). S4 `event-ingest`, environment E, data face
**Patterns**: [nfr-design-patterns.md](nfr-design-patterns.md) (NP-ET-01 to 18)

---

## 1. S4 `event-ingest` (`services/event-ingest`)

| Component | Responsibility | Depends on |
|---|---|---|
| `main.ts` | Loads `eventIngest` configuration and secrets (P9); the start-up check for `JSON.rawJSON` (NP-ET-05); the verify-only ring (P5); the seal ring (`loadSealKeyRing`); the store connection as `soorma_env_ingest`; `synchronous_commit` checked; start and stop (NP-ET-17) | P9, P5, P2 (`loadSealKeyRing` only), `env-store`, service-kit |
| `runtime.ts` | `assembleRuntime`, once: the revocation cache and the facts cache with `PROPAGATION_BOUND_MS` (factories injected), the entry point, the channel, the registry, the semaphore, the scheduler (NP-ET-02, 12) | P5, P3 (`createEnvelopeAdmission`, `createCachingAgentFacts`), P4 (`agentFactsFromStore`), P11, `credentials` |
| `apps.ts` | The edge app over service-kit's adapter with route limits (NP-ET-04); the throttle; the Problem filter | service-kit |
| `edge/` | `publish` and `subscribe`: steps 2 to 4 (P1 `checkAgentRequest`), the parse step (NP-ET-05), `admit` with the Body Form, the cap, the record (NP-ET-14), the hand-off or the stream | P1, P3 entry point, P7, `jcs` (`parseRawNumbers`) |
| `stream/registry.ts` | Streams, the `cid` index, order keys, supersede, the cap (NP-ET-09) | the channel |
| `stream/writer.ts` | The raw reply, headers, the serial chain, buffer accounting, heartbeat, `end`, the grace (NP-ET-10, 12) | the scheduler, P5's cache |
| `stream/sweep.ts` | Every 1 s, every open stream through the cache (NP-ET-12) | P5's cache |
| `channel/` | The port and the in-process channel (NP-ET-08) | — |
| `security-log.ts` | S4's events (NP-ET-16), and U3's security-log port | service-kit |
| `settings.ts` | The constants: 64 permits, 1 s wait, `Retry-After` 5, 256 streams, 1 MiB buffer, 5 s grace, 1 s sweep, 15 s heartbeat, the route limits, P. **No bound**: `PROPAGATION_BOUND_MS` is imported, never redefined | — |
| `throttle.ts` | S3's module, plus the release at stream open (NP-ET-13) | service-kit |

**Not a dependency**: `@soorma/org-identity`, S1, S2, S3, any other environment.

## 2. Changes to Earlier Units' Packages (all additive)

| Package | Change | Earlier tests |
|---|---|---|
| `packages/service-kit` (U4) | `createAdapter`'s optional route limits (NP-ET-04) | Unchanged; new tests |
| `packages/credentials` (U4, U6) | `VerifyKeyRing`, `loadVerifyKeyRing`; `verifyAgentCredential` takes the wider type (NP-ET-07) | Unchanged; new tests |
| `packages/authority` (U3) | The Body Form on `EnvelopeRequest` (NP-ET-06) | **Unchanged** (the user's condition); new tests |
| `packages/jcs` (U3) | `parseRawNumbers`; `raw-json.ts` (the type declarations); `canonicalize`'s `{ numbers: 'source' }`; `CanonicalizationError.pointer` (NP-ET-05) | Unchanged; new tests |
| `packages/attribution` (U4, U6) | `ENVELOPE_BEARING_AGENT_OPERATIONS`; the reverse rule (NP-ET-14) | Unchanged, except **U5's constructed record: the approved class-3 change, exactly** |
| `packages/env-store` (U4) | `0005_attribution_envelope_bearing.sql`, `0006_event_ingest_role.sql` | TC-EHA-068's list gains two names (class 1) |
| `packages/config` (U2, U4, U6) | `loadEventIngest`; the `eventIngest` part of the schema | Unchanged; new tests |
| `contract/` (U1) | `event-ingest.openapi.yaml`; `envelope.md`, `errors.md`, `pre-release.md`, CHANGELOG; generated types | U1's checks extend over the new document |

## 3. Data and Messages

| Item | Where | Never |
|---|---|---|
| The publish and subscribe records | E's store, `attribution_records` (U4's table) | Any payload or seal |
| A Delivery frame | In memory: the channel, then each stream's buffer | Stored, logged, or sent outside E |
| A `supersede` message | The channel | Outside E |
| Cache entries (revocation, agent facts) | Memory, per instance, keyed on E | Shared across environments |

## 4. The Stream's States

```text
  admitted, recorded, registered
              |
              v
          +--------+   delivery checked and written   +--------+
          |  open  |--------------------------------->|  open  |
          +--------+                                  +--------+
              |
              | exp, revoked, unreadable past B, superseded, overflow, shutdown
              v
          +--------+   end { code } written, or the grace elapses
          | ending |-------------------------------------------------+
          +--------+                                                 |
                                                                     v
                                                                 +--------+
                                                                 | closed |
                                                                 +--------+
```

*Text alternative*: a stream opens once it is admitted, recorded and registered. While open,
each delivery is checked and written. Its credential's expiry, a revocation, revocation state
unreadable past B, a superseding stream, an overflowing buffer, or shutdown moves it to ending,
where its `end` event is written, or the 5-second grace elapses; then it is closed. The client
closing its connection closes it directly.

## 5. Obligations Carried Forward

| To | Obligation |
|---|---|
| **Infrastructure Design** | `soorma_env_ingest` in `env-roles.sql` and `pg_hba`; S4 per environment in Compose (`8446`, `8447`), its secrets (TLS, its database password, the agent verify halves, the seal key ring), its memory limit (NFR-ET-09, the number recorded); the one-S4-per-environment Compose-model assertion; TC-ET-022 as a `stack:outage` case; S4's README *Operations* (two-phase seal-key rotation) |
| **Code Generation** | The changes in §2, each with its earlier units' tests unchanged except the recorded ones; the four payload tests; the start-up check |
