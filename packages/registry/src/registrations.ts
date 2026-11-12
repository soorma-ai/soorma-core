// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Logical agent registrations and registration secrets in the environment
// store (U5 NP-AR-01, 03, 04, 06; BR-RG, BR-SE, BR-AF).
// - A registration is written once (the app role has no UPDATE or DELETE).
//   A violation of its primary key, and only that, is registration_exists;
//   any other store failure is unavailable (NP-AR-06)
// - Sets are stored sorted and de-duplicated (asStoredSet; D-CG-AR-07)
// - A secret is inserted under the cap of 10 active per registration,
//   serialised per registration by a transaction-scoped advisory lock, which
//   needs no UPDATE privilege (NP-AR-03): lock, count, insert. The lock is
//   released at commit or rollback
// - The agent-facts source is one statement for a list of agents in one
//   environment; an agent not returned is not found; a failure rejects the
//   whole call (U3 NP-04). It reads neither the snapshot nor the sponsor
// P4 compares no permission sets: the ceiling, the human-only class, and the
// declaration are P3's (D-AR-10). Writes run over the caller's transaction,
// so each commits with its attribution record (D-AR-18).
import type { Tx } from '@soorma/env-store';
import { environmentParams } from '@soorma/env-store';
import type { EnvironmentRef, PermissionSet } from '@soorma/policy-decision-seam';
import { ConflictError, UnavailableError, type Queryable } from '@soorma/service-kit';
import { asStoredSet } from './grants.ts';
import { registrationLockKey } from './registration-secret.ts';
import { SQL } from './sql.ts';

/** At most this many active secrets per registration (NFR-AR-06): a security bound, not a quota. */
export const MAX_ACTIVE_SECRETS = 10;

/** The registrations primary key, the one constraint mapped to registration_exists. */
const REGISTRATION_KEY = 'registrations_pkey';

export interface RegistrationRecord {
  readonly agent: string;
  readonly environment: EnvironmentRef;
  /** The sponsor's principal; its organization is the environment's. */
  readonly sponsor: string;
  readonly ceilingSnapshot: readonly string[];
  readonly standingPermissions: readonly string[];
  readonly reBroadeningDeclaration: readonly string[];
  readonly autonomyDeclared: boolean;
  readonly registeredAt: Date;
  readonly state: 'registered';
}

interface RegistrationRow {
  agent: string;
  sponsor: string;
  ceiling_snapshot: string[];
  standing_permissions: string[];
  re_broadening_declaration: string[];
  autonomy_declared: boolean;
  registered_at: Date;
  state: string;
}

export type RegistrationWrite =
  | { readonly kind: 'registered'; readonly registration: RegistrationRecord }
  | { readonly kind: 'exists' };

/** Writes one registration; `exists` when the agent's identifier is taken in E (D-AR-02, 26). */
export async function insertRegistration(
  tx: Tx,
  input: {
    environment: EnvironmentRef;
    agent: string;
    sponsor: string;
    ceilingSnapshot: Iterable<string>;
    standingPermissions: Iterable<string>;
    reBroadeningDeclaration: Iterable<string>;
    autonomyDeclared: boolean;
    registeredAt: Date;
  },
): Promise<RegistrationWrite> {
  const registration: RegistrationRecord = {
    agent: input.agent,
    environment: input.environment,
    sponsor: input.sponsor,
    ceilingSnapshot: asStoredSet(input.ceilingSnapshot),
    standingPermissions: asStoredSet(input.standingPermissions),
    reBroadeningDeclaration: asStoredSet(input.reBroadeningDeclaration),
    autonomyDeclared: input.autonomyDeclared,
    registeredAt: input.registeredAt,
    state: 'registered',
  };
  try {
    await tx.query(SQL.insertRegistration, [
      ...environmentParams(input.environment),
      registration.agent,
      registration.sponsor,
      registration.ceilingSnapshot,
      registration.standingPermissions,
      registration.reBroadeningDeclaration,
      registration.autonomyDeclared,
      registration.registeredAt,
    ]);
  } catch (error) {
    if (error instanceof ConflictError) {
      if (error.constraint === REGISTRATION_KEY) return { kind: 'exists' };
      throw new UnavailableError('the env store refused the registration');
    }
    throw error;
  }
  return { kind: 'registered', registration };
}

