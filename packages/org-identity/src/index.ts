// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/org-identity (P10): human principals, material, sign-ins, keys, tokens,
// TOTP, the K policy, and the org store.
export { CLOCK, systemClock, type Clock } from './clock.ts';
export { KeyMaterialError, UnavailableError } from './errors.ts';
export {
  Lifetimes,
  PENDING_SECOND_FACTOR_LIFETIME_MS,
  SIGN_IN_ABSOLUTE_MAXIMUM_MS,
  SIGN_IN_LIFETIME_MS,
} from './lifetimes.ts';
export {
  canonicalJson,
  referenceJson,
  type Canonical,
  type PrincipalReference,
} from './crypto/canonical.ts';
export {
  defaultPermits,
  HASH_MEMORY_MIB,
  HASH_WAIT_MS,
  HashSemaphore,
} from './crypto/hash-semaphore.ts';
export {
  KeyRing,
  thumbprint,
  type CallerKey,
  type KeyMaterialInput,
  type PublicJwk,
  type VerifyKey,
} from './crypto/key-ring.ts';
export { pseudonym, type HumanPseudonym } from './crypto/pseudonym.ts';
export {
  ARGON2_PARAMETERS,
  nodeArgon2id,
  SecretHasher,
  secretInput,
  type Argon2Call,
  type Argon2id,
} from './crypto/secret-hash.ts';
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
  decryptSeed,
  encryptSeed,
  SeedDecryptionError,
  type StoredSeed,
} from './crypto/seed-cipher.ts';
export {
  issuerOf,
  mintSignIn,
  SIGN_IN_PREFIX,
  SIGN_IN_TYP,
  verifySignIn,
  type MaterialClass,
  type MintInput,
  type SignInClaims,
  type VerifyResult,
} from './crypto/sign-in-token.ts';
export {
  base32,
  codeAt,
  matchStep,
  newSeed,
  otpauthUri,
  stepAt,
  TOTP_DIGITS,
  TOTP_DRIFT_STEPS,
  TOTP_SEED_BYTES,
  TOTP_STEP_SECONDS,
} from './crypto/totp.ts';
export {
  BREACHED_FILE,
  BREACHED_MANIFEST,
  BreachedList,
  BreachedListError,
  breachedPrefix,
  manifestDigest,
} from './policy/breached-list.ts';
export {
  CONTEXT_WORD_MIN_LENGTH,
  K_MAX_CODE_POINTS,
  K_MIN_CODE_POINTS,
  SecretPolicy,
  type PolicyContext,
  type PolicyResult,
  type SecretRejection,
} from './policy/secret-policy.ts';
export { migrationStatement, SQL, statement, type Statement } from './sql.ts';
export { MIGRATION_LOCK_KEY, MigrationError, MIGRATIONS_DIR, migrate } from './store/migrations.ts';
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
export {
  FirstAdminError,
  OrgIdentity,
  type FirstAdminOutcome,
  type FirstAuthentication,
  type IssuedSignIn,
  type MaterialChange,
  type MaterialChangeResult,
  type OrgIdentityDependencies,
  type Refusal,
  type Result,
  type SecondFactorProof,
} from './domain/org-identity.ts';
export type { AttemptBound, BoundAdmission, FailureRecorder, Surface } from './domain/ports.ts';
export {
  PRUNE_INTERVAL_MS,
  PRUNE_LOCK_KEY,
  Pruner,
  RETENTION_MS,
  type PruneResult,
} from './domain/pruner.ts';
