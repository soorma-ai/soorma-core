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
};
