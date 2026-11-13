# NFR Requirements: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). Data face, environment level: S4 `event-ingest`
and E's fan-out channel
**Profile source**: **PF §9 *NFR Profile*** @ `prd-platform-foundations-v1.3`
**Built against**: PF @ `prd-platform-foundations-v1.3`, ID @ `prd-identity-v1.0`
**Approved**: 2026-11-13T00:21:13Z, with the user's addition (§4's ASCII-escaping residual; NFR-ET-06's wording); NFR-ET-04 and the limits unchanged
**Decisions from**: the NFR Requirements plan, Q1 to Q6 and P-01 to P-16, answered
2026-11-13T00:13:38Z (recorded verbatim in `audit.md`): Q1 A; **Q2 A with the user's precise
guarantee** (NFR-ET-04); **Q3 A with its consequence stated** (NFR-ET-13, §4); Q4 A; Q5 A with
the memory sizing at Infrastructure Design (NFR-ET-09); Q6 A; P-01 to P-16 accepted
**Functional Design**: `construction/event-transport/functional-design/` (approved, `a7d7804`)
**Tech stack**: [tech-stack-decisions.md](tech-stack-decisions.md)
**Gap**: GAP-ET-001 (Open, soorma-prd#31) bears on the *Availability* row; its work-around
(D-ET-09) stands, and nothing here decides it

Symbols: **B** `PROPAGATION_BOUND_MS` (60 s); **L** the agent credential's lifetime (15 min);
**P** the Delivery payload bound; **R** the stream's sweep interval.

---

## 1. The Plane-Face Profile: PF §9, Carried Forward

Settled by the PRD and carried verbatim. No control-face property is added: no read-your-writes
target for a human operator, no durability class for events (live only, GAP-INT-003).

| Property | PF §9 | How U7 meets it |
|---|---|---|
| Latency: revocation read | **Hot path; must not dominate request latency** | P5's cache at S4: a hit is a memory lookup (U6 NFR-AC-16); a miss one indexed read (NFR-ET-16) |
| Latency: exchange and renewal | Startup and periodic | N/A at S4 (S3's) |
| Availability | **High, but bounded by the cache rather than absolute**; "the revocation store is not the availability floor for the environment" | **The revocation read meets it**, through the cache for B. **New publishes and subscribes do not, in M1**: the record's synchronous write makes E's store their floor (GAP-ET-001, D-ET-09, Open). Open streams survive a store outage for up to B (NFR-ET-14) |
| Throughput | **Scales with total request volume, not agent count**: one read per request | **Per instance**, one cached revocation read per request, one agent-facts read on a miss, one record per operation. **Across instances: not demonstrated in M1**, which runs exactly one S4 per environment (NFR-ET-13; residual §4) |
| Isolation | **Per environment; no global revocation list** | One S4, cache space, and channel per environment (BR-FO-01) |
| **Revocation propagation bound** | **Finite, published, platform-set, not tenant-configurable**; "the bound *is* the cache TTL: one number" | `PROPAGATION_BOUND_MS` as both caches' TTL; no configuration key; a test (NFR-ET-01) |

## 2. Categories That Do Not Apply

| Category | Why |
|---|---|
| An availability percentage, failover, disaster recovery | A local stack in M1, no hosted deployment (as U2 to U6) |
| Durability of events | Live only (GAP-INT-003, Awaiting PRD: Event) |
| Scalability targets across instances | One S4 per environment in M1 (NFR-ET-13); the first hosted deployment |
| Usability, accessibility | No user interface |

## 3. Requirements

### Bounds

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-ET-01 | **B and L as U6 set them**: `PROPAGATION_BOUND_MS` (60 s) is the TTL of P5's revocation cache and of U3's agent-facts cache at S4; **no configuration key** for it; L (15 min) caps a stream through its credential's `exp`. R and the heartbeat are not bounds on revocation (BR-BND-04) | P-01; D-ET-15; PF FR-012 | The composition and no-key test (BR-BND-03); *QA enrichment* |
| NFR-ET-02 | **P = 64 KiB (65 536 bytes)**, measured on the payload's JCS serialization (*Consistency fix from NFR Design (2026-11-13)*: **with each number counted by its source text**, `packages/jcs`'s `{ numbers: 'source' }` mode, NP-ET-05). A publish whose payload exceeds it is `payload_too_large` (413) at step 6, after the schema. **A Delivery is therefore at most about 81 KiB** (envelope 16 KiB, seal 1 KiB, payload 64 KiB, compact) | Q1 A; D-ET-27 | P at 65 536 bytes accepted, 65 537 refused; *QA enrichment* |
| NFR-ET-03 | **Step-1 limits on the raw body**: **subscribe 64 KiB (65 536 bytes); publish 256 KiB (262 144 bytes)**. The limit is accepted; **the limit plus one byte is `payload_too_large`** (413), before any credential is read | Q2 A; D-ET-26 | Both edges at both operations; *QA enrichment* |
| NFR-ET-04 | **The guarantee** (the user's, Q2): both limits admit **any maximum-size forwarding draft shaped like a real stamped envelope**: a chain of **up to 32 entries**, the envelope's **defined fields**, and **one flat unknown field padding the envelope to 16 384 bytes in JCS**, with the seal, `traceparent`, `tracestate` and `clientContractVersion` at their maxima; **serialized with every non-ASCII character escaped as `\uXXXX` and indented with 2 spaces**. **For publish**, the same draft plus **a maximum payload (P, as one flat member) serialized the same way**. *Why it fits*: escaping at most triples a non-ASCII character's UTF-8 bytes and leaves ASCII unchanged, so the envelope is at most 49 152 bytes plus indentation (about 2 KB over a 32-entry chain), and the payload at most 196 608 bytes plus indentation; the totals sit under 64 KiB and 256 KiB. **No limit admits every indented maximum-size draft**: an unknown field has no nesting limit (only the 16 KiB size and `maxChainDepth` bound the envelope), and indentation grows with depth; that is the residual in §4 | Q2 A, the user's guarantee; U3 OB-03 | **P-15's test sends exactly that shape**, built at the maximum, through step 1 of **both** operations (accepted), and the same body grown to the limit plus one byte (`payload_too_large`); *QA enrichment* |
| NFR-ET-05 | **U3's maximum-nesting test runs at each operation's actual limit** (64 KiB and 256 KiB, both under U3's 1 MiB body): the JSON parser and every walk survive it | U3 OB-09; NFR-AE-19 | *QA enrichment* |
| NFR-ET-06 | **The contract recommends compact JSON**: `envelope.md` states that clients should serialize drafts and payloads **"compact, without HTML-safe or other ASCII escaping (for example Go's `json.Encoder.SetEscapeHTML(false)`)"** (as JCS or `JSON.stringify` does), because the step-1 limits guarantee only NFR-ET-04's shape. A statement, compatible. *Wording added at approval (the user's, 2026-11-13)* | Q2, the user's | The contract check; Functional Design §14 (consistency fix) |

### The stream

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-ET-07 | **R = 1 second**: every open stream is checked for revocation through P5's cache at least every second, besides before every delivery. **Heartbeat every 15 seconds**: an SSE comment line on a stream with no other event | Q4 A; D-ET-04 | Injected-clock tests: the close by revocation + B + 1 s; a heartbeat at 15 s of silence; *QA enrichment* |
| NFR-ET-08 | **At most 256 open streams per S4 instance**; **a 1 MiB send buffer per stream** (bytes queued and not yet written; at least 12 maximum-size Deliveries); **a 5-second grace** for a stream that cannot take its `end` event. Worst case: **256 MiB of stream buffers per instance** | Q5 A; D-ET-06, 25 | The 257th stream `unavailable` (a supersede on the same instance not counting); a buffer past 1 MiB ends `overflow`; the grace close; *QA enrichment* |
| NFR-ET-09 | **S4's container memory is sized for the 256 MiB worst case of stream buffers plus its baseline** (runtime, both caches at their maximum entries, in-flight requests). **The number is fixed and recorded at Infrastructure Design**, from the baseline measured there. *Recorded at Infrastructure Design (2026-11-13, D-ID-ET-17)*: **`mem_limit: 512m`** (S3 measured at 54 MiB; S4's baseline estimated at 131 MiB; 387 MiB with the buffers); S4's own peak measured at Code Generation and recorded beside it; above 460 MiB, a stop, never a raise | Q5 A, the user's | Infrastructure Design's record; the Compose model carries the limit |
| NFR-ET-10 | **The stream's connection**: no server-side request or idle timeout on the stream route (its life is at most L); every other route keeps the server's timeouts. **SSE encoding**: UTF-8; `event: delivery` or `event: end`; one `data:` line of compact JSON; no `id:`, no `retry:`; comments (`:`) for heartbeats | P-04, P-05 | A stream outlives the server's ordinary timeouts; the encoding test; *QA enrichment* |
| NFR-ET-11 | **Shutdown**: on termination, stop accepting, end every open stream with `end` `unavailable`, exit within **5 seconds** | P-06; BR-SM-08 | *QA enrichment* |

### Throughput and availability

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-ET-12 | **Throttle**: at most **64 requests in flight per S4 instance**; a slot taken before step 1 and released once when the response is sent, the request aborts, or a stream opens; a request that cannot take a slot within **1 second** is `unavailable`. **`Retry-After: 5`** on S4's own `unavailable` (throttle, cap, revocation unreadable, the record, the hand-off); U3's stays 1 (NFR-AE-21) | P-02, P-03; U4 NFR-EHA-04; U6 NFR-AC-12 | U4's 64-abort test shape at S4; *QA enrichment* |
| NFR-ET-13 | **E's fan-out channel is in process**, behind a **channel port** a distributed implementation can fill later. **M1 runs exactly one S4 per environment**: every stream in E is on that instance. Superseding is tested on one instance and **in process with two S4 instances sharing one channel object** (BR-FO-08). **Consequence (the user's)**: PF §9's *Throughput* row ("scales with total request volume") is **not demonstrated for S4 in M1**: a residual, carried to Build and Test and to the first hosted deployment with the distributed channel (§4). **Infrastructure Design adds a Compose-model assertion that each environment has exactly one S4 service and no replicas** | Q3 A, the user's consequence | The two-instance in-process test; the Compose-model assertion (Infrastructure Design); *QA enrichment* |
| NFR-ET-14 | **Availability**: S4 is stateless apart from its open streams and two caches; an instance lost loses only its streams. **E's store is the floor for new publishes and subscribes** (GAP-ET-001 work-around); within B of a store outage, open streams stay open and steps 1 to 3 answer exactly. S1's outage does not touch S4 (M1-NFR-08) | P-07; D-ET-09, 23 | `stack:outage` (S1 stopped, TC-ET-022); the store-down cases (business-logic-model §8); *QA enrichment* |

