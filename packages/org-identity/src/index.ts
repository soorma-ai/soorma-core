// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/org-identity (P10): human principals, material, sign-ins, keys, tokens,
// TOTP, the K policy, and the org store.
export { CLOCK, systemClock, type Clock } from './clock.ts';
export {
  Lifetimes,
  PENDING_SECOND_FACTOR_LIFETIME_MS,
  SIGN_IN_ABSOLUTE_MAXIMUM_MS,
  SIGN_IN_LIFETIME_MS,
} from './lifetimes.ts';
