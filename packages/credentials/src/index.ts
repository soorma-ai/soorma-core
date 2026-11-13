// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/credentials (P5): an environment's own credentials, minted and
// verified with its own key ring only (ID §6; PF §6), and their records. U4
// builds the human environment credential; U6 adds the agent credential, its
// own key ring's use (D-AC-03), revocation reads and the fail-closed cache,
// and the three constants B, L, M (NP-AC-01).
export {
  loadEnvironmentKeyRing,
  loadVerifyKeyRing,
  type EnvironmentKeyRing,
  type VerifyKeyRing,
} from './key-ring.ts';
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
export {
  AGENT_CREDENTIAL_LIFETIME_MS,
  LINEAGE_MAX_AGE_MS,
  PROPAGATION_BOUND_MS,
} from './lifetimes.ts';
export {
  AGENT_CREDENTIAL_PREFIX,
  AGENT_CREDENTIAL_TYP,
  mintAgentCredential,
  verifyAgentCredential,
  type AgentCredentialClaims,
  type AgentTokenVerification,
} from './agent-token.ts';
export {
  insertAgentCredential,
  lineageTimes,
  readAgentCredential,
  renewAgentCredentialRecord,
  renewedExpiry,
  wholeSeconds,
  type AgentCredentialRecord,
} from './agent-records.ts';
export {
  createRevocationCache,
  directRevocationSource,
  type RevocationAnswer,
  type RevocationCacheOptions,
  type RevocationSource,
  type RevocationTarget,
} from './revocation.ts';
