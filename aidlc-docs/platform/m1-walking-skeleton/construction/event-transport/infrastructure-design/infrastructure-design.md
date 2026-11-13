# Infrastructure Design: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). **S4 `event-ingest`**, one per environment (E,
E2), the second data-face deployable
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Decisions from**: the Infrastructure Design plan, Q1, Q2 and P-01 to P-16, answered
2026-11-13T01:02:48Z (verbatim in `audit.md`): **Q1 A** (`mem_limit: 512m`, recorded now; S4
measured at Code Generation, the peak recorded, a stop above 460 MiB, never a raise); **Q2 A**
(a seal-key overlap of at least 24 hours, the consequence stated); P-01 to P-16 accepted, the
stricter forbidden-package list included. Every answer is technology (I11); no specification gap
**Rules applied**: [shared-infrastructure.md](../../shared-infrastructure.md) (U2, U4, U6). Every
rule applies, with no deviation; what U7 settles is added there
**Companion**: [deployment-architecture.md](deployment-architecture.md)

M1 is the local Compose stack (M1-NFR-05). There is no cloud provider and no IaC.

---

## 1. Decisions

| ID | Decision | Source |
|---|---|---|
| D-ID-ET-01 | **`e-event-ingest`, `e2-event-ingest`**, written out in full on an `*event-ingest` anchor carrying `*hardening`; image `soorma/event-ingest:local`, built once by `e-event-ingest`; the loopback health listener on 8080; variables `SOORMA_PROJECT`, `SOORMA_ENVIRONMENT`, `SOORMA_HEALTH_PORT` only; started after `{env}-secrets-init` and `{env}-migrate`, **never after `org-gateway`, S2, or S3**; restart `unless-stopped` | P-01 |
| D-ID-ET-02 | **Edges `127.0.0.1:8446` (E) and `127.0.0.1:8447` (E2)** to the container's 8443; **its own `{env}` network only**, alias `event-ingest.{env}.soorma.internal`; never `org-internal-{env}` | P-02; item 5 |
| D-ID-ET-03 | **`{env}-event-ingest-tls`** from the local CA by `stack:certs`; TLS 1.3 at the edge (streams included); `verify-full` to the store | P-03 |
| D-ID-ET-04 | **S4's role `soorma_env_ingest`** in `env-roles.sql`; its password **`{env}-db-ingest-password`** (`stack:init`), set by the store's init script, copied into `db/` and `event-ingest/`; `env-pg_hba.conf` admits it. Grants in `0006` only. `{env}-migrate` runs `0005` and `0006`; S4's image ships no migrations | P-04; NP-ET-14, 15 |
| D-ID-ET-05 | **The seal key ring**: `stack:init` writes **`{env}-seal-key-1`** (base64url, 256 CSPRNG bits), **never overwriting** one; the environment's part of `tenancy.yaml` gains `sealKeys: { current: s1, keys: [{ id: s1, secret: {env}-seal-key-1 }] }`; one ring per environment, never shared | P-05; item 3; U3 NP-02 |
| D-ID-ET-06 | **`event-ingest/`** holds exactly `{env}-event-ingest-tls`, `stack-ca-cert`, `{env}-db-ingest-password`, **`{env}-agent-verify-key-1`**, **`{env}-seal-key-1`**; both keys listed on `{env}-secrets-init` and copied **nowhere else** | P-06; items 3, 4; D-ID-AC-12 |
| D-ID-ET-07 | **`tenancy.yaml`'s `eventIngest` part** (§6): edge, health, database, `keys.agentVerify`; no time value | P-07 |
| D-ID-ET-08 | **The image** (§3), with **`image-packages --forbid @soorma/org-identity,@soorma/identity-resolution,@soorma/agent-identity,@soorma/abuse-bound`** | P-08 |
| D-ID-ET-09 | **No log-pseudonym key for S4**; a test asserts no S4 log line has a human-principal field | P-09 |
| D-ID-ET-10 | **Smoke**: S4's checks per environment (§9), **at the depth U6 gave S3** (*changed at the user's review, 2026-11-13*): a real round trip at each environment's S4 (registered through its S2, bootstrapped at its S3, subscribing and publishing over TLS 1.3, receiving its own Delivery), E's credential refused at E2's S4, each S4's five secrets, S4's session as `soorma_env_ingest`; the existing checks kept | P-10; the user's change |
| D-ID-ET-11 | **`stack:outage` Case 4** (TC-ET-022) (§10) | P-11; item 6 |
| D-ID-ET-12 | **U5's backup e2e lists gain `e-event-ingest`** (§11) | P-12; item 7 |
| D-ID-ET-13 | **S4's README `## Operations`** (§12) | P-13; item 8 |
| D-ID-ET-14 | **The Compose-model rules** (§14): U4's test, list items only; U7's own assertions in a new test file, **exactly one S4 per environment, no replicas** | P-14; item 1 |
| D-ID-ET-15 | **Monitoring** (§13) | P-15 |
| D-ID-ET-16 | **CI** (§16) | P-16 |
| **D-ID-ET-17** | **`mem_limit: 512m`** for each S4 (NFR-ET-09, **the number recorded**): S3's measured 54 MiB, S4's estimated baseline 131 MiB, plus 256 MiB of stream buffers, 387 MiB; 125 MiB (24 %) over. **At Code Generation, S4 itself is measured** idle and under the worst case (**256 stalled streams with full 1 MiB buffers plus 64 concurrent maximum-size publishes**), and **the peak is recorded beside the limit**. **Above 90 % (460 MiB), Code Generation stops for the user; the limit is never raised** | Q1 A; item 2 |
| **D-ID-ET-18** | **The seal-key rotation's overlap is at least 24 hours** (M); the README states the consequence: **once the old key is removed, envelopes sealed with it can't be forwarded** (`invalid_inbound_context`) | Q2 A; item 8 |
| **D-ID-ET-19** | **`loadEventIngest` refuses a shared secret** (§6): a seal key, agent verify key, or database password also named by another environment's part, by another deployable's part in the same environment, or by the organization level (the CA excepted); and any role but `soorma_env_ingest`. A config test for each case. *Added at the user's review (2026-11-13)*: §9's round trip cannot catch a seal key shared across environments | The user's correction; U6 D-CG-AC-27 |

