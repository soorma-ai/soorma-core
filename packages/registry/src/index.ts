// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/registry (P4): grants to human principals and the human GrantSource
// (U4), the accepted-identifier set (BR-ACC); registrations and registration
// secrets join at U5.
export {
  ACCEPTED_PERMISSIONS,
  isAcceptedIdentifier,
  MAX_UNACCEPTED_POINTERS,
  unacceptedPositions,
} from './accepted.ts';
export {
  applyFirstGrant,
  asStoredSet,
  createGrant,
  createHumanGrantSource,
  type GrantedBy,
  type GrantRecord,
  type GrantSource,
} from './grants.ts';