/** One registration in E, or undefined (BR-SE-03). A read failure rejects. */
export async function findRegistration(
  store: Queryable,
  environment: EnvironmentRef,
  agent: string,
): Promise<RegistrationRecord | undefined> {
  const rows = await store.query<RegistrationRow>(SQL.findRegistration, [
    ...environmentParams(environment),
    agent,
  ]);
  const row = rows[0];
  if (!row) return undefined;
  return {
    agent: row.agent,
    environment,
    sponsor: row.sponsor,
    ceilingSnapshot: row.ceiling_snapshot,
    standingPermissions: row.standing_permissions,
    reBroadeningDeclaration: row.re_broadening_declaration,
    autonomyDeclared: row.autonomy_declared,
    registeredAt: row.registered_at,
    state: 'registered',
  };
}

/**
 * U6's bootstrap and renewal read (BR-BS-04, BR-RN-04; D-CG-AC-20): the
 * registration's state and its sponsor, for the attribution record. S3 runs
 * it as soorma_env_data, which holds SELECT on registrations only.
 */
export async function registrationForBootstrap(
  store: Queryable,
  environment: EnvironmentRef,
  agent: string,
): Promise<{ state: string; sponsor: string } | undefined> {
  const [row] = await store.query<{ state: string; sponsor: string }>(
    SQL.registrationForBootstrap,
    [...environmentParams(environment), agent],
  );
  return row ? { state: row.state, sponsor: row.sponsor } : undefined;
}

export interface SecretRecord {
  readonly id: string;
  readonly environment: EnvironmentRef;
  readonly registration: string;
  readonly issuer: string;
  readonly issuedAt: Date;
  readonly state: 'active';
}

export type SecretWrite =
  { readonly kind: 'issued'; readonly secret: SecretRecord } | { readonly kind: 'limitReached' };

/**
 * Inserts a secret's record under the cap (NP-AR-03): the per-registration
 * advisory lock, the count of active secrets, then the insert. `limitReached`
 * at 10 active, writing nothing. Only the digest is stored.
 */
export async function insertSecretUnderCap(
  tx: Tx,
  input: {
    id: string;
    environment: EnvironmentRef;
    registration: string;
    issuer: string;
    digest: Buffer;
    issuedAt: Date;
  },
): Promise<SecretWrite> {
  await tx.query(SQL.lockRegistrationSecrets, [
    registrationLockKey(input.environment, input.registration),
  ]);
  const [row] = await tx.query<{ active: number }>(SQL.countActiveSecrets, [
    ...environmentParams(input.environment),
    input.registration,
  ]);
  if ((row?.active ?? 0) >= MAX_ACTIVE_SECRETS) return { kind: 'limitReached' };
  await tx.query(SQL.insertSecret, [
    input.id,
    ...environmentParams(input.environment),
    input.registration,
    input.issuer,
    input.digest,
    input.issuedAt,
  ]);
  return {
    kind: 'issued',
    secret: {
      id: input.id,
      environment: input.environment,
      registration: input.registration,
      issuer: input.issuer,
      issuedAt: input.issuedAt,
      state: 'active',
    },
  };
}

/** U3's AgentFacts, by shape (P4 does not import P3; NP-AR-04). */
export interface StoredAgentFacts {
  readonly registrationView: {
    readonly autonomyDeclared: boolean;
    readonly reBroadeningDeclaration: PermissionSet;
  };
  readonly standingSet: PermissionSet;
}

/** U3's AgentFactsSource, by shape. */
export interface StoredAgentFactsSource {
  load(
    environment: EnvironmentRef,
    agents: readonly string[],
  ): Promise<ReadonlyMap<string, StoredAgentFacts>>;
}

/** P4's agent-facts source (D-AR-19): one statement per call; all or nothing. */
export function agentFactsFromStore(store: Queryable): StoredAgentFactsSource {
  return Object.freeze({
    async load(
      environment: EnvironmentRef,
      agents: readonly string[],
    ): Promise<ReadonlyMap<string, StoredAgentFacts>> {
      const facts = new Map<string, StoredAgentFacts>();
      if (agents.length === 0) return facts;
      const rows = await store.query<{
        agent: string;
        autonomy_declared: boolean;
        re_broadening_declaration: string[];
        standing_permissions: string[];
      }>(SQL.agentFacts, [...environmentParams(environment), [...new Set(agents)]]);
      for (const row of rows)
        facts.set(
          row.agent,
          Object.freeze({
            registrationView: Object.freeze({
              autonomyDeclared: row.autonomy_declared,
              reBroadeningDeclaration: new Set(row.re_broadening_declaration),
            }),
            standingSet: new Set(row.standing_permissions),
          }),
        );
      return facts;
    },
  });
}
