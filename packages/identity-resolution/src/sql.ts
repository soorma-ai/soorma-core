// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Every SQL statement of identity resolution (D-CG-OI-04). Read-only: it
// decides identity and changes no record (BR-SEAM-02).
import { statement } from '@soorma/org-identity';

export const SQL = {
  /** The principal's current (not retired) material of one class, if any. $1 org, $2 principal, $3 class. */
  currentMaterial: statement(
    `SELECT id, state, verifier, seed, last_step
       FROM materials
      WHERE organization = $1 AND principal = $2 AND class = $3 AND state <> 'retired'`,
  ),
} as const;