---

## 2. Component → Infrastructure

| Logical component (NFR Design) | Infrastructure |
|---|---|
| S4 `event-ingest` | `{env}-event-ingest`, a distroless container per environment, **exactly one** (D-ID-ET-01, 14) |
| E's fan-out channel | In S4's process (NFR-ET-13): no container, network, or port of its own |
| Open streams and their buffers | S4's memory, within `mem_limit: 512m` (D-ID-ET-17) |
| P5's revocation cache, U3's facts cache | S4's memory |
| Attribution records; migrations `0005`, `0006` | E's store, `{env}-db`, run by `{env}-migrate` (D-ID-ET-04) |
| The seal key ring | `{env}-seal-key-1` in `event-ingest/` (D-ID-ET-05) |
| The agent verify ring | `{env}-agent-verify-key-1` in `event-ingest/` (D-ID-ET-06) |
| S4's database connection | Role `soorma_env_ingest`, password `{env}-db-ingest-password` (D-ID-ET-04) |
| The test-only revocation seeding | `docker compose exec {env}-db psql` as the store's owner, from U7's own e2e file (U6's pattern) |

## 3. The Image

`services/event-ingest/Dockerfile`: S3's two stages, pinned by digest (`node:26.13.0` to build,
`gcr.io/distroless/nodejs26-debian13:nonroot` to run, the digest NFR Design checked
`JSON.rawJSON` on); explicit `COPY` of exactly S4's workspaces: `contract`,
`seams/policy-decision`, `packages/jcs`, `service-kit`, `env-store` (`src/` only, not
`migrations/`), `registry`, `credentials`, `attribution`, `config`, `perimeter`, `envelope`,
`authority`, `policy-decision`, `services/event-ingest`; `pnpm deploy --prod`. **Never**
`org-identity`, `identity-resolution`, `agent-identity`, or `abuse-bound`, checked by
`image-packages --forbid` (D-ID-ET-08) and the secret scan.

## 4. Secrets: Mounted Files Only

Generated by `pnpm stack:init` (0600, never overwritten), listed **only on `{env}-secrets-init`**,
copied by `deploy/local/secrets-init/env.sh {env}`:

