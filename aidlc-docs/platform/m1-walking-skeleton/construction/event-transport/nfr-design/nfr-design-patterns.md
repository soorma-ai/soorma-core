# NFR Design Patterns: U7 `event-transport`

**Unit**: U7 `event-transport` (soorma-core#10). S4 `event-ingest`, environment E, data face
**Decisions from**: the NFR Design plan, Q1 to Q4 and P-01 to P-18, answered
2026-11-13T00:39:18Z (recorded verbatim in `audit.md`): Q1 A, Q2 A, Q3 A; **Q4 X, the user's
design: payload numbers delivered exactly, nothing refused for precision** (NP-ET-05); P-01 to
P-18 accepted, P-14's thresholds included
**Requirements**: [../nfr-requirements/nfr-requirements.md](../nfr-requirements/nfr-requirements.md)
(NFR-ET-01 to 24). **Functional Design**: [../functional-design/](../functional-design/)
(D-ET-01 to 36). **Components**: [logical-components.md](logical-components.md)

**Checked before generating** (the user's condition on Q4): `JSON.rawJSON`, `JSON.isRawJSON`,
and the reviver's source-text `context` work in **S4's runtime path**: in the pinned runtime
image (`gcr.io/distroless/nodejs26-debian13`, Node v26.13.0, the digest S3 uses), parsing
`{"id":12345678901234567890,"d":0.10000000000000000555,"e":1E+400,"x":-0}` with the reviver and
stringifying it returned the text unchanged; the raw values are frozen, null-prototype, and
`JSON.isRawJSON` is true. **The TypeScript libraries do not declare them**: TypeScript 6.0.3's
`JSON.parse` reviver takes two arguments and no lib declares `rawJSON`, and neither does
`@types/node` 26.6.6. NP-ET-05 declares them once, in `packages/jcs`, and S4 checks them at
start-up; nothing falls back.

---

## Patterns

| ID | Pattern | Serves | Verification |
|---|---|---|---|
| NP-ET-01 | **The workspace** `services/event-ingest` (FSL-1.1-ALv2), laid out as S3: `main.ts`, `runtime.ts`, `apps.ts`, `edge/` (handlers, module), `stream/` (registry, stream writer, sweep), `channel/` (port, in-process), `security-log.ts`, `settings.ts`, `throttle.ts`. Configuration through P9's new `loadEventIngest` (an `eventIngest` part per environment in `tenancy.yaml`: edge, health, database, verify keys, seal keys) | D-ET-30; NFR-ET-22 | The closure test; the configuration tests |
| NP-ET-02 | **The composition, once, with injected factories**: `assembleRuntime` builds the revocation cache, the facts cache, the entry point, the channel, and the registry, taking `createRevocationCache` and `createCachingAgentFacts` as parameters with those defaults. **Composition test**: recording factories, both receive `ttl === PROPAGATION_BOUND_MS` (imported from `@soorma/credentials`); with the injected clock, a `not_revoked` answer is re-read at exactly 60 s. **No-key test**: `tenancy.schema.json` and `loadEventIngest`'s settings hold no key matching `/bound\|ttl\|propagation/i` | D-ET-15; NFR-ET-01; BR-BND-03 | The two tests |
| NP-ET-03 | **The import allowlist** (*BR-EP-03 made precise*): from `@soorma/authority`, only `createEnvelopeAdmission` and `createCachingAgentFacts` (U3 NP-04) and types; from `@soorma/envelope`, only `loadSealKeyRing` (U3 NP-02) and types. A test over S4's import declarations and its built output refuses anything else of P2 or P3 | D-ET-13; I5 | The import test |
| NP-ET-04 | **Body limits per route** (Q1 A): service-kit's `createAdapter` gains an optional map of route limits, applied as each route registers; S4 passes `{ '/events': 262 144, '/subscriptions': 65 536 }`; every other path keeps 16 KiB. Fastify refuses a larger body before the handler (step 1), as today. Without the option nothing changes: **service-kit's tests unchanged**, new tests for the option | NFR-ET-03; D-ET-26 | Both edges at both routes; NFR-ET-04's shape (P-15's test) |
| NP-ET-05 | **The parse step** (Q4, the user's design; detail below): the body is parsed twice from one decoded text; the draft exactly as today, the payload with **every number carried by its source text** (`JSON.rawJSON`). The payload bound is measured on `packages/jcs`'s canonical form **with numbers counted by their source text**. A payload string with a lone surrogate is `malformed_request` with a pointer. Delivered: numbers as written, every other value equal, compact | D-ET-27; NFR-ET-02; I9 | The four tests below |
| NP-ET-06 | **The Body Form on each request** (Q2 A): `EnvelopeRequest.bodyForm?: { draft: 'draft'; members: readonly { name: string; maxJcsBytes?: number }[] }`. Absent: today's behaviour. Present: step 5 refuses a non-object body (`""`) and a missing or non-object draft member (`/draft`), then reads the version there; step 6 judges the members with the draft's schema under BR-DV's precedence, pointers from the root; then each member's bound, measured as NP-ET-05. **Every U3 test unchanged**; new tests in `packages/authority` for both forms and every case of BR-BF-03 to 05 | D-ET-01; BR-BF-07 | U3's suite unchanged; the new tests |
| NP-ET-07 | **A verify-only key ring in P5**: `VerifyKeyRing` (`kids`, `verifyKey`), which `EnvironmentKeyRing` already satisfies; `verifyAgentCredential` takes a `VerifyKeyRing` (a wider parameter: every caller and test unchanged); `loadVerifyKeyRing` reads SPKI public PEMs, refusing a repeated `kid`, an empty list, or a non-Ed25519 key. S4's `verify` callback wraps it and keeps the verified `exp` for the request; P1's context is unchanged | D-ET-12, 22, 30 | New P5 tests; U4's and U6's unchanged |
| NP-ET-08 | **The channel port and the in-process channel**: `publish(message)`, `subscribe(handler) → unsubscribe`; messages `{ kind: 'delivery', frame }` or `{ kind: 'supersede', cid, order }`; the in-process channel calls every handler of the same object, in order. One per S4 process, so one per environment (NFR-ET-13). **The two-instance test** builds two runtimes over one channel object | NFR-ET-13; D-ET-05, 20 | The single-instance and two-instance supersede tests |
| NP-ET-09 | **The stream registry**: streams by id; `cid` to its open stream; the order key `(openedAt ms from the clock, id of 128 CSPRNG bits)`, compared as a pair; register, then supersede locally and by message; the open-stream cap as a counter (a same-`cid` stream on this instance not counting) | D-ET-05, 25; BR-FO-04, 05 | Supersede, race, and cap tests |
| NP-ET-10 | **The stream writer**: after the record, the handler takes over the raw reply, writes status and headers itself (`200`, `text/event-stream; charset=utf-8`, `Cache-Control: no-store`, `Soorma-Contract-Version`, `Soorma-Request-Id`), sets the socket's idle timeout to 0, and releases its throttle permit (the release-once guard covers later hooks). Per stream, **a serial chain**: each delivery checked (expiry; revocation through the cache), then written. **Buffer accounting**: bytes handed to the socket and not yet drained; past 1 MiB, `end` `overflow`; an `end` that cannot be written closes the socket after 5 s | NFR-ET-08, 10, 12; D-ET-06 | Overflow, grace, ordering, and header tests |
| NP-ET-11 | **One frame per publish**: the Delivery's SSE frame (`event: delivery\ndata: <compact JSON>\n\n`) is serialized once and the same string offered to every stream | NFR-ET-02, 08 | A frame-identity test |
| NP-ET-12 | **Injected time**: service-kit's `Clock` and a scheduler (`setTimeout`, `setInterval`, cancel) replaced by a manual one in tests. Each stream's `exp` timer and heartbeat (15 s, re-armed by every write); **one sweep per instance every 1 s**; the grace; shutdown | NFR-ET-07, 11, 23 | The timeline tests (revocation + B, expiry, heartbeat) |
| NP-ET-13 | **Throttle**: S3's module (64 permits, a 1 s wait, the release-once guard), plus the explicit release at stream open; the cap's refusal is `throttle.refused` with code `streams` | NFR-ET-12; D-ET-25 | U4's 64-abort shape at S4; a stream holding no permit |
| NP-ET-14 | **The record path**: one transaction: the sponsor statement (`SELECT sponsor FROM registrations WHERE` E's columns `AND agent = $4`), then P7's `recordAttribution`. **P7** gains `ENVELOPE_BEARING_AGENT_OPERATIONS` (`publish`, `subscribe`) and the reverse rule in `checkRecord`. **Migrations**: `0005_attribution_envelope_bearing.sql` (the CHECK `actor_kind <> 'agent' OR operation IN ('exchangeBootstrap', 'renewAgentCredential') OR chain IS NOT NULL`, alone) and `0006_event_ingest_role.sql` (S4's grants). TC-EHA-068's list gains both (class 1). **U5's constructed record**: the approved class-3 change, exactly | D-ET-07, 18, 29 | P7 tests both ways; the CHECK refuses as the writer does; TC-EHA-068 |
| NP-ET-15 | **S4's role `soorma_env_ingest`** (Q3 A): **column-level `SELECT`** on `registrations` (`organization`, `project`, `environment`, `agent`, `autonomy_declared`, `re_broadening_declaration`, `standing_permissions`, `sponsor`); `SELECT` on `credential_revocations` and `agent_revocations`; `INSERT` on `attribution_records`; nothing else. **The privilege test** runs U5's agent-facts statement, the sponsor statement, P5's revocation statement, and P7's insert as the role (they succeed), and refuses a `SELECT` of `ceiling_snapshot`, any `UPDATE` or `DELETE`, and any read of `grants`, `credentials`, `agent_credentials`, or secrets. The role itself in `env-roles.sql` (Infrastructure Design) | D-ET-29; SECURITY-06 | The privilege test |
| NP-ET-16 | **Security events** (`security-log.ts`, U4's JSON format): `event.published`, `stream.opened`, `stream.ended` (code: `credential_expired`, `superseded`, `unavailable` at shutdown, or the client gone), `stream.revoked`, `stream.overflow`, `ingest.refused` (steps 1 to 4 and the body form, with the internal reason), `envelope.refused` (U3's port), and the shared `store.unavailable`, `throttle.refused`. **The overlap with S1 to S3 is exactly `store.unavailable` and `throttle.refused`**, pinned in `monitoring.test.ts`. **Alert rules**: `stream.revoked` at 1, by environment; `stream.overflow` at 5 in 5 minutes, by environment; `ingest.refused` and `envelope.refused` at 20 in 5 minutes, by code; the shared rules unchanged; none by agent | NFR-ET-18, 19 | The monitoring tests with S4's items added (class 1); the log scan |
| NP-ET-17 | **Shutdown**: `stop()` closes the edge to new requests, ends every stream with `end` `unavailable`, waits up to 5 s for the sockets, then closes the store | NFR-ET-11 | Injected-scheduler test |
| NP-ET-18 | **Closure and image**: S4's production closure excludes `@soorma/org-identity`; the image's installed-packages check finds no `org-identity`, no seeding path, no test fixture; the contract's generated types for `event-ingest.openapi.yaml`; `e2e/event-transport-support.ts` (raw HTTPS publish and subscribe, an SSE reader of `delivery` and `end`, seeding helpers for U7's own file only) | D-ET-23, 32, 33, 34 | The closure test; CI's image steps |

---

## NP-ET-05 in Detail: The Parse Step and the Payload's Numbers

The user's design (Q4 X). **The payload is never read for meaning.** It is parsed only to check
that it is well-formed JSON and within its bound, and its numbers are never converted.

### Where it runs

| Step | What happens |
|---|---|
| 1 | Fastify refuses a raw body over the route's limit (NP-ET-04). The body is kept as bytes |
| 2 to 4 | Credentials; the body is not read |
| **5, S4's part** | The bytes are decoded as UTF-8 once into `text`. **Parse 1**: `JSON.parse(text)`; a failure is `malformed_request`, pointer `""` (BR-BF-03, "the body is not a JSON object"). **Parse 2, publish only**: `parseRawNumbers(text)` (below); its `payload` member replaces parse 1's. The draft is parse 1's, exactly as every other envelope-bearing body is parsed today |
| 5 to 10, `admit` | The Body Form (NP-ET-06): version, schema, then the payload's bound measured as below |
| Delivery | `JSON.stringify({ envelope, seal, payload })` once (NP-ET-11): raw numbers are written as their source text; everything else compact |

Two parses of one text keep the draft's path identical to U3's, so the envelope, the seal, and
JCS over the envelope are untouched by raw numbers. A body up to 256 KiB is parsed twice; the
cost is linear and bounded by step 1.

### `parseRawNumbers` (in `packages/jcs`)

```text
parseRawNumbers(text) =
  JSON.parse(text, (key, value, context) =>
    typeof value === 'number' ? JSON.rawJSON(context.source) : value)
```

- **Every number** in the parsed value becomes a raw JSON value holding its exact source text:
  `12345678901234567890`, `0.10000000000000000555`, `1E+400`, and `-0` survive as written
- **Strings, booleans, null, arrays, objects** are JSON's parse: equal in value. A string keeps
  its code units, a lone surrogate included (refused at the bound, below)
- **Duplicate member names**: the last value is kept (JSON's parse). The contract says so
- **Types**: TypeScript does not declare `JSON.rawJSON`, `JSON.isRawJSON`, or the reviver's
  `context`. `packages/jcs` declares them once (`raw-json.ts`: a `RawJsonNumber` type, typed
  `rawJSON`, `isRawJSON`, and the three-argument reviver) and every other module uses those
  exports. A type declaration, not a substitute: nothing implements them in JavaScript
- **Start-up check**: S4 refuses to start (a `ConfigurationError`, the reason logged) unless
  `JSON.rawJSON` and `JSON.isRawJSON` exist and `JSON.stringify(parseRawNumbers('[12345678901234567890]'))`
  returns `[12345678901234567890]`. **No fallback**: a runtime without them does not run S4

### How `packages/jcs` measures the payload

**Decision (the user asked for it to be decided and recorded)**: `canonicalize` gains one option,
`{ numbers: 'source' }`. **Default (`'value'`) is unchanged**: a raw JSON value is not a plain
object, so it is refused as today, and the envelope, the seal, and every existing caller and
test behave exactly as before. With `'source'`:

| Value | Written as |
|---|---|
| A raw JSON value (`JSON.isRawJSON`) whose text matches the JSON number grammar | **Its source text, unchanged** (no `Number.prototype.toString`, no `-0` to `0`) |
| A raw JSON value whose text is anything else | Refused (`CanonicalizationError`): only `parseRawNumbers` makes them, and only for numbers |
| A plain JavaScript number (none occurs in a parse-2 payload) | Refused in this mode: the payload's numbers are always raw |
| Strings, booleans, null, arrays, objects | As RFC 8785 (keys sorted by UTF-16 code units; strings escaped as `JSON.stringify` does; a lone surrogate refused) |

So **the bound is the payload's JCS form with each number counted by its source text**: what
the subscriber receives, minus whitespace and with keys sorted. `CanonicalizationError` gains a
`pointer` (the JSON Pointer of the offending value, which the iterative frames already know),
additive; the Body Form reports it from the member's root (`/payload/...`). The `numbers` option
is used only by the Body Form's member bound.

### Refusals and deliveries

| Payload | Result |
|---|---|
| `{ "id": 12345678901234567890 }` | Accepted; delivered `{"id":12345678901234567890}` |
| `[0.10000000000000000555, 6.02214076e23, 1E+400, -0]` | Accepted; delivered exactly as written, compact |
| `{ "a": "\ud800" }` | **`malformed_request`**, pointer `/payload/a` (a lone surrogate has no JCS form) |
| A payload whose source-text JCS form is 65 536 bytes, holding a 60 000-digit number | Accepted; one byte more is `payload_too_large` |
| `{ "k": 1, "k": 2 }` | Accepted; delivered `{"k":2}` |

### Tests (the user's four, and the start-up check)

1. **An integer above 2^53** (`12345678901234567890`) published and delivered unchanged, in
   process and on the stack
2. **A long decimal and an exponent form** (`0.10000000000000000555`, `6.02214076e23`)
   delivered exactly as written
3. **A lone surrogate** refused, `malformed_request`, pointer `/payload/...`
4. **The bound measured with a large number at the limit**: a payload whose source-text JCS form
   is exactly P (a long number making up most of it) accepted; one byte more refused
5. `packages/jcs`: the `'source'` mode's table above; the default mode unchanged (U3's suite)
6. S4's start-up check refuses a runtime without `JSON.rawJSON` (a stubbed global)

### I9

**The I9 row stays "never inspected beyond its bound and its JSON well-formedness"**: parse 2
finds well-formedness (and a lone surrogate, which has no JSON text form under JCS), the bound
counts bytes, and no number is ever converted or compared.

### The contract

`envelope.md` *The Delivery*: **payload numbers are delivered as written**; payloads need not
use I-JSON numbers; a payload string must be well-formed Unicode (a lone surrogate is refused);
**duplicate member names keep the last value**; the bound is measured on the payload's canonical
form with each number counted by its source text.

---

## Consistency Fixes Made Here

Marked in place, *Consistency fix from NFR Design (2026-11-13)*:
- Functional Design business-rules: BR-EP-03 (the allowlist, NP-ET-03); BR-BF-06 (numbers by
  source text, NP-ET-05); §14 (the contract's payload statements)
- Functional Design domain-entities: *Delivery* (numbers as written)
- Functional Design invariant-coverage-matrix: I9 (the row's wording)
- NFR Requirements: NFR-ET-02 (how P is measured)

---

## Test Cases (assigned at QA construction enrichment, 2026-11-13)

`inception/test-cases/event-transport/`:

| Pattern | Test cases |
|---|---|
| NP-ET-01 | TC-ET-083 (closure), TC-ET-089 (configuration) |
| NP-ET-02 | TC-ET-030 |
| NP-ET-03 | TC-ET-043 |
| NP-ET-04 | TC-ET-050, TC-ET-070 |
| NP-ET-05 | TC-ET-071, 072, 073, 049 (the user's four), TC-ET-074, 075, 076, 047 |
| NP-ET-06 | TC-ET-077, TC-ET-025 |
| NP-ET-07 | TC-ET-078 |
| NP-ET-08 | TC-ET-062, TC-ET-039 |
| NP-ET-09 | TC-ET-055, 062, 063, 064 |
| NP-ET-10 | TC-ET-079, 056, 057 |
| NP-ET-11 | TC-ET-080 |
| NP-ET-12 | TC-ET-054, TC-ET-016, TC-ET-017 |
| NP-ET-13 | TC-ET-061, TC-ET-055 |
| NP-ET-14 | TC-ET-042, TC-ET-081, TC-ET-034 |
| NP-ET-15 | TC-ET-082 |
| NP-ET-16 | TC-ET-069, TC-ET-068 |
| NP-ET-17 | TC-ET-060 |
| NP-ET-18 | TC-ET-083, TC-ET-085 (the e2e helpers through the smoke and journey) |
