// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The one statement P6's agent half runs (U6 NP-AC-08; D-CG-AC-03): the
// registration secret record its value names, by id, in E, and whether the
// claimed agent exists (for the security log's reason only). It never
// iterates a registration's secrets (U5 obligation). Run by S3 as
// soorma_env_data; the privilege test runs this same object (TC-AC-080).
import { statement } from '@soorma/service-kit';

export const SQL = {
  /** $1 to $3 the environment, $4 the claimed agent, $5 the secret record's id. */
  secretForBootstrap: statement(
    `SELECT EXISTS (SELECT 1 FROM registrations
                     WHERE organization = $1 AND project = $2 AND environment = $3
                       AND agent = $4) AS agent_exists,
            s.registration, s.state, s.digest
       FROM (SELECT 1) AS one
       LEFT JOIN registration_secrets s
         ON s.id = $5 AND s.organization = $1 AND s.project = $2 AND s.environment = $3`,
  ),
};