| Secret | New | Copied into |
|---|---|---|
| `{env}-event-ingest-tls` | U7 (by `stack:certs`) | `event-ingest/` |
| `{env}-db-ingest-password` | U7 | `db/`, `event-ingest/` |
| `{env}-agent-verify-key-1` | U6 (unmounted until now) | **`event-ingest/` only** |
| `{env}-seal-key-1` | U7 | **`event-ingest/` only** |

`env.sh`: `db/`'s list gains the ingest password, and one line is added; every other line is
unchanged:

```sh
# {env}-event-ingest (distroless nonroot, 65532; U7 D-ID-ET-06): its own role's
# password; the agent verify half and the seal ring, never a signing key.
copy event-ingest 65532 \
  "$env-event-ingest-tls" stack-ca-cert "$env-db-ingest-password" \
  "$env-agent-verify-key-1" "$env-seal-key-1"
```

**Never** in `event-ingest/`: an agent signing key, the human ring, the caller key, a
log-pseudonym key, the app, migrator, or data password. **Never elsewhere**: the seal key and the
verify half.

## 5. S4's Database Role (D-ID-ET-04)

**`env-roles.sql`** creates `soorma_env_ingest` beside the three existing roles, with the same
attributes (`LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS`), only
if absent; `CONNECT` on the target database, `USAGE` on `public`, no `CREATE`. The existing lines
are unchanged. **`db/init/10-soorma-env-roles.sh`** sets its password from
`{env}-db-ingest-password`. **`env-pg_hba.conf`**: the two `hostssl` lines gain
`soorma_env_ingest`.

