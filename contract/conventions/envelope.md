<!-- SPDX-License-Identifier: Apache-2.0 -->

# The Envelope

Defined in [`../envelope.schema.json`](../envelope.schema.json). Field names are camelCase.

## Envelope v1

The envelope is the identity context of an event or an agent-originated call. It has exactly
seven fields. Six are platform-stamped; one is agent-asserted.

| Field                 | Required                                                           | Set by                                                |
| --------------------- | ------------------------------------------------------------------ | ----------------------------------------------------- |
| `envelopeVersion`     | Yes. Always `1`                                                    | Platform                                              |
| `scope`               | Yes: `{ organization, project, environment }`                      | Platform, from the presented credential               |
| `originMode`          | Yes. Known values `autonomous`, `delegated`                        | Platform                                              |
| `delegatingPrincipal` | Exactly when `originMode` is `delegated`; absent when `autonomous` | Platform. No path in this version stamps it           |
| `actorChain`          | Yes: 1 to 32 entries, most recent last                             | Platform, appended per hop                            |
| `reBroadening`        | When re-broadening was load-bearing at some hop                    | Platform                                              |
| `traceContext`        | Yes                                                                | Agent-asserted, in the draft; validated for form only |

Sponsorship is not on the envelope: it is resolved from `actorChain[i].agent` through the
registration.

**The envelope is open to unknown fields at every level**: the envelope, `scope`, each actor
reference, each re-broadening record, the delegating principal reference, and `traceContext`.
A consumer preserves and forwards fields it does not know. **Enumerated values are open
strings**: an unknown `originMode` is not an error.

**The envelope carries assertions, not proof.** It is never self-authenticating, and it is never
usable to act: acting always needs the presenter's own credential.

## maxChainDepth

**`maxChainDepth` is 32 for envelope v1.** A chain that would exceed it is refused with
`chain_too_deep`, never truncated. It is not lowered within envelope v1.

## The draft

What a client sends on an envelope-bearing call. Its top level is **closed**:
`clientContractVersion` (required), `traceContext` (required), and `inbound` (optional). Any other
field is refused with `unknown_field`, except a platform-stamped field.

**A draft never sets a platform-stamped field**: `envelopeVersion`, `scope`, `originMode`,
`delegatingPrincipal`, `actorChain`, or `reBroadening`. Such a draft is **rejected, never
overwritten**, with `stamped_field_set` and a pointer to the field. **A stamped field takes
precedence over `unknown_field`**: a draft carrying both is refused with `stamped_field_set`.
**A draft never carries origin mode**: it is stamped from the registration's autonomy declaration.

`traceContext` has two definitions. **In a draft it is closed**: exactly `traceparent` and
`tracestate`. In an envelope it is open, like every envelope object.

## Forwarded context and the seal

When a call is triggered by an event, the draft carries `inbound: { envelope, seal }`, copied from
the Delivery. The wrapper is closed; **the envelope inside it is open and carried as received**.
Its unknown fields are preserved into the envelope stamped for this hop. The platform verifies
the seal before using the forwarded envelope, and requires its scope to be this environment's. A
failure of either is `invalid_inbound_context`.

**The stamped `traceContext` on a forwarded call** is the forwarded envelope's `traceContext`
without its `traceparent` and `tracestate`, so its unknown fields are kept; then the draft's
`traceparent`; then the draft's `tracestate`, **only if the draft carries one**. A forwarded
`traceparent` or `tracestate` is never carried: the trace context is this hop's assertion.

**The seal is opaque.** A client forwards it unchanged and must not treat it as proof it can
check. It proves to the platform that this environment stamped the envelope, unaltered. It does
not prove that the envelope was delivered to the forwarder, or that it is recent.

## The envelope bound

**The envelope bound is 16 KiB, measured on the envelope's RFC 8785 (JCS) serialization.** It
applies to a forwarded envelope (`inbound.envelope`) and to an envelope the platform would stamp:
the platform refuses to stamp an envelope over the bound with `envelope_too_large`, and never
truncates or drops fields to fit. So every envelope the platform stamps can be forwarded.

**A forwarded envelope over the bound is refused with `invalid_inbound_context`**, before its seal
is computed: no envelope the platform stamped can exceed it.

## Envelope-bearing operations

| Operation                    | Surface | Envelope                                                   |
| ---------------------------- | ------- | ---------------------------------------------------------- |
| Publish                      | S4      | A draft in the request                                     |
| Subscribe                    | S4      | A draft in the request; a Delivery per event on the stream |
| Bootstrap exchange           | S3      | **None**                                                   |
| Credential renewal           | S3      | **None**                                                   |
| Every direct human operation | S1, S2  | **None**                                                   |

**The bootstrap exchange and credential renewal carry no envelope.** Direct human operations
carry none either.

- An operation not listed as envelope-bearing does not accept a draft. A body field named like a
  draft field has no envelope meaning there
- A surface that adds an envelope-bearing operation adds a row here. That is a contract change,
  classified under [versioning.md](versioning.md)
