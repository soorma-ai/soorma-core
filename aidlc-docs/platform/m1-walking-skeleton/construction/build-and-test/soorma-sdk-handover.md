# Handover to soorma-sdk: the M1 Wire Contract

**For**: the soorma-sdk M1 session (`soorma-sdk/aidlc-docs/harness/m1-walking-skeleton/`), which
builds PF §11's harness operations and proves *done when* 2, 3, and 5 through the SDK against a
running soorma-core.
**From**: soorma-core's M1 Build and Test, 2026-11-13.

## Pin

**`contract-v0.1.0`**: an annotated tag on soorma-core `main`, peeling to
`c1e3d7f3a71eddb0a2bce8e7d27fd736181c667d`. The contract is `contract/` at that tag (Apache 2.0),
version `0.1.0`, **pre-release** (`conventions/pre-release.md`). Build against the tag, never
against a branch.

The documents an agent-side SDK needs:

| Document | For |
|---|---|
| `contract/data-gateway.openapi.yaml` | acquire (`exchangeBootstrap`) and renew (`renewAgentCredential`) at S3 |
| `contract/event-ingest.openapi.yaml` | publish and subscribe at S4 |
| `contract/envelope.schema.json`, `contract/delivery.schema.json` | the draft, the envelope, the Delivery |
| `contract/conventions/` | credentials, the envelope and its bounds, Problems, identifiers, versioning |

S1 and S2 are human-facing: no agent operation is there.

