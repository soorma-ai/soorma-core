// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Every statement P5 runs over the environment store (D-CG-OI-04;
// NFR-EHA-13). Constant text, values bound. Every statement constrains on the
// environment's three columns (D-EHA-29).
import { statement } from '@soorma/service-kit';

const sql = statement;

export const SQL = {
  /** $1 id, $2 to $4 the environment, $5 principal, $6 issued_from, $7 issued_at, $8 expires_at. */
  insertCredential: sql(
    `INSERT INTO credentials (id, organization, project, environment, principal, issued_from,
       issued_at, expires_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'live')`,
  ),
  /** O3 (NP-EHA-01 step 9): the record by id in E, uncached. $1 id, $2 to $4 the environment. */
  credentialById: sql(
    `SELECT principal, issued_from, expires_at, state FROM credentials
      WHERE id = $1 AND organization = $2 AND project = $3 AND environment = $4`,
  ),
  /**
   * Renewal (NP-EHA-09): only while live. Zero rows: another request ended it.
   * $1 id, $2 to $4 the environment, $5 the new expiry.
   */
  renewCredential: sql(
    `UPDATE credentials SET expires_at = $5
      WHERE id = $1 AND organization = $2 AND project = $3 AND environment = $4
        AND state = 'live'
     RETURNING id`,
  ),
  /** Ending (NP-EHA-09): only while live. $1 id, $2 to $4 the environment, $5 ended_at. */
  endCredential: sql(
    `UPDATE credentials SET state = 'ended', ended_at = $5, ended_by = 'self'
      WHERE id = $1 AND organization = $2 AND project = $3 AND environment = $4
        AND state = 'live'
     RETURNING id`,
  ),

  // ---- U6: the agent credential (NP-AC-03) and revocation state (NP-AC-04). ----
  // Run as S3's role, soorma_env_data (D-ID-AC-07); the privilege test runs
  // these same objects as that role (TC-AC-080).

  /** A new lineage. $1 cid, $2 to $4 the environment, $5 agent, $6 instance, $7 secret id,
   * $8 issued_at, $9 lineage_ends_at, $10 expires_at. */
  insertAgentCredential: sql(
    `INSERT INTO agent_credentials (id, organization, project, environment, agent, instance,
       secret, issued_at, lineage_ends_at, expires_at)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
  ),
  /** The record by cid in E, uncached (BR-RN-02). $1 cid, $2 to $4 the environment. */
  agentCredentialById: sql(
    `SELECT agent, instance, secret, issued_at, lineage_ends_at, expires_at FROM agent_credentials
      WHERE id = $1 AND organization = $2 AND project = $3 AND environment = $4`,
  ),
  /**
   * Renewal (BR-RN-06, 07): the binding is in the WHERE, so a token whose
   * record names another agent or instance updates nothing; concurrent
   * renewals keep the later expiry. The store's CHECK refuses an expiry past
   * the lineage end. $1 cid, $2 to $4 the environment, $5 agent, $6 instance,
   * $7 the new expiry.
   */
  renewAgentCredential: sql(
    `UPDATE agent_credentials SET expires_at = GREATEST(expires_at, $7)
      WHERE id = $1 AND organization = $2 AND project = $3 AND environment = $4
        AND agent = $5 AND instance = $6
     RETURNING expires_at, lineage_ends_at`,
  ),
  /**
   * The direct revocation read (D-AC-01; NP-AC-04): each granularity
   * answered on its own, so the caller can tell which one revoked
   * (BR-RN-03; BR-RF-AC-03). At bootstrap there is no cid yet: $4 is null
   * and matches nothing. $1 to $3 the environment, $4 cid, $5 agent.
   */
  revoked: sql(
    `SELECT EXISTS (SELECT 1 FROM credential_revocations
                     WHERE organization = $1 AND project = $2 AND environment = $3
                       AND credential = $4) AS credential_revoked,
            EXISTS (SELECT 1 FROM agent_revocations
                     WHERE organization = $1 AND project = $2 AND environment = $3
                       AND agent = $5) AS agent_revoked`,
  ),
};
