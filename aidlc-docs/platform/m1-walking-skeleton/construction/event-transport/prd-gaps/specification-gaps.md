# Specification Gaps: U7 `event-transport`

Gaps found while building U7 (soorma-core#10), classified with `prd-gap-classification.md`.
The register of every gap in this initiative is in `aidlc-state.md`, *PRD Specification
Gaps*. Intake-time gaps are in `inception/prd-intake/specification-gaps.md`.

| ID | Status | Raised against | Resolved by | Issue |
|---|---|---|---|---|
| [GAP-ET-001](#gap-et-001-may-attribution-recording-make-the-store-the-data-faces-availability-floor) | **Open**; worked around in M1 (a synchronous record, fail closed) | PF @ `prd-platform-foundations-v1.3` | — | [soorma-prd#31](https://github.com/soorma-ai/soorma-prd/issues/31) (open) |

---

## GAP-ET-001: May attribution recording make the store the data face's availability floor

**Raised**: 2026-11-12T23:11:09Z
**Stage**: Functional Design, U7 `event-transport` (plan Q9, classified as specification by the
user)
**Raised against**: PF, soorma-prd/aiprd-docs/platform-foundations/requirements/prd.md @ `prd-platform-foundations-v1.3`
**PRD section**: PF §9 *NFR Profile*, the *Availability* row and the *Revocation propagation
bound* row; PF §20 *Decision Log*, row 12 (OQ-12); PF FR-025
**Owner**: platform-foundations
**Unit**: U7 (publish and subscribe at S4, event ingest)
**Issue**: [soorma-prd#31](https://github.com/soorma-ai/soorma-prd/issues/31), opened 2026-11-12 with this entry verbatim, pinned to `b05931e`
**Resolved by**: —

### What the build needs

Every publish and every subscribe is a platform-resource operation (PF §8a), so each produces
an attribution record (FR-025). The perimeter can authorize a publish during a store outage:
O3 is served from the revocation cache for up to the propagation bound (FR-012), and the
agent facts behind authority are cached for the same bound. Whether the publish then
**proceeds** depends on where and when its record is written. The build needs to know whether
the record may be a synchronous write to a store whose outage then refuses the operation, or
whether the data face must keep operating through an outage within the bound, which
requires the record to be decoupled from that store.

In M1, the attribution record and revocation state live in the same per-environment store
(a technology choice made at U4). With a synchronous record, a store outage makes publish and
subscribe `unavailable` at once, while both caches would still authorize them.

### What the PRD says

- PF §9 *NFR Profile*, **Availability**: "High, but **bounded by the cache rather than
  absolute** — the revocation store is not the availability floor for the environment".
  Rationale: "Caching within the propagation bound decouples per-request authorization from
  store availability"
- PF §9 *NFR Profile*, **Revocation propagation bound**: "The bound *is* the cache TTL: one
  number that is simultaneously the window in which a revoked agent may still act and **the
  outage window during which authorization continues**"
- PF §20 *Decision Log*, row 12 (OQ-12): "Revocation state **cached with a platform-set TTL,
  then fail closed**; the TTL *is* the published propagation bound". Alternatives rejected
  include "**No cache (store becomes the availability floor)**"
- PF FR-025: "Every platform-resource operation produces an attribution record". It says
  nothing about when the record is written, where, or the operation's availability

### Why this is specification, not technology

Two competent engineers can read these sections differently, and each reading changes
observable behaviour at the edge during an outage.

- **Reading 1**: §9 and OQ-12 constrain only the **revocation read**. They say that reading
  revocation state must not make the store the floor; they say nothing about recording. A
  synchronous record that refuses the operation during an outage is then correct, and the
  environment's store is the data face's availability floor for every operation that records.
- **Reading 2**: §9 states the data face's availability: "the outage window during which
  authorization continues" and the rejection of "store becomes the availability floor" mean
  an authorized publish keeps working through a store outage of up to the bound. Under a
  synchronous record in that store, the sentence means nothing for the data face, because
  every authorization-bearing data-face operation also records. Attribution must then be
  decoupled from the store's availability.

The answer is the availability guarantee of the data face during an outage: which component
is the floor. That is a property the PRD's NFR profile owns, not a choice of storage
technology. Satisfying reading 2 also requires deciding what happens to records written
during an outage, which bears on I4 (attribution recoverable).

### Options considered

1. **The store is the data face's availability floor for recording operations.** The record is
   written synchronously and the operation fails closed when it cannot be. §9's Availability
   row is read as the revocation read only, and the PRD would say so, for example in §9 or
   FR-025: "an operation whose attribution record cannot be written is refused". Simple, and
   I4 holds by construction. Cost: during an outage the caches still authorize, but nothing
   proceeds.
2. **Attribution decoupled from the store's availability**, for example **buffered**: the
   record is written durably somewhere the outage does not reach (a per-instance durable buffer,
   or a separate store) and reconciled into the environment's record afterwards. An authorized
   operation proceeds through an outage within the bound. The PRD would need to state what a
   decoupled record must preserve: durability before the operation is acknowledged, the order
   of records, and that a record is never lost in a crash (I4). Cost: state in a stateless
   deployable, and a reconciliation path.

AI-DLC's working reading for M1 is option 1, as a **work-around**, not a decision (below).

### Blocked

Nothing is blocked. U7 is built under option D (work around): **the record is written
synchronously in E's store, in the operation's own transaction, and the operation is
`unavailable` (503, `Retry-After`) when it cannot be** (U7 business-rules D-ET-09).

**Residual, carried to Build and Test**: in M1, E's store is S4's availability floor for new
publishes and subscribes. During a store outage the revocation and agent-facts caches keep
answering for up to `PROPAGATION_BOUND_MS`, so open streams stay open and a malformed or
foreign credential is still refused exactly, but no new publish or subscribe proceeds. If the
PRD chooses option 2, U7's record path changes; the contract's codes do not.

**Status**: Open
