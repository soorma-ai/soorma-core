// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2's fixed values, each from its requirement. None is configuration: a
// change is a reviewed code change.

/** A human environment credential's lifetime, capped at the sign-in's (NFR-EHA-01). */
export const CREDENTIAL_LIFETIME_MS = 15 * 60_000;
/** The sign-in token check's tolerance at an environment (NFR-EHA-03; U2 F-2). */
export const SIGN_IN_TOLERANCE = Object.freeze({ expSeconds: 30, iatAheadSeconds: 30 });
/** Retry-After on every 503 S2 answers (NFR-EHA-04, 05, 07). */
export const RETRY_AFTER_SECONDS = 5;
/** Requests in flight per instance, and how long one waits for a permit (NFR-EHA-04). */
export const REQUEST_PERMITS = 64;
/** Calls to S1 in flight per instance (NFR-EHA-05). */
export const S1_CALL_PERMITS = 8;
export const PERMIT_WAIT_MS = 1000;
/** One attempt per call to S1, within this deadline (NFR-EHA-07). */
export const S1_DEADLINE_MS = 2000;
/** The largest answer S2 reads from S1 (NP-EHA-04). */
export const S1_RESPONSE_CAP_BYTES = 64 * 1024;
/** The verify keys' scheduled refresh, and the on-demand fetch limit (NFR-EHA-08). */
export const KEY_REFRESH_MS = 5 * 60_000;
export const KEY_REFETCH_LIMIT_MS = 30_000;
/** The permissions configuration grants E's first Admin (BR-FG-01). */
export const FIRST_ADMIN_PERMISSIONS: readonly string[] = Object.freeze([
  'grant:human',
  'human:manage',
]);