**`0006_event_ingest_role.sql`** grants exactly NP-ET-15's privileges (column-level `SELECT` on
`registrations`; `SELECT` on the two revocation tables; `INSERT` on `attribution_records`).
**Tests**: the role's attributes (U4's helper with the new role); the privilege test running the
real statements as the role and the refusals (NP-ET-15); the test harness gains the role as an
export, its existing constants and connections unchanged (class 1, shown by U4's, U5's, and U6's
store tests passing unchanged, as U6's D-CG-AC-17).

## 6. `tenancy.yaml`

```yaml
      - id: e
        firstAdmin: h@example.com
        sealKeys:                       # U7 (D-ID-ET-05): read by P9's loadSealKeys
          current: s1
          keys:
            - { id: s1, secret: e-seal-key-1 }
        controlGateway: { … }           # unchanged
        dataGateway: { … }              # unchanged
        eventIngest:
          edge: { port: 8443, tls: e-event-ingest-tls }
          health: { port: 8080 }
          database:
            host: env-db.e.soorma.internal
            port: 5432
            name: soorma_env
            user: soorma_env_ingest
            password: e-db-ingest-password
            ca: stack-ca-cert
          keys:
            agentVerify: [e-agent-verify-key-1]
```

E2's part is the same with `e2-`. Validated by `packages/config`'s schema. **No bound, TTL, or
other time value** (NP-ET-02's no-key test).

**No shared secret** (D-ID-ET-19; *added at the user's review, 2026-11-13*, as U6's `dataGateway`
part, D-CG-AC-27): **`loadEventIngest` refuses** the configuration, naming the offending secret,
when **a seal key** (the environment's `sealKeys`, which only S4 reads), **an agent verify key**
(`agentVerify`), or **the database password** is also named:
- by **another environment's** part (its `sealKeys`, `controlGateway`, `dataGateway`, or
  `eventIngest`)
- by **another deployable's part in the same environment** (`controlGateway`, `dataGateway`)
- by **the organization level**

The CA certificate (`stack-ca-cert`) is the one exception, as for S3. It also refuses a
`database.user` other than `soorma_env_ingest` (never S2's, S3's, or the migrator's role). **A
config test for each case**: a seal key, a verify key, and the database password, each shared
with another environment's part, with S2's part, with S3's part, and with the organization level
(twelve refusals, each naming the secret), and S2's, S3's, and the migrator's role each refused as
`database.user`; plus the valid local `tenancy.yaml` accepted.

## 7. Networks and Ports (D-ID-ET-02)

| Network | Members after U7 |
|---|---|
| `{env}` | `{env}-db`, `{env}-migrate`, `{env}-control-gateway`, `{env}-data-gateway`, **`{env}-event-ingest`**; under the `backup` profile, `{env}-backup`, `{env}-restore` |
| `org-internal-{env}` | `{env}-control-gateway`, `org-gateway` (unchanged) |

Published: `127.0.0.1:8441` (S1), `8442`, `8443` (S2), `8444`, `8445` (S3), **`8446` (E's S4)**,
**`8447` (E2's S4)**. Nothing on `0.0.0.0`.

## 8. Hardening and Resources

S4 inherits `*hardening`: user 65532, read-only root, `tmpfs` `/tmp`, `cap_drop: [ALL]`,
`no-new-privileges`; restart `unless-stopped`; **`mem_limit: 512m`** (D-ID-ET-17). **No
`deploy.replicas`, no `scale`**: one S4 per environment (D-ID-ET-14).

**The measurement at Code Generation** (D-ID-ET-17), recorded in U7's code summary beside the
limit: S4's memory idle on the stack; then the peak under 256 subscribe streams whose readers
stop reading until each buffer holds 1 MiB, with 64 concurrent maximum-size publishes (256 KiB
bodies) in flight. **Peak above 460 MiB: stop for the user, never raise the limit.**

## 9. Smoke (D-ID-ET-10)

*Changed at the user's review (2026-11-13)*: as first written, S4's smoke test never made S4 use
its store, its agent verify key, or its seal key, so a wrong role or password, or a missing seal
or verify key in E2's S4, would have passed; the e2e journey reaches E2's S4 only through a
refusal. **S4's section matches the depth U6 gave S3** (`deploy/local/scripts/smoke.ts` §11), as
a new **§12, S4 in E and E2**. Per environment, in order:

| # | Check | What it proves |
|---|---|---|
| 1 | `{env}-event-ingest` healthy; published on `127.0.0.1:{8446 \| 8447}` only; hardened (as S3's check) | The service as designed |
| 2 | **Its secrets**: `/run/secrets` holds **exactly its five** (`{env}-event-ingest-tls`, `stack-ca-cert`, `{env}-db-ingest-password`, `{env}-agent-verify-key-1`, `{env}-seal-key-1`), owner 65532, mode 0400 | No missing key; nothing extra |
| 3 | TLS 1.3 on its edge | — |
| 4 | A publish with no credential is `401` `credential_refused`, a well-formed Problem with `Soorma-Contract-Version` and `Soorma-Request-Id` | The edge's refusal path (kept) |
| 5 | **Set-up**: H's environment credential at that environment's S2 (as S3's set-up); **a further grant** to H of `event:publish` and `event:subscribe` (a second `/grants` call, after S3's `agent:register` grant, which is unchanged); an agent registered through that S2 with `standingPermissions: ['event:publish', 'event:subscribe']` and `autonomyDeclared: true`, **using the existing `registeredAgent` helper** (below); its secret | — |
| 6 | **Bootstrapped at that environment's S3** | S3's path, again |
| 7 | **The round trip at that environment's S4, over TLS 1.3**: the agent subscribes (`POST /subscriptions`, `200` `text/event-stream`), then publishes (`POST /events`, `202`), and **receives its own Delivery** on its stream | **S4's agent verify key** (O1), **its store** (revocation, agent facts, the two records, as `soorma_env_ingest`), and **its seal key** (the stamp) |
| 8 | **The Delivery**: `envelope.scope` is `{ organization: o1, project: p1, environment: {env} }`; `seal` is a non-empty string | The stamp is this environment's, and sealed |
| 9 | **Database role, right after that environment's round trip** (the pool's sessions close after 10 seconds idle, as U6's TC-AC-090): `soorma_env_ingest` exists with U4's attributes; **S4's session runs as `soorma_env_ingest` over TLS 1.3** (`pg_stat_activity` joined with `pg_stat_ssl`, by S4's address on network `{env}`); S3's still as `soorma_env_data` and S2's as `soorma_env_app` | The role and password are right, and in use |
| 10 | **Cross-environment** (after both environments' round trips): **E's agent credential at E2's S4** is `401` `credential_refused` | O4 at S4 |
| 11 | **The log scan** (kept, extended): every credential, secret, token, seal, and payload the smoke test saw is absent from every container's logs, S4's included | — |

**`registeredAgent`** (`deploy/local/scripts/stack-client.ts`, U6's helper) gains **one optional
parameter**, the registration's further fields (`standingPermissions`, `autonomyDeclared`),
**defaulting to exactly today's body** (`{ agent, standingPermissions: [] }`). Its existing callers
(`smoke.ts` §11, `s1-outage.ts`, `services/data-gateway/test/refusals.test.ts`) pass nothing, so
the request they send is byte-identical. **Class 1, with evidence**, as U6's harness change
(D-CG-AC-17): a parameter added, existing behaviour unchanged, shown by every existing caller's
checks and tests passing unchanged; the diff in the completion message. If any existing caller's
check or test would need to change, Code Generation stops.

**Reach of each check**: a wrong database role or password fails #7 or #9; a missing or wrong
agent verify key fails #7 (the credential refused); **a missing seal key fails #2 or #7**; in
**E2** as in E. *Corrected at the user's review (2026-11-13)*: **a wrong seal key does not fail
#7**: a round trip seals and verifies with the same key, so E2's S4 holding E's seal key would
still pass, and a cross-environment forward could not tell it apart, since every
forwarded-context failure is `invalid_inbound_context`. **A seal key shared across environments
is caught by S4's configuration part instead** (§6, D-ID-ET-19).

## 10. TC-ET-022: S1 Stopped (D-ID-ET-11)

`deploy/local/scripts/s1-outage.ts` gains **Case 4**, after the three existing cases (unchanged):
1. Stop `org-gateway`
2. **(a)** With `e-event-ingest` running: B subscribes, A publishes, B receives the Delivery
3. **(b)** Restart `e-event-ingest`, S1 still stopped: it becomes healthy; the round trip again
4. Start `org-gateway`; wait until healthy

Its agents and credentials come from the store-owner seeding helpers (not a *done when* proof).
Class 1: a case added, the existing cases and checks unchanged. Run in CI's S1-stopped
demonstration.

## 11. U5's Backup E2E (D-ID-ET-12)

`e2e/agent-registration.test.ts`, class 1 (a service added to each list, every assertion
unchanged):

```diff
-      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-data-gateway', 'e-db']);
-      docker([...COMPOSE, 'rm', '-f', 'e-control-gateway', 'e-data-gateway', 'e-db', 'e-migrate']);
+      docker([...COMPOSE, 'stop', 'e-control-gateway', 'e-data-gateway', 'e-event-ingest', 'e-db']);
+      docker([...COMPOSE, 'rm', '-f', 'e-control-gateway', 'e-data-gateway', 'e-event-ingest', 'e-db', 'e-migrate']);
```

and the `up -d --wait` that brings `e-control-gateway` and `e-data-gateway` back brings
`e-event-ingest` with them. The exact lines are confirmed at Code Generation.

## 12. Operations Notes (D-ID-ET-13, 18)

`services/event-ingest/README.md` `## Operations`:

| Topic | Note |
|---|---|
| **Seal-key rotation** (two phases) | (1) `stack:init` writes `{env}-seal-key-{n+1}`; add it to `sealKeys.keys`, restart S4: it verifies with both and still seals with the old. (2) Make it `current`, restart S4: new envelopes carry the new key. (3) **Wait at least 24 hours**, then remove the old key, restart. **Once the old key is removed, envelopes sealed with it can't be forwarded** (`invalid_inbound_context`) |
| **Agent verify-key rotation** | In step with S3's (U6 D-ID-AC-17): add the new verify half to `agentVerify` when S3 adds the signing key to `verify`; remove the old one only after S3's "wait at least 15 minutes" |
| The store down | New publishes and subscribes `unavailable` (503, `Retry-After: 5`): E's store is S4's availability floor in M1 (GAP-ET-001, soorma-prd#31). Open streams stay open for up to the propagation bound, then end `unavailable` |
| S1 stopped | No effect (TC-ET-022) |
| One S4 per environment | M1 runs exactly one; the channel is in process. A second instance would not receive the first one's events |
| The constants | B is `PROPAGATION_BOUND_MS` (60 s), imported, not configuration; P 64 KiB; limits 64 KiB and 256 KiB; 256 streams, 1 MiB each; `mem_limit` 512m |
| **Upgrading a local stack to U7** | A store initialised before U7 has no `soorma_env_ingest`, so `0006` fails on its first grant. Re-create it once: `pnpm stack:down -v`, `pnpm stack:init`, `pnpm stack:up`. CI always starts fresh |

A docs test checks the rotation steps, "at least 24 hours", and the constants against the code.

## 13. Monitoring (D-ID-ET-15)

S4's events and alert rules (NP-ET-16) join `deploy/monitoring/`: `stream.revoked` at 1, by
environment; `stream.overflow` at 5 in 5 minutes, by environment; `ingest.refused` and
`envelope.refused` at 20 in 5 minutes, by code; the shared `store.unavailable` and
`throttle.refused` rules unchanged. The monitoring tests gain S4's items (class 1); the overlap
with S1 to S3 pinned to exactly `store.unavailable` and `throttle.refused`. Nothing evaluates them
in M1 (SECURITY-14, the user's decision).

## 14. The Compose-Model Rules (D-ID-ET-14)

**U4's `deploy/test/compose-model.test.ts`**, rendered with every profile (U6 D-ID-AC-13); **list
items only, class 1**:

| Change | Class |
|---|---|
| The service list gains `event-ingest` per environment | 1 |
| The `{env}-secrets-init` list gains `{env}-event-ingest-tls`, `{env}-db-ingest-password`, `{env}-agent-verify-key-1`, `{env}-seal-key-1` | 1 |
| `env.sh`'s copy directories gain `event-ingest` | 1 |
| The variable allowlist gains `{env}-event-ingest` (`SOORMA_ENVIRONMENT`, `SOORMA_HEALTH_PORT`, `SOORMA_PROJECT`) | 1 |
| *"Each environment service names its own environment and project"* gains `event-ingest` | 1 |
| The `{env}` network's members gain `{env}-event-ingest` | 1 |
| The published list gains `e-event-ingest 127.0.0.1:8446->8443` and `e2-event-ingest 127.0.0.1:8447->8443` | 1 |

If any assertion would need more than an item added, Code Generation stops (the standing rules).

**U7's own assertions**, a new `deploy/test/event-ingest.test.ts`, with every profile:
- **each environment has exactly one service whose role is `event-ingest`, with no
  `deploy.replicas` and no `scale` above 1** (item 1)
- **each S4's `mem_limit` is 512m**, the recorded number (D-ID-ET-17)
- `{env}-seal-key-*` and `{env}-agent-verify-key-*` only in their environment's `event-ingest/`
- no `{env}-agent-signing-key-*`, human ring, caller key, log-pseudonym key, or another role's
  password in `event-ingest/`
- S4 on its `{env}` network only, never `org-internal-*`
- S4's variables read only from its allowlist

## 15. Obligations Discharged

| From | Obligation | Where |
|---|---|---|
| U3 (#10) | Seal key ring per environment: 256 bits, CSPRNG, never logged, never in source or IaC, never shared, mounted only into S4; U2's seed-key form; two-phase rotation in the operations notes | §1 (D-ID-ET-05, 06), §4, §6, §12 |
| U6 (#10) | Edges from `8446`; verify halves on `{env}-secrets-init`, copied only into S4's subdirectory; S4's own role by D-ID-AC-07's pattern | §1, §4, §5, §7 |
| NFR Requirements §5 | One S4 per environment asserted; memory sized and recorded; S4 in Compose; TC-ET-022 | §1, §8, §10, §14 |
| NFR Design §5 | The role in `env-roles.sql` and `pg_hba`; S4's secrets; the README | §5, §4, §12 |
| The user's eight items | All eight | §1 to §14 |

## 16. CI (D-ID-ET-16)

| Job | Steps added (class 2) |
|---|---|
| Build, check, and test | S4's tests; the new package tests (service-kit, P5, P3, `jcs`, P7, `env-store`, P9); `deploy/test/event-ingest.test.ts` |
| Images, image secret scans, stack smoke test, and the S1-stopped demonstration | Build S4's image; its secret scan; `image-packages --forbid` (D-ID-ET-08); the smoke test's S4 checks; Case 4 |
| E2E (`test:e2e` on a fresh stack) | *Done when* 3, 4, 6, 7 in U5's journey; U7's own file |

## 17. Carried Forward

| To | Item |
|---|---|
| **U7 Code Generation** | Every file above; the class-1 diffs of §9 (`registeredAgent`, with evidence), §11 and §14 in the completion message; the role and its tests (§5); **the memory measurement and its stop (D-ID-ET-17)**; the upgrade note |
| **Build and Test** | `stack:outage` with Case 4; the Compose-model, privilege, and docs tests; the image checks; the recorded memory peak |
| **The first hosted deployment** | A distributed channel and more than one S4 per environment (NFR-ET-13's residual); per-agent limits; as `shared-infrastructure.md`'s *Carried* row |

## 18. Security Compliance at Infrastructure Design

| Rule | Status | Note |
|---|---|---|
| SECURITY-01 | Compliant in transit; at rest not applicable in M1 (the user's decision) | TLS 1.3 edge; `verify-full` to the store; no secret stored by S4 |
| SECURITY-02, 04 | N/A | No new intermediary; no HTML |
| SECURITY-03 | Compliant, except the centralized log service (the user's M1 decision) | JSON to stdout; no human field; no secret |
| SECURITY-05 | Compliant | Route body limits; P |
| SECURITY-06 | Compliant | Its own role with column-level `SELECT`; its own secrets subdirectory; verify halves only |
| SECURITY-07 | Compliant | Loopback edges; `{env}` network only |
| SECURITY-08, 12 | Compliant | Every check at S4; mounted secrets only |
| SECURITY-09 | Compliant | Hardened container; no default credential; generic Problems |
| SECURITY-10 | Compliant | Pinned images; secret scan; the stricter `image-packages` list |
| SECURITY-11 | Compliant | Throttle, cap, buffer, memory limit |
| SECURITY-13 | Compliant | Checksummed migrations; records before effects |
| SECURITY-14 | Not applicable in M1 (the user's decision) | Rules as files |
| SECURITY-15 | Compliant | Fail closed; a memory limit with a measured peak |

## 19. Invariant Compliance at Infrastructure Design

| Invariant | Status |
|---|---|
| I1 | Compliant: one S4, channel, store, seal ring, and verify ring per environment; no network spans two |
| I2 | Compliant: S4 on its own edge; no internal path bypasses it |
| I3 | Compliant: nothing reads a network position for identity |
| I4 | Compliant: the records in E's store; S4's `INSERT` only |
| I5 | Compliant: no infrastructure path evaluates authority |
| I6 | Compliant: S4 data face only, its own port and limits |
| I7 | Compliant: the contract unchanged by this stage |
| I8 | Compliant: no commercial capability; no broker or durable queue |
| I9 | Compliant: no tenant name in any file |
| I10 | Compliant: one S4 per environment is a deployment fact, never an identity input |
| I11 | N/A |

## 20. Test Cases (assigned at QA construction enrichment, 2026-11-13)

`inception/test-cases/event-transport/`:

| Decision | Test cases |
|---|---|
| D-ID-ET-01, 02, 07, 14 | TC-ET-065 (the Compose model: one S4 per environment, no replicas, 512m, secrets, network, variables) |
| D-ID-ET-03 | TC-ET-067 |
| D-ID-ET-04 | TC-ET-082, TC-ET-081 |
| D-ID-ET-05 | TC-ET-084 |
| D-ID-ET-06 | TC-ET-065, TC-ET-085 (#2) |
| D-ID-ET-08 | TC-ET-083 |
| D-ID-ET-09 | TC-ET-068 |
| D-ID-ET-10 | TC-ET-085 |
| D-ID-ET-11 | TC-ET-022 |
| D-ID-ET-12 | TC-ET-086 |
| D-ID-ET-13, 18 | TC-ET-087 |
| D-ID-ET-15 | TC-ET-069 |
| D-ID-ET-16 | CI itself (every case above runs in it) |
| D-ID-ET-17 | TC-ET-088 |
| D-ID-ET-19 | TC-ET-089 |
