// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Every statement P4 runs over the environment store (D-CG-OI-04;
// NFR-EHA-13). Constant text, values bound. Every statement constrains on the
// environment's three columns (D-EHA-29).
import { statement } from '@soorma/service-kit';

const sql = statement;

export const SQL = {
  /** $1 id, $2 to $4 the environment, $5 principal, $6 permissions, $7 granted_by_principal,
   * $8 granted_by_credential, $9 self_grant, $10 granted_at. */
  insertGrant: sql(
    `INSERT INTO grants (id, organization, project, environment, principal, permissions,
       granted_by_kind, granted_by_principal, granted_by_credential, self_grant, granted_at)
     VALUES ($1, $2, $3, $4, $5, $6, 'principal', $7, $8, $9, $10)`,
  ),
  /**
   * The configured first grant (NP-EHA-08): at most one per principal, by the
   * partial unique index. No row back means another start-up applied it.
   * $1 id, $2 to $4 the environment, $5 principal, $6 permissions, $7 granted_at.
   */
  insertFirstGrant: sql(
    `INSERT INTO grants (id, organization, project, environment, principal, permissions,
       granted_by_kind, granted_by_principal, granted_by_credential, self_grant, granted_at)
     VALUES ($1, $2, $3, $4, $5, $6, 'configuration', NULL, NULL, false, $7)
     ON CONFLICT (organization, project, environment, principal)
       WHERE granted_by_kind = 'configuration' DO NOTHING
     RETURNING id`,
  ),
  /** The held set (NP-EHA-10): the union of a principal's grants in E. Uncached. */
  heldSet: sql(
    `SELECT DISTINCT unnest(permissions) AS permission FROM grants
      WHERE organization = $1 AND project = $2 AND environment = $3 AND principal = $4`,
  ),
  /** A registration (NP-AR-01). $1 to $3 the environment, $4 agent, $5 sponsor,
   * $6 ceiling_snapshot, $7 standing_permissions, $8 re_broadening_declaration,
   * $9 autonomy_declared, $10 registered_at. */
  insertRegistration: sql(
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'registered')`,
  ),
  /** One registration in E. $1 to $3 the environment, $4 agent. */
  findRegistration: sql(
    `SELECT agent, sponsor, ceiling_snapshot, standing_permissions, re_broadening_declaration,
            autonomy_declared, registered_at, state
       FROM registrations
      WHERE organization = $1 AND project = $2 AND environment = $3 AND agent = $4`,
  ),
  /**
   * The agent-facts statement behind U3's port (NP-AR-04): never the snapshot
   * or the sponsor (PF §8b). $1 to $3 the environment, $4 the agents.
   */
  agentFacts: sql(
    `SELECT agent, autonomy_declared, re_broadening_declaration, standing_permissions
       FROM registrations
      WHERE organization = $1 AND project = $2 AND environment = $3
        AND agent = ANY($4::text[])`,
  ),
  /** The cap's per-registration lock, released at commit or rollback (NP-AR-03). $1 the key. */
  lockRegistrationSecrets: sql(`SELECT pg_advisory_xact_lock($1::bigint)`),
  /** Active secrets of one registration. $1 to $3 the environment, $4 registration. */
  countActiveSecrets: sql(
    `SELECT count(*)::int AS active FROM registration_secrets
      WHERE organization = $1 AND project = $2 AND environment = $3 AND registration = $4
        AND state = 'active'`,
  ),
  /** A secret's record: its verifier only, never the value. $1 id, $2 to $4 the
   * environment, $5 registration, $6 issuer, $7 digest, $8 issued_at. */
  insertSecret: sql(
    `INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')`,
  ),

  /**
   * U6's bootstrap (BR-BS-04; BR-AT-AC-01): the registration's state, and its
   * sponsor for the attribution record. Run by S3 as soorma_env_data.
   * $1 to $3 the environment, $4 agent.
   */
  registrationForBootstrap: sql(
    `SELECT state, sponsor FROM registrations
      WHERE organization = $1 AND project = $2 AND environment = $3 AND agent = $4`,
  ),

  /**
   * U7's publish and subscribe records (D-ET-18; D-CG-ET-09): the sponsor,
   * resolved from the registration inside the record's own transaction. Run by
   * S4 as soorma_env_ingest, whose SELECT on registrations is column-level.
   * $1 to $3 the environment, $4 agent.
   */
  sponsorForRecord: sql(
    `SELECT sponsor FROM registrations
      WHERE organization = $1 AND project = $2 AND environment = $3 AND agent = $4`,
  ),
};