### Performance

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-ET-15 | **Reported, not gated, on the local stack**: `publish` at most **200 ms p95**; opening a stream at most **200 ms p95**; **publish to delivery** (A's request sent to B's `delivery` event read) at most **250 ms p95**. Measured at Build and Test, as U4's TC-EHA-070 and U6's TC-AC-067 | Q6 A | *QA enrichment* (Build and Test) |
| NFR-ET-16 | **The revocation read and steps 5 to 10** as their units set them: a cache hit 0.1 ms p99 in process (U6 NFR-AC-16, `pnpm bench:revocation`); steps 5 to 10 at most 2 ms p99 (U3 NFR-AE-07, `pnpm bench:admit`, TC-AE-040), both reported | U6, U3 | Their benchmarks, unchanged |

### Security

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-ET-17 | **TLS 1.3 on S4's edge**, streams included, and **`verify-full` to E's store**. **SECURITY-01 at rest: not applicable in M1** (the user's decision); S4 stores only attribution records, which hold no secret | P-08; U4 NFR-EHA-23 | U4's TLS tests at S4; *QA enrichment* |
| NFR-ET-18 | **Security events** in U4's JSON log format, under the shared-name rule: an event published, a stream opened, a stream ended with its code, a request refused with its internal reason, U3's `envelope_refused`; `store.unavailable` and `throttle.refused` shared. **Never a token, seal, envelope, payload, or trace value**; agents and instances only | P-09; D-ET-28; SECURITY-03 | The log scan over S4's tests; `monitoring.test.ts`'s overlap; *QA enrichment* |
| NFR-ET-19 | **Alert rules** in `deploy/monitoring/alerts.yaml`: bursts of ingest refusals; any stream ended `credential_refused`; repeated `overflow`; `store.unavailable`, `throttle.refused`. **Grouped by environment or code, never by agent**. SECURITY-14: not applicable in M1 (the user's decision) | P-10; D-ET-28 | The monitoring tests (U2, U4) with S4's items added; *QA enrichment* |
| NFR-ET-20 | **Per-agent publish and stream limits are not built in M1**; carried to the first hosted deployment. Residual: one agent can publish to every subscriber in E up to the throttle, and hold streams up to the cap with several lineages | P-16; D-ET-36 | Listed in §4 and §5 |

### Reliability and maintainability

| ID | Requirement | Source | Verification |
|---|---|---|---|
| NFR-ET-21 | **The store guarantees are U4's** (NFR-EHA-10): one primary, `synchronous_commit` on, success after commit; one transaction per operation; nothing pruned | P-13 | U4's store tests, unchanged |
| NFR-ET-22 | **No new dependency** (tech-stack-decisions) | P-11; SECURITY-10 | The dependency register unchanged; `pnpm audit` |
| NFR-ET-23 | **Time-based behaviour is tested with an injected clock**: `exp`, the revocation timeline against B, R, the heartbeat, the grace, the throttle's wait, shutdown | P-12 | The tests named above |
| NFR-ET-24 | **The bounds are security bounds, not tenant quotas** (I8): the step-1 limits, P, the cap, the buffer, the throttle; platform constants, not configuration | P-14 | The I8 table, re-checked at Code Generation |

## 4. Residuals (carried to Build and Test)

| Residual | Source | Carried to |
|---|---|---|
| **Pretty-printing deeply nested unknown fields can exceed the step-1 limits.** An unknown field has no nesting limit, and indentation grows with depth; NFR-ET-04's shape is what is guaranteed, and `envelope.md` recommends compact JSON. *Added at approval (the user's, 2026-11-13)*: **NFR-ET-04 assumes ASCII is unchanged, and common serializers escape some ASCII by default**: Go's `encoding/json` writes `<`, `>`, `&` as `\u003c`, `\u003e`, `\u0026` (six times the bytes), and some serializers write `/` as `\/`. A draft or payload rich in those characters, so serialized, can exceed the limits | Q2, the user's; the user's addition at approval | Build and Test |
| **PF §9's *Throughput* row is not demonstrated for S4 in M1**: exactly one S4 per environment, the channel in process | Q3, the user's | Build and Test; **the first hosted deployment, with the distributed channel** |
| **Cross-instance superseding over a real channel** is not exercised on the stack (tested in process with two instances on one channel object); a lost `supersede` leaves two streams of one lineage for at most L | D-ET-05 (Functional Design) | Build and Test; the first hosted deployment |
| **GAP-ET-001**: E's store is S4's availability floor for new operations | D-ET-09 | Build and Test (an `Open` gap) |
| Per-agent publish and stream limits not built | NFR-ET-20 | The first hosted deployment |

## 5. Obligations Carried Forward

| To | Obligation |
|---|---|
| **NFR Design** | The channel port and its in-process implementation; the stream registry, the sweep (R), the buffer accounting, the grace, shutdown; the Body Form's physical shape on `admit`; S4's role and the reverse rule's migration; the log names under the shared-name rule; the composition and no-key test; the import and closure tests |
| **Infrastructure Design** | S4 per environment (E, E2) in Compose, `127.0.0.1:8446` and `8447`; **a Compose-model assertion that each environment has exactly one S4 service and no replicas** (NFR-ET-13); **S4's container memory sized for 256 MiB of stream buffers plus its measured baseline, the number recorded** (NFR-ET-09); the seal key ring and agent verify halves; S4's role, `pg_hba`; TC-ET-022 as a `stack:outage` case; S4's README *Operations* |
| **Build and Test** | §4's residuals; NFR-ET-15's measurements |

## 6. Security Compliance at NFR Requirements

| Rule | Status |
|---|---|
| SECURITY-01 | In transit: TLS 1.3 at the edge and `verify-full` to the store (NFR-ET-17). At rest: not applicable in M1 (the user's decision); no secret stored |
| SECURITY-02, 04 | N/A: no new intermediary; no HTML |
| SECURITY-03 | Compliant, except the centralized log service (the user's M1 decision): named events, no token, seal, envelope, payload, or trace value (NFR-ET-18) |
| SECURITY-05 | Compliant: the step-1 limits, P, the closed bodies, NFR-ET-04's guarantee and its test |
| SECURITY-06 | Compliant: S4's own role (D-ET-29); its own secrets (Infrastructure Design) |
| SECURITY-07 | Compliant: a loopback edge; E's network only (Infrastructure Design) |
| SECURITY-08 | Compliant: every check at S4 from the raw request; streams re-checked |
| SECURITY-09 | Compliant: generic Problems; B not configurable; no default credential |
| SECURITY-10 | Compliant: no new dependency (NFR-ET-22) |
| SECURITY-11 | Compliant: the throttle, the cap, the buffer, the bounds; the per-agent residual stated (NFR-ET-20) |
| SECURITY-12 | Compliant: credentials verified per request and per stream; mounted secrets only |
| SECURITY-13 | Compliant: every publish and subscribe attributed before it takes effect |
| SECURITY-14 | Not applicable in M1 (the user's decision): S4's rules as files (NFR-ET-19) |
| SECURITY-15 | Compliant: fail closed on the store, unreadable revocation, the record, the hand-off; shutdown ends streams explicitly |

## 7. Invariant Compliance at NFR Requirements

| Invariant | Status |
|---|---|
| I1 | Compliant: one channel, cache space, and S4 per environment (NFR-ET-13) |
| I2 | Compliant: the bounds enforced at S4 from the raw request |
| I3 | Compliant: no requirement reads a source address or host |
| I4 | Compliant: the record before the effect; availability per GAP-ET-001's work-around |
| I5 | Compliant: no requirement adds an evaluation path |
| I6 | Compliant: PF §9's profile only; no control-face property |
| I7 | Compliant: the published bounds and the compact-JSON statement are compatible |
| I8 | Compliant: the bounds are security bounds (NFR-ET-24) |
| I9 | Compliant: the payload bound is a size, never a reading of content |
| I10 | Compliant: nothing depends on a managed runtime; one S4 per environment is a deployment fact, never an identity input |
| I11 | N/A: Construction is where technology is selected |
