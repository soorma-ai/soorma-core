// SPDX-License-Identifier: FSL-1.1-ALv2
//
// P7's one statement (D-CG-OI-04; NFR-EHA-13). The app role has INSERT and
// SELECT on attribution_records, no UPDATE or DELETE: records are written once
// (BR-AT-08).
import { statement } from '@soorma/service-kit';

const sql = statement;

export const SQL = {
  insertRecord: sql(
    `INSERT INTO attribution_records (id, recorded_at, request_id, organization, project,
       environment, operation, actor_kind, principal, credential_kind, credential_id,
       registration, instance, sponsor, target_kind, target_id, self_grant, chain, origin,
       rebroadening_load_bearing, rebroadening_hop)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17,
       $18, $19, $20, $21)`,
  ),
};
