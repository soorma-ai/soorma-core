# Tech Stack Decisions: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10)
**Scope**: U7's selections. U1's toolchain (T-01 to T-16), U2's runtime selections (T-OI-01 to
12), U3's (T-AE-01 to 06), U4's (T-EHA-01 to 10), U5's (T-AR-01 to 05), and U6's (T-AC-01 to 07)
apply unchanged
**Dependencies**: **U7 adds none** (NFR-ET-22). It adds one workspace (`services/event-ingest`,
named at NFR Design) whose dependencies are all already in the register at their locked versions

---

## 1. Decisions

| ID | Selection | Choice | Version | Licence | Kind | Why | Source |
|---|---|---|---|---|---|---|---|
| T-ET-01 | Framework and adapter for S4 | **NestJS 12 on Fastify 5**, as S1 to S3 | 12.3.2; `fastify` 5.12.7 | MIT | Runtime | One framework across the deployables (U2 T-OI-01, 02; U6 T-AC-01) | NFR-ET-10, 12 |
| T-ET-02 | The event stream | **Server-Sent Events written on Fastify's raw reply**, by S4's own code: the headers, `event:` and `data:` lines, comment heartbeats, the `end` event, backpressure from the socket's write result | Node 26.13.0 (U1 T-01) | — | Runtime, built in | `subscribe` is a POST carrying a draft, and the stream needs an exact end event, a byte-counted buffer, and its own checks before each write. NestJS's `@Sse()` serves GET with an Observable and controls none of these | NFR-ET-07, 08, 10 |
| T-ET-03 | E's fan-out channel | **In house, in process**, behind a channel port: one channel object per S4 process, carrying `delivery` and `supersede` messages to every registered stream; **one S4 per environment in M1** | — | — | Runtime | Q3 A: no new dependency or deployable; a distributed implementation fills the same port later | NFR-ET-13 |
| T-ET-04 | Measuring the payload | **`packages/jcs`** (U3's RFC 8785 implementation): the payload's JCS byte length against P | workspace | FSL-1.1-ALv2 (the package's own) | Runtime | The envelope bound is measured the same way (U1 BR-ENV-10, BR-DR-09) | NFR-ET-02 |
| T-ET-05 | Datastore, access, migrations, validation, logging, throttling, caches, monitoring definitions | **Unchanged**: PostgreSQL 18 per environment; `pg` with parameterized SQL through service-kit's `statement()`; `env-store`'s one migration sequence; Ajv 8 (through U3's validator); NestJS's logger in U4's JSON format; service-kit's semaphore; P5's revocation cache and U3's agent-facts cache; U2's YAML monitoring files | as locked | as registered | Runtime | Inherited | NFR-ET-12, 18, 19, 21 |

**Lifecycle scripts**: none is added, so the allowlist stays empty (U1 NFR-WC-16).

## 2. Rejected

| Option | Reason |
|---|---|
| PostgreSQL `LISTEN`/`NOTIFY` as the channel | Q3 B, not chosen: a notification carries at most 8 000 bytes and a Delivery up to about 81 KiB, so events would be stored in E's store and announced by id, against live only and PF §6 *Envelope (in flight): not stored here*; S4's role would need `DELETE` |
| A message broker per environment (for example NATS without persistence) | Q3 C, not chosen for M1: a new dependency and a deployable per environment. The candidate for the distributed channel at the first hosted deployment |
| NestJS `@Sse()` | GET and an Observable only; see T-ET-02 |
| An SSE library | A new dependency for a few dozen lines whose rules (the end event, the buffer, the checks) are the behaviour |
| Larger or smaller payload bounds (256 KiB, 16 KiB) | Q1 B and C, not chosen |
| A sweep every 5 seconds | Q4 B, not chosen: R does not change the store's load (the cache re-reads at most once per B), so a shorter close lag costs only cache lookups |

## 3. Not Decided Here

| Selection | Decided at |
|---|---|
| The workspace's name and layout; the channel port's interface; the stream registry, sweep, and buffer accounting; the Body Form's shape on `admit`; S4's role name and the migrations' numbers; the log event names | NFR Design |
| S4's container memory limit (NFR-ET-09); the Compose services, ports, secrets, networks, and the one-S4-per-environment assertion | Infrastructure Design |

## 4. Next Stages

**NFR Design runs** (the patterns above). **Infrastructure Design runs**: S4 is a new
deployable with its own secrets, role, ports, and memory limit.
