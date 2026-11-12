// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3's fixed values, each from its requirement. None is configuration: a
// change is a reviewed code change. The propagation bound and the two
// lifetimes are @soorma/credentials' constants (NP-AC-01), never repeated here.

/** Retry-After on every 503 S3 answers (U4 NFR-EHA-04, as S2). */
export const RETRY_AFTER_SECONDS = 5;
/** Requests in flight per instance, and how long one waits for a permit (as S2). */
export const REQUEST_PERMITS = 64;
export const PERMIT_WAIT_MS = 1000;
