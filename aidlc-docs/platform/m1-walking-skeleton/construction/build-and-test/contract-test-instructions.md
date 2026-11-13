# Contract Test Instructions

soorma-core owns the wire contract between an agent and the platform (the slice brief). It lives
in `contract/` (Apache 2.0), version `0.1.0`, pre-release, and is published as the annotated tag
**`contract-v0.1.0`** on `main`'s merge commit `c1e3d7f` (U1 to U7). soorma-sdk pins that tag.

## The documents

| Document | Surface |
|---|---|
| `envelope.schema.json`, `delivery.schema.json` | the envelope (stamped and asserted fields, open at every level), the draft (closed), the Delivery |
| `conventions/` | Problems (RFC 9457 with `code`), versioning and compatibility, identifiers, credentials, the shared components |
| `org-gateway.openapi.yaml` | S1, the organization level (human sign-in) |
| `control-gateway.openapi.yaml` | S2, an environment's control face (humans) |
| `data-gateway.openapi.yaml` | S3, an environment's data face: bootstrap and renewal (agents) |
| `event-ingest.openapi.yaml` | S4, an environment's data face: publish and subscribe (agents) |
| `fixtures/0.1.0/` | valid and invalid samples: the compatibility baseline |
| `CHANGELOG.md` | every change, classified compatible or breaking |

One surface document per deployable, and no document serves both faces (I6).

## Run

```bash
pnpm run check:contract     # the contract's rules, licences, meta-schema, and compatibility
pnpm run check:generated    # the generated TypeScript types match the documents
pnpm test                   # includes contract/test/ (TC-WC-001 to 041) and each surface's tests
```

The compatibility test validates every fixture of every version against the current schemas. An
earlier valid fixture that now fails is breaking; an earlier invalid fixture that now passes is a
widening. Either fails the test unless `CHANGELOG.md` classifies it (TC-WC-030, 031).

**Emission is tested where it happens.** The received Problem schema requires no field (RFC 9457:
gateways and proxies send `about:blank`), so it cannot check what soorma-core emits. Each
perimeter's tests check every Problem soorma-core sends: all five of `type`, `title`, `status`,
`code`, `instance`, with `type` = `urn:soorma:problem:{code}` and `instance` naming the response's
`Soorma-Request-Id` (U1 BR-ERR-08; U3's TC-AE-031 and each surface's tests; on the stack,
TC-AR-043 and TC-ET-040).

## Result (2026-11-13)

| Check | Result |
|---|---|
| `check:contract` | Pass |
| `check:generated` | Pass |
| `contract/test/` (TC-WC-001 to 041) | Pass (in the 1707) |
| Every emitted Problem, at each perimeter and on the stack | Pass |
| The tag: `contract-v0.1.0` peels to `c1e3d7f3a71eddb0a2bce8e7d27fd736181c667d` | Pass |

**I7 (contract compatibility)**: `0.1.0` is the first published version, so there is no earlier
published client or schema to run against it yet. The fixtures under `fixtures/0.1.0/` are that
baseline: from the next version on, the compatibility test runs every `0.1.0` fixture against the
new schemas, and any change that fails one must be classified in `CHANGELOG.md`.

The handover of the contract's behaviour to soorma-sdk is in `soorma-sdk-handover.md`.
