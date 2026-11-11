// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/credentials (P5): an environment's own credentials, minted and
// verified with its own key ring only (ID §6; PF §6), and their records. U4
// builds the human environment credential; U6 adds the agent credential.
export { loadEnvironmentKeyRing, type EnvironmentKeyRing } from './key-ring.ts';
export {
  checkCredentialRecord,
  endCredential,
  insertCredential,
  readCredential,
  renewCredential,
  type CredentialRecord,
  type O3Result,
} from './records.ts';
export {
  ENVIRONMENT_CREDENTIAL_PREFIX,
  ENVIRONMENT_CREDENTIAL_TYP,
  IAT_AHEAD_SECONDS,
  mintEnvironmentCredential,
  verifyEnvironmentCredential,
  type CredentialClaims,
  type TokenRefusalReason,
  type TokenVerification,
} from './token.ts';
