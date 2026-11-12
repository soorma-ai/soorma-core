// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/registry (P4): grants to human principals and the human GrantSource
// (U4), the accepted-identifier set (BR-ACC); registrations and registration
// secrets (U5): the secret's format and verifier, shared with U6's bootstrap.
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
export {
  digestRegistrationSecret,
  generateRegistrationSecret,
  parseRegistrationSecret,
  REGISTRATION_SECRET_MAX_LENGTH,
  REGISTRATION_SECRET_PREFIX,
  registrationLockKey,
  registrationSecretMatches,
  type GeneratedRegistrationSecret,
  type ParsedRegistrationSecret,
} from './registration-secret.ts';
export {
  agentFactsFromStore,
  findRegistration,
  insertRegistration,
  insertSecretUnderCap,
  MAX_ACTIVE_SECRETS,
  registrationForBootstrap,
  type RegistrationRecord,
  type RegistrationWrite,
  type SecretRecord,
  type SecretWrite,
  type StoredAgentFacts,
  type StoredAgentFactsSource,
} from './registrations.ts';
