<!-- SPDX-License-Identifier: FSL-1.1-ALv2 -->

# event-ingest (S4)

An environment's data face for events. One runs in each environment (`e` and `e2` on the local
stack). An agent instance publishes an event, and subscribes to the events published in its
environment, with its agent credential. Its operations are defined in
[`contract/event-ingest.openapi.yaml`](../../contract/event-ingest.openapi.yaml):

| Operation   | Request               | What it does                                                                                                                                                                                                                                                                             |
| ----------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `publish`   | `POST /events`        | With `{ draft, payload }`: S4 stamps and seals the envelope, records the publish, and offers one Delivery to each stream open in this environment. `202` with no body. Requires `event:publish`                                                                                          |
| `subscribe` | `POST /subscriptions` | With `{ draft }`: S4 records the subscribe and answers `200` with a `text/event-stream`: a `delivery` event per Delivery accepted after it opened, heartbeats, and one final `end` event. One stream per credential lineage: a later subscribe supersedes it. Requires `event:subscribe` |

**Every check runs here, on the raw request.** The credential is checked with the environment's
agent verify keys and its revocation state, and the draft, any forwarded context, and authority
by `@soorma/authority`'s entry point; nothing trusts an earlier check by another service. A stream
ends at its credential's expiry, and within the propagation bound of a revocation. Delivery is
live only: nothing about an event is stored, replayed, or acknowledged. S4 never calls the
organization level: it starts and serves with S1 stopped.

## Running it

S4 runs as part of the local stack; see
[`services/org-gateway/README.md`](../org-gateway/README.md#running-the-local-stack) for the
prerequisites. `pnpm stack:init` generates each environment's S4 secrets (its seal key, its
database role's password, and its TLS certificate, all named `{env}-…`; its agent verify key is
S3's signing key's verify half), and `pnpm stack:up` starts S4 beside S2 and S3.

| Environment | Edge                     | Database role       |
| ----------- | ------------------------ | ------------------- |
| `e`         | `https://localhost:8446` | `soorma_env_ingest` |
| `e2`        | `https://localhost:8447` | `soorma_env_ingest` |

Each edge is on the host's loopback only, with a certificate from the local CA. S4 joins its own
environment's network only, connects to the store as its own role, `soorma_env_ingest`, which
holds only what S4's statements need, and sees only its own five secrets: never a signing key,
another role's password, the human key ring, the caller key, or a log-pseudonym key. Its image
holds no organization-level code, no identity resolution, no agent identity, no abuse bound, and
no migrations (`{env}-migrate` applies them). Its memory limit is `512m`.

`pnpm stack:smoke` registers an agent through S2 in each environment, bootstraps it at S3, and
subscribes and publishes at S4, receiving its own Delivery; it checks that E's credential is
refused at E2's S4. `pnpm stack:outage` shows S4 serving with S1 stopped (Case 4).

## Operations

### Rotating E's seal key

S4 seals with `sealKeys.current` and verifies a forwarded envelope with any key in
`sealKeys.keys`. A forwarded envelope can be up to a lineage's lifetime old, so the old key keeps
verifying for at least that long:

1. Generate the new key (`pnpm stack:init` writes `{env}-seal-key-{n}` for a new name), add it to
   E's `sealKeys.keys`, and restart every S4 of E: it verifies with both, and still seals with the
   old.
2. Make the new key E's `sealKeys.current`, and restart every S4 of E: new envelopes carry it.
3. Wait at least 24 hours after step 2, then remove the old key from `sealKeys.keys`, and restart.

Once the old key is removed, envelopes sealed with it can't be forwarded: a draft forwarding one
is refused with `invalid_inbound_context`.

### Rotating E's agent verify key

In step with S3's agent key rotation (its README, _Rotating E's agent key_): add the new key's
verify half to `eventIngest.keys.agentVerify` when S3 adds the signing key to `keys.verify`, and
restart S4; remove the old half only after S3's "wait at least 15 minutes", and restart.

S4 refuses to start if a seal key, an agent verify key, or its database password is also named by
another environment's part, by S2's or S3's part, or by the organization level, or if its
database role is not `soorma_env_ingest`.

### When the store is down

New publishes and subscribes answer `503` with `Retry-After: 5`: the environment's store is S4's
availability floor in M1 (GAP-ET-001, soorma-prd#31). A malformed, foreign, or expired credential
is still refused exactly. Open streams stay open for up to the propagation bound, then end with
`end` `unavailable`.

### When the organization level is down

Nothing changes: S4 has no dependency on S1, and starts without it.

### One S4 per environment

M1 runs exactly one S4 per environment, and its fan-out channel is in its own process. A second
instance would not receive the first one's events.

### The fixed values

The propagation bound (60 seconds) is `PROPAGATION_BOUND_MS` from `@soorma/credentials`, the TTL
of both of S4's caches, not configuration. S4's own constants are in `src/settings.ts`: the
Delivery payload bound (64 KiB on its JCS serialization), the body limits (publish 256 KiB,
subscribe 64 KiB), at most 256 open streams with a 1 MiB send buffer each, a heartbeat after 15
seconds of silence, a revocation sweep every second, at most 64 requests in flight, and
`Retry-After: 5`. The contract publishes the payload bound and the stream's behaviour in
[`contract/conventions/envelope.md`](../../contract/conventions/envelope.md#the-delivery).

### Upgrading a local stack to U7

The store's roles are created when it first starts, so a store initialised before U7 has no
`soorma_env_ingest`, and migration `0006` fails at its first grant. Re-create the stack once:
`pnpm stack:down -v`, `pnpm stack:init`, `pnpm stack:up`. CI always starts fresh.

## What it keeps, and what it does not

- An attribution record for each accepted publish and subscribe, in the environment's own store,
  written before the operation takes effect, with the stamped chain, origin, and re-broadening
  outcome. Records are never deleted, and `soorma_env_ingest` holds only `INSERT` on them
- Nothing of an event: no payload, envelope, or seal is stored. A Delivery lives only in memory,
  on its way to the streams open at that moment
- Payload numbers are delivered exactly as written; S4 refuses to start in a runtime that cannot
  carry them (`JSON.rawJSON`)
- Logs are JSON on stdout, naming the agent, the instance, and the environment, never a token, a
  seal, an envelope, a payload, a trace value, or a human

## Layout

| Path                 | What it is                                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------------------------------- |
| `src/main.ts`        | S4: the `JSON.rawJSON` self-check, configuration, the verify-only ring, the seal ring, the store, shutdown     |
| `src/runtime.ts`     | The components, wired once: both caches with the propagation bound, the entry point, the channel, the registry |
| `src/edge/`          | The two operations, in the check order                                                                         |
| `src/stream/`        | A stream (its checks, buffer, heartbeat, and end) and the instance's registry (the cap and superseding)        |
| `src/channel/`       | The fan-out channel: the port, and the in-process channel M1 runs                                              |
| `src/throttle.ts`    | The request limit, released when a stream opens                                                                |
| `src/healthcheck.ts` | The Compose healthcheck (the image has no shell)                                                               |
| `Dockerfile`         | The image: built on `node:26.13.0`, run on distroless, both pinned by digest; S4's closure only                |
| `test/`              | Tests                                                                                                          |

The domain lives in the workspace packages: `@soorma/authority` (P3, the entry point),
`@soorma/credentials` (P5), `@soorma/registry` (P4), `@soorma/attribution` (P7),
`@soorma/jcs`, `@soorma/env-store`, `@soorma/service-kit`, `@soorma/perimeter` (P1),
`@soorma/policy-decision` (P11), and `@soorma/config` (P9).
