// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/service-kit: the organization-neutral runtime that the organization
// level (S1) and each environment's services share (U4 NFR Design NP-EHA-15).
// Moved, unchanged, from @soorma/org-identity, @soorma/perimeter, and S1, so
// an environment's service never links the organization level's code.
export { CLOCK, systemClock, type Clock } from './clock.ts';
export { KeyMaterialError, UnavailableError } from './errors.ts';
export {
  canonicalJson,
  referenceJson,
  type Canonical,
  type PrincipalReference,
} from './crypto/canonical.ts';
export {
  bodyHash,
  INTERNAL_LEEWAY_SECONDS,
  INTERNAL_MAX_LIFETIME_SECONDS,
  INTERNAL_TYP,
  internalAudience,
  signInternalRequest,
  verifyInternalRequest,
  type CallerKeySource,
  type ReceivedRequest,
} from './crypto/internal-request.ts';
export { thumbprint, type CallerKey, type PublicJwk, type VerifyKey } from './crypto/keys.ts';
export { pseudonym, type HumanPseudonym } from './crypto/pseudonym.ts';
export {
  asSecretBytes,
  asSecretText,
  asTotpCode,
  asVerifier,
  secretEqual,
  type SecretBytes,
  type SecretText,
  type TotpCode,
  type Verifier,
} from './crypto/secret-types.ts';
export {
  issuerOf,
  SIGN_IN_PREFIX,
  SIGN_IN_TYP,
  verifySignIn,
  type MaterialClass,
  type SignInClaims,
  type SignInKeySource,
  type VerifyResult,
} from './crypto/sign-in-verify.ts';
export { createHealthServer, HEALTH_HOST, listenHealth } from './http/health.ts';
export { runHealthcheck } from './http/healthcheck.ts';
export {
  CONTRACT_VERSION,
  isProblemCode,
  PROBLEM_TABLE,
  ProblemError,
  problemBody,
  problemResponse,
  SUPPORTED_VERSIONS,
  type FieldError,
  type ProblemCode,
  type ProblemResponse,
  type Refusal,
} from './http/problems.ts';
export { migrationStatement, statement, type Statement } from './sql.ts';
export { MigrationError, migrate, runMigrations } from './store/migrations.ts';
export {
  CONNECTION_TIMEOUT_MS,
  ConflictError,
  POOL_MAX,
  poolConfig,
  STATEMENT_TIMEOUT_MS,
  Store,
  type ConnectionSettings,
  type Queryable,
} from './store/store.ts';
