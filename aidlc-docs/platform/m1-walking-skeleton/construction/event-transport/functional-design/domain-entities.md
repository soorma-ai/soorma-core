# Domain Entities: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). Data face, environment level. Builds the
deployable S4 `event-ingest`, with `publish` and `subscribe`
**Built against**: PF @ `prd-platform-foundations-v1.3` (the main source), ID @ `prd-identity-v1.0`
**Rules**: [business-rules.md](business-rules.md). **Logic**: [business-logic-model.md](business-logic-model.md)

U7 adds **no stored record of its own**. A publish leaves an attribution record (U4's table) and
nothing else: events are live only (GAP-INT-003). Everything else below is a value in flight or
state held in an S4 instance's memory for the life of a stream.

Entities defined by earlier units and used here unchanged: the Envelope, Draft, Forwarded
Context, Seal, and Delivery (U1, `construction/wire-contract/functional-design/domain-entities.md`);
the Checked Agent Context and Agent Facts (U3); the Attribution Record (U4); the Agent Credential
Token and Revocation Answer (U6).

---

## Entity Map

```text
+------------------+      admit (U3)      +---------------------+
| Publish Request  |--------------------->| Stamped Envelope    |
| { draft,payload }|                      | + Seal              |
+------------------+                      +---------------------+
         |                                        |
         | one record (P7)                        | Delivery {envelope, seal, payload}
         v                                        v
+------------------+                      +---------------------+
| Attribution      |                      | Channel Message     |
| Record: publish  |                      | (delivery)          |
+------------------+                      +---------------------+
                                                  |  E's fan-out channel,
                                                  |  every S4 instance in E
                                                  v
+------------------+   admit, record      +---------------------+
| Subscribe Request|--------------------->| Stream              |
| { draft }        |                      | (one per lineage)   |
+------------------+                      +---------------------+
         |                                   |            |
         | one record (P7)                   | delivery   | end { code }
         v                                   v            v
+------------------+                      the subscriber's connection
| Attribution      |
| Record: subscribe|        Channel Message (supersede): ends an earlier
+------------------+        stream of the same lineage on any instance in E
```

*Text alternative*: a Publish Request passes U3's `admit`, which returns a Stamped Envelope and
its Seal; S4 writes one publish Attribution Record, then puts a Delivery on E's fan-out channel
as a delivery Channel Message, which reaches every S4 instance in E. A Subscribe Request passes
`admit`, S4 writes one subscribe Attribution Record, then opens a Stream. Each Stream receives
delivery messages as `delivery` events and ends with one `end` event. A supersede Channel Message
ends an earlier Stream of the same credential lineage on any instance in E.

---

## Publish Request (value)

The body of `POST /events` (D-ET-01). **Closed**: exactly two members.

| Member | Type | Required | Rule |
|---|---|---|---|
| `draft` | Draft (U1), an object | Yes | The draft, closed as U1 defines it: `clientContractVersion`, `traceContext`, `inbound` (optional) |
| `payload` | any JSON value | Yes | Opaque to the platform (I9). At most the Delivery payload bound on its JCS serialization (D-ET-27) |

The whole body is at most publish's step-1 limit (D-ET-26).

## Subscribe Request (value)

The body of `POST /subscriptions` (D-ET-01). **Closed**: exactly one member, `draft` (a Draft,
required). The whole body is at most subscribe's step-1 limit, which admits a maximum-size
forwarding draft (D-ET-26).

## Body Form (value: the option `admit` gains, D-ET-01)

What S4 tells U3's `admit` about where the draft sits and what else the body may hold. Without
it, `admit` behaves exactly as today: the body is the draft.

| Part | Publish | Subscribe |
|---|---|---|
| The draft's member | `draft` | `draft` |
| Other members, each required | `payload`, bounded on its JCS serialization by the Delivery payload bound | none |
| Any member not listed | `unknown_field` | `unknown_field` |

The physical form (a field on the request, or a construction option) is NFR Design's.

## Stamped Envelope and Seal (values, U3's)

What `admit` returns for this hop: the envelope (scope from the credential, origin, the chain
with this hop appended, a re-broadening record when load-bearing, the trace context) and the
seal over its JCS form with E's seal key ring. **For a publish they become the Delivery's
envelope and seal**. For a subscribe they are recorded in its attribution record and given to no
one (D-ET-02).

## Delivery (value, U1's, as S4 sends it)

`{ envelope, seal, payload }`: the publish's Stamped Envelope and Seal, exactly as `admit`
returned them, and the publish's payload, equal as JSON to what the publisher sent (D-ET-19). *Consistency fix from NFR Design (2026-11-13)*: **the payload's numbers exactly as written** (carried by their source text), every other value equal in value, compact (NP-ET-05).
**One Delivery per accepted publish, the same for every stream**: no stream's own hop is stamped
into it. Bounded: the envelope at most 16 KiB (JCS), the seal, the payload at most the Delivery
payload bound.

## Channel Message (value, internal to E)

What travels on E's fan-out channel between S4 instances in E (D-ET-20, D-ET-05). Never leaves
E: each environment's deployment has its own channel. Never stored, replayed, or acknowledged.

| Kind | Carries | Effect on each instance in E |
|---|---|---|
| `delivery` | One Delivery | Offered to every open stream on the instance |
| `supersede` | The lineage (`cid`), and the new stream's identity and order key | Ends that instance's open stream of the same lineage, if it is ordered before the new one, with `end` `superseded` |

The channel's technology is NFR Requirements'.

## Stream (state, per S4 instance)

One open `subscribe` response (D-ET-03 to 06, D-ET-21, 22).

| Attribute | Value |
|---|---|
| Id | Unique per instance; with the opening time, the **order key** that decides which of two streams of one lineage is later |
| Lineage | The credential's `cid`, which renewal keeps (U6 D-AC-14). **At most one open stream per lineage in E** (D-ET-05) |
| Subscriber | The Checked Agent Context: E, the logical agent, the instance, the `cid` |
| Expires at | The presented credential's `exp`, kept from verification (D-ET-22) |
| Last revocation answer | Through P5's cache, at each check (D-ET-04) |
| Send buffer | Bounded (size at NFR Requirements); full means the stream ends `overflow` (D-ET-06) |
| State | `open`, then `ended` with one end code; never reopened |

A stream's authority is evaluated once, at open (D-ET-21).

## Stream End (value)

The stream's last event, `end`, with data `{ code }` (D-ET-03). `code` is an **open string**:
a client tolerates codes it does not know.

| Code | When |
|---|---|
| `credential_expired` | The presented credential's `exp` is reached |
| `credential_refused` | Revocation at either granularity, observed through P5's cache. Never says which granularity (PF §7a: revocation state readable by no principal) |
| `unavailable` | No revocation answer younger than the bound can be had; or the S4 instance is stopping |
| `superseded` | A later stream of the same lineage opened in E |
| `overflow` | The stream's send buffer filled |

After a stream's `200`, no Problem is sent: the end event is the only way the stream says why.

## Attribution Record: `publish` and `subscribe` (record, U4's table)

One per accepted operation, written before the operation takes effect (D-ET-16, 17). U4's record
with an **agent actor and envelope facts** (D-ET-18):

| Field | Value |
|---|---|
| Operation | `publish` or `subscribe` |
| Scope | E, as configured (U4 BR-AT-06) |
| Actor | Agent: the registration (the logical agent), the instance, **the sponsor resolved from the registration in the record's own transaction**, the credential presented (`agentCredential`, its `cid`) |
| Chain | The stamped `actorChain` |
| Origin | `{ originMode, delegatingPrincipal? }` as stamped; `delegatingPrincipal` never present in M1 |
| Re-broadening | `loadBearing`, and `hop` exactly when load-bearing: **the chain's last index**, the presenter's own hop |
| Request id | The request's |
| Target | None: the namespace is E, which is the scope |

## Envelope-Bearing Agent Operations (constant, P7)

`publish`, `subscribe`. With U6's envelope-free list (`exchangeBootstrap`,
`renewAgentCredential`), **P7 closes the rule both ways** (D-ET-07): an agent record for an
operation on the envelope-free list carries no envelope facts; an agent record for any other
operation carries them.

