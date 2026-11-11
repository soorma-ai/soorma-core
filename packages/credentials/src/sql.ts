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
};
