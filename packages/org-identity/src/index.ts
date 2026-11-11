// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/org-identity (P10): human principals, material, sign-ins, keys, tokens,
// TOTP, the K policy, and the org store. Its organization-neutral runtime moved
// to @soorma/service-kit (U4 NP-EHA-15).
export {
  Lifetimes,
  PENDING_SECOND_FACTOR_LIFETIME_MS,
  SIGN_IN_ABSOLUTE_MAXIMUM_MS,
  SIGN_IN_LIFETIME_MS,
} from './lifetimes.ts';
export {
  defaultPermits,
  HASH_MEMORY_MIB,
  HASH_WAIT_MS,
  HashSemaphore,
} from './crypto/hash-semaphore.ts';
export { KeyRing, type KeyMaterialInput } from './crypto/key-ring.ts';
export {
  ARGON2_PARAMETERS,
  nodeArgon2id,
  SecretHasher,
  secretInput,
  type Argon2Call,
  type Argon2id,
  type Argon2Parameters,
} from './crypto/secret-hash.ts';
export {
  decryptSeed,
  encryptSeed,
  SeedDecryptionError,
  type StoredSeed,
} from './crypto/seed-cipher.ts';
export { mintSignIn, type MintInput } from './crypto/sign-in-token.ts';
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
export { SQL } from './sql.ts';
export {
  MIGRATION_LOCK_KEY,
  MigrationError,
  MIGRATIONS_DIR,
  migrate,
  runMigrations,
} from './store/migrations.ts';
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
