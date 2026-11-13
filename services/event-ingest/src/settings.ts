// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4's fixed values, each from its requirement. None is configuration: a
// change is a reviewed code change. **The propagation bound is not here**:
// it is @soorma/credentials' PROPAGATION_BOUND_MS, imported where the two
// caches are built (D-ET-15; BR-BND-01, 02), never redefined.

/** Retry-After on S4's own 503s: throttle, cap, revocation, record, hand-off (NFR-ET-12). */
export const RETRY_AFTER_SECONDS = 5;
/** Requests in flight per instance, and how long one waits for a permit (NFR-ET-12). */
export const REQUEST_PERMITS = 64;
export const PERMIT_WAIT_MS = 1000;

/** Step 1's limits on the raw body (NFR-ET-03; NP-ET-04). Every other path keeps 16 KiB. */
export const PUBLISH_BODY_LIMIT = 262_144;
export const SUBSCRIBE_BODY_LIMIT = 65_536;
export const ROUTE_BODY_LIMITS: Readonly<Record<string, number>> = Object.freeze({
  '/events': PUBLISH_BODY_LIMIT,
  '/subscriptions': SUBSCRIBE_BODY_LIMIT,
});

/**
 * P, the Delivery payload bound: 64 KiB on the payload's JCS serialization,
 * each number counted by its source text (NFR-ET-02; envelope.md).
 */
export const DELIVERY_PAYLOAD_BOUND = 65_536;

/** At most this many open streams per instance (NFR-ET-08; D-ET-25). */
export const MAX_STREAMS = 256;
/** A stream's send buffer: bytes queued and not yet written to the socket (NFR-ET-08). */
export const SEND_BUFFER_BYTES = 1_048_576;
/** How long a stream that cannot take its `end` event is given before it is closed. */
export const END_GRACE_MS = 5_000;
/** R: every open stream's revocation is checked at least this often (NFR-ET-07). */
export const SWEEP_INTERVAL_MS = 1_000;
/** A heartbeat comment after this much silence on a stream (NFR-ET-07). */
export const HEARTBEAT_MS = 15_000;
/** Shutdown ends every stream and exits within this (NFR-ET-11). */
export const SHUTDOWN_MS = 5_000;