**If the contract is insufficient**, that is not a specification gap (the contract is not the
PRD's). Raise it against the soorma-core initiative and change it there; never adapt it locally
in the SDK (the slice brief, *Order and the shared contract*).

## What the SDK must do (the contract's rules, collected)

### Credentials (`conventions/credentials.md`)

- Bootstrap with `{ agent, secret, instance }`. The secret (`soorma_rs_…`) is opaque: pass it
  through, never parse it, log it, or store it beside the credential.
- The credential (`soorma_ac_…`) is opaque. Present it as `Authorization: Bearer` in its own
  environment only.
- **Schedule renewal from the response's `expiresAt`**, and **bootstrap again when renewal
  answers `credential_expired`** at the end of the lineage. The lifetimes (15 minutes per token,
  24 hours per lineage) are **upper bounds only**: never hard-code them.
- Revocation reaches every request within **60 seconds**, the platform's propagation bound. Past
  it, a surface that cannot read revocation state answers `unavailable`.
- Instance identifiers are asserted, not verified, and may repeat: two instances asserting one
  name each hold their own credential lineage and their own stream.
- Neither bootstrap nor renewal carries an envelope.

### The draft and the envelope (`conventions/envelope.md`)

- A draft has `clientContractVersion` (required), `traceContext` (required), and `inbound`
  (optional), and nothing else: it is closed.
- **Never set a platform-stamped field** (`scope`, `originMode`, `actorChain`, and the rest of the
  envelope's stamped fields). The platform refuses the draft with `stamped_field_set` and a pointer
  to the field; it never overwrites. This is *What the SDK may not populate*.
- Populate `traceContext` (W3C `traceparent`, optional `tracestate`). The platform carries it
  unchanged; emitting the trace is the SDK's (*done when* 5).
- When a call is triggered by an event, forward its context: `inbound: { envelope, seal }`,
  **copied exactly from the Delivery**, unknown fields included. A changed envelope fails the seal
  (`invalid_inbound_context`).
- Preserve unknown envelope fields (PF FR-005): the envelope is open at every level.

### Publish and subscribe (`event-ingest.openapi.yaml`)

- **Publish**: `POST /events` with `{ draft, payload }`. **`202` with no body** means accepted for
  live delivery, and promises no delivery.
- **Subscribe**: `POST /subscriptions` with `{ draft }`. `200`, `text/event-stream`: one `delivery`
  event per Delivery accepted in the environment after the stream opened (the subscriber's own
  publishes included), heartbeats as comment lines, and **exactly one final `end` event** whose
  data is `{ code }`, unless the connection is already gone. After the 200 no Problem is sent: the
  `end` event is the only signal.
- `end` codes: `credential_expired`, `credential_refused`, `unavailable`, `superseded`, `overflow`.
  **An open set**: tolerate codes you do not know. Subscribe again to receive further events.
- **At most one stream per credential lineage**: a later subscribe supersedes the earlier stream
  (`superseded`). So, before `exp`: renew, then subscribe again with the renewed credential.
- **No resumption**: no event carries an id, and `Last-Event-ID` is ignored. **Live only**: an
  event published while a subscriber is offline, superseded, or overflowed is not delivered to it
  (GAP-INT-003, *Awaiting PRD: Event*).
- Every subscriber in an environment receives everything published in it: there are no topics.

### Bytes on the wire

- **Send compact JSON.** S4 checks each raw body first: **publish 256 KiB, subscribe 64 KiB**;
  over that, `payload_too_large`. The limits guarantee only the shape `conventions/envelope.md`
  states (a maximum-size forwarding draft and payload, even escaped and indented by 2 spaces).
  Pretty-printing deeply nested unknown fields, or ASCII escaping by a serializer (Go's
  `encoding/json` escapes `<`, `>`, `&` at six times their bytes; some escape `/` as `\/`), can
  push a body over. In Go, `json.Encoder.SetEscapeHTML(false)`. Duplicate member names keep the
  last value: do not send them.
- The payload is any JSON value, bounded at **64 KiB** on its RFC 8785 serialization; the
  envelope at **16 KiB**.
- **Payload numbers are delivered exactly as written** (their source text), and **object members
  arrive in RFC 8785 order**, not the publisher's. Do not rely on member order.

### Errors

- Problems are RFC 9457 `application/problem+json` with a `code`. **Tolerate unknown codes** and
  extra members. A `503` carries `Retry-After`; honour it.

## A known risk to handle: deeply nested payloads

S4 delivers what it accepts. A payload within the 64 KiB bound can nest about **32,000 levels**.
Common receiving parsers fail far sooner: **Python's `json` at about 1,000 levels**, and a
**TypeScript `JSON.parse` with a reviver at about 3,000** (U7 D-CG-ET-28). The SDK decides how
its receiving side bounds parse depth, and what it surfaces when a Delivery exceeds it. soorma-core
does not limit nesting below the byte bound.

## Specification gaps that touch the SDK

All are open on soorma-prd and worked around in soorma-core. The SDK builds against the
work-arounds, which are the contract at `0.1.0`:

| Gap | What the SDK sees |
|---|---|
| GAP-INT-003 (soorma-prd#13, *Awaiting PRD: Event*) | Live only; delivery semantics unspecified |
| GAP-INT-007 (#25) | Origin is always stamped at the first hop; a draft never carries it |
| GAP-INT-008 (#27) | No envelope on bootstrap or renewal |
| GAP-AE-001 (#30) | An agent that did not declare autonomy, forwarding an autonomous envelope, is denied |
| GAP-ET-001 (#31) | During a store outage S4 refuses new publishes and subscribes with `unavailable` (open streams continue) |

## Running soorma-core locally

From a soorma-core checkout at the tag: `pnpm install --frozen-lockfile`, `pnpm run build`, build
the four images (`build-instructions.md`), `pnpm stack:init`, `pnpm stack:up`. Edges on the host
loopback, TLS 1.3, trusting the stack's own CA at `deploy/local/.secrets/stack-ca.pem`:

| | `e` | `e2` |
|---|---|---|
| S1 (organization) | `127.0.0.1:8441` | (shared) |
| S2 (control) | `8442` | `8443` |
| S3 (data: bootstrap, renewal) | `8444` | `8445` |
| S4 (data: events) | `8446` | `8447` |

The human steps that precede an SDK run (first authentication, a sign-in, an environment
credential, the self-grant, registering two agents, a secret each) are shown as raw calls in
soorma-core's `e2e/agent-registration.test.ts`, TC-AR-008.