- **On S4, the draft is the `draft` member of the request body** ([`../event-ingest.openapi.yaml`](../event-ingest.openapi.yaml)).
  Publish's body is `{ draft, payload }`, both required; subscribe's is `{ draft }`. Both bodies
  are closed: any other member is `unknown_field`. The body and the draft are checked together,
  at steps 5 and 6 of [errors.md](errors.md) _Check order_, with pointers from the body's root
  (`/draft/traceContext/traceparent`)

## The Delivery

Each event on a subscriber's stream is a `Delivery` ([`../delivery.schema.json`](../delivery.schema.json)):
`{ envelope, seal, payload }`, all required, open to unknown fields. The payload is any JSON
value, opaque to the platform. **The Delivery payload bound is set by the event transport unit
(U7) and published there: 64 KiB (65 536 bytes), measured on the payload's RFC 8785 (JCS)
serialization, with each number counted by its source text.** A publish whose payload exceeds
it is refused with `payload_too_large`, after the body and the draft are checked. A Delivery is
therefore at most about 81 KiB: the envelope 16 KiB, the seal, and the payload 64 KiB.

The payload is never read for meaning, and is delivered as it was published:

- **Payload numbers are delivered exactly as written.** Each number is carried by its source
  text, never rounded or re-formatted: `1.0` stays `1.0`, and `1e2` stays `1e2`
- **I-JSON numbers are not required.** A number beyond IEEE 754 double precision is accepted and
  delivered as written. A consumer that parses it into a double may lose precision
- Every other value is delivered equal in value, in compact form: whitespace and the escaping of
  strings may differ from what was sent
- **Payload strings must be well-formed Unicode.** A lone surrogate (an unpaired `\uD800` to
  `\uDFFF` escape) is refused with `malformed_request`, with a pointer to it
- **Duplicate member names keep the last value.** An object with a member name repeated is
  delivered with that member once, holding its last value. Do not send duplicates

**The request body limits on S4** are checked first, on the raw body, before any credential:
**publish 256 KiB (262 144 bytes), subscribe 64 KiB (65 536 bytes)**. Over its limit, a body is
`payload_too_large`. Both limits admit any maximum-size forwarding draft (a chain of 32 entries,
the envelope at the 16 KiB bound, the seal and the trace context at their maxima), and, for
publish, a maximum-size payload, even serialized with every non-ASCII character escaped and
indented with 2 spaces. They guarantee no more than that shape: an indented draft nested deeper
may not fit. **Clients should serialize drafts and payloads compact, without HTML-safe or other
ASCII escaping (for example Go's `json.Encoder.SetEscapeHTML(false)`)**, as RFC 8785 (JCS) and
JavaScript's `JSON.stringify` do.

## The stream

A subscribe that succeeds answers `200` with a `text/event-stream` (server-sent events), UTF-8:

- **`delivery` events**: each one's `data` is one `Delivery`, as one line of compact JSON. A
  stream receives every Delivery accepted in its environment **after it opened**, the
  subscriber's own publishes included. Nothing earlier, and nothing from another environment
- **Heartbeats** are comment lines (`:`), at least every 15 seconds without another event.
  They carry nothing
- **Exactly one `end` event**, last, unless the connection is already gone. Its `data` is
  `{ code }` (`StreamEnd`). **The codes are an open set**: `credential_expired` (the stream's
  credential expired), `credential_refused` (it, or its agent, was revoked), `unavailable` (the
  platform cannot check revocation, or is stopping), `superseded` (a later subscribe of the same
  credential lineage opened a stream), and `overflow` (the stream fell too far behind). After
  the `200` no Problem is sent: the `end` event is the only signal
- **A stream ends at its credential's expiry.** It is never renewed in place: renew the
  credential, and subscribe again before it expires
- **At most one stream is open per credential lineage**: a later subscribe with the same
  credential, or one renewed from it, supersedes the earlier stream. Subscribe once per
  instance
- **A stream is not resumable.** No event carries an `id`, and a `Last-Event-ID` header is
  ignored. A Delivery accepted while no stream was open is not delivered later: subscribe again
  to receive events from then on

## Rules checked in code

A schema cannot express these. The receiving unit checks them in code, and the schema's own
checks do not replace them:

| Rule                                                        | Where it applies                               |
| ----------------------------------------------------------- | ---------------------------------------------- |
| Each `hop` in `reBroadening` is an index into `actorChain`  | Envelope                                       |
| No `hop` appears twice in `reBroadening`                    | Envelope                                       |
| A `traceparent` version of `ff` is invalid                  | Draft                                          |
| An all-zero trace id is invalid                             | Draft                                          |
| An all-zero parent id is invalid                            | Draft                                          |
| `tracestate` has at most 32 list members                    | Draft                                          |
| Each `tracestate` key follows W3C key syntax                | Draft                                          |
| The envelope bound: 16 KiB on the JCS serialization         | `inbound.envelope`; the envelope to be stamped |
| The Delivery payload bound: 64 KiB on the JCS serialization | A publish's `payload`                          |
| Payload strings are well-formed Unicode                     | A publish's `payload`                          |

**Trace context is validated for form only.** The platform never interprets the values, and
emits no spans.
