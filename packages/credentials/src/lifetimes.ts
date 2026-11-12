// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The three numbers of the data face (U6 NFR-AC-01 to 04; NFR Design NP-AC-01),
// as code constants, never deployment configuration: PF FR-012 makes the
// propagation bound "platform-set and not tenant-configurable", and rejects
// "a tenant-configurable bound — relocates a safety property into
// configuration". soorma-core is self-hosted, and the team running a
// deployment is typically the tenant (PF §6, Deployment Note).
//
// The contract publishes B as the platform's bound and L and M as upper bounds
// only (credentials.md, Revocation and Lifetimes); a docs test ties the
// published values to these constants (TC-AC-038).

/**
 * B, the propagation bound: a not-revoked answer is served for at most this
 * long from its read's issue, and past it, with revocation state unreadable, a
 * request is denied. The one value: P5's revocation cache and U3's term cache
 * (passed by U7) both read it; no second TTL exists.
 */
export const PROPAGATION_BOUND_MS = 60_000;

/** L, the agent credential's lifetime: a token's exp is at most this long after its iat. */
export const AGENT_CREDENTIAL_LIFETIME_MS = 15 * 60_000;

/** M, a lineage's maximum age: no token of a lineage expires later than its start plus this. */
export const LINEAGE_MAX_AGE_MS = 24 * 60 * 60_000;