## S4's Checked Agent Context (value)

P1's `checkAgentRequest` result, unchanged: scope, logical agent, instance, `cid`. S4's own
`verify` callback also keeps the verified token's `exp` for the request, which the stream needs
(D-ET-22); P1's shape does not change.

## Problem Codes (U1's set; one widened)

| Code | At S4 |
|---|---|
| `payload_too_large` (413) | Step 1 (a body over its operation's limit); **widened** to step 6 for a publish whose `payload` exceeds the Delivery payload bound (D-ET-27) |
| `credential_refused` (401) | Steps 2 to 4: presenter, verification, environment, revocation |
| `credential_expired` (401) | Step 3 |
| `malformed_request`, `unknown_field`, `stamped_field_set`, `unsupported_contract_version` (400) | Steps 5 and 6, on the body form (D-ET-01) |
| `invalid_inbound_context`, `chain_too_deep`, `envelope_too_large` (400) | Steps 7, 8, 10 |
| `forbidden` (403) | Step 9: O12 (and GAP-AE-001's forwarded case), or the required permission |
| `unavailable` (503) | Throttle or the open-stream cap; revocation unreadable past the bound; agent facts unreadable; the record's write (GAP-ET-001 work-around); the channel hand-off |
| `internal_error` (500) | Anything unexpected |
