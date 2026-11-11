// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Every SQL statement this package runs (D-CG-OI-04; NFR-OI-17). Each is a
// constant string with $n placeholders; values are always bound parameters,
// never interpolated. The `sql` check (tools/checks) fails on a query whose
// statement is not from this module, and on a template literal with a
// substitution here.
import { statement } from '@soorma/service-kit';

const sql = statement;

export const SQL = {
  /** Infrastructure Design §5: asserted at start-up. */
  synchronousCommit: sql('SHOW synchronous_commit'),

  // Principals.
  principalState: sql('SELECT state FROM principals WHERE organization = $1 AND principal = $2'),
  /** Registers a first Admin unless present (BR-CFG-05). $1 org, $2 principal, $3 at, $4 environment. */
  registerPrincipal: sql(
    `INSERT INTO principals (organization, principal, state, registered_at, registered_by_environment)
     VALUES ($1, $2, 'pending', $3, $4)
     ON CONFLICT (organization, principal) DO NOTHING
     RETURNING principal`,
  ),
  /** $1 org, $2 principal, $3 at. */
  activatePrincipal: sql(
    `UPDATE principals SET state = 'active', activated_at = $3
      WHERE organization = $1 AND principal = $2 AND state = 'pending'
      RETURNING principal`,
  ),

  // Material.
  /** $1 id, $2 org, $3 principal, $4 verifier, $5 at. */
  insertEnrollment: sql(
    `INSERT INTO materials (id, organization, principal, class, state, verifier, enrolled_at, enrolled_by)
     VALUES ($1, $2, $3, 'K', 'enrollment', $4, $5, 'configuration')`,
  ),
  /** Single use (D-OI-04): only an enrollment record becomes active. $1 id, $2 verifier, $3 at, $4 org, $5 principal. */
  establishFromEnrollment: sql(
    `UPDATE materials
        SET state = 'active', verifier = $2, established_at = $3,
            established_by_organization = $4, established_by_principal = $5
      WHERE id = $1 AND organization = $4 AND principal = $5 AND state = 'enrollment'
      RETURNING id`,
  ),
  /** $1 org, $2 principal, $3 class. */
  activeMaterialId: sql(
    `SELECT id FROM materials
      WHERE organization = $1 AND principal = $2 AND class = $3 AND state = 'active'`,
  ),
  /** Retires a current record, destroying its verifier or seed. $1 id, $2 at. */
  retireMaterial: sql(
    `UPDATE materials SET state = 'retired', verifier = NULL, seed = NULL, retired_at = $2
      WHERE id = $1 AND state = 'active'
      RETURNING id`,
  ),
  /** $1 id, $2 org, $3 principal, $4 verifier, $5 at. */
  insertActiveK: sql(
    `INSERT INTO materials (id, organization, principal, class, state, verifier,
                            established_at, established_by_organization, established_by_principal)
     VALUES ($1, $2, $3, 'K', 'active', $4, $5, $2, $3)`,
  ),
  /** $1 id, $2 org, $3 principal, $4 type, $5 seed, $6 accepted step, $7 at. */
  insertActiveP: sql(
    `INSERT INTO materials (id, organization, principal, class, state, authenticator_type, seed, last_step,
                            established_at, established_by_organization, established_by_principal)
     VALUES ($1, $2, $3, 'P', 'active', $4, $5, $6, $7, $2, $3)`,
  ),
  /** A TOTP code is accepted at most once (P-12): a conditional update. $1 id, $2 step. */
  acceptStep: sql(
    `UPDATE materials SET last_step = $2
      WHERE id = $1 AND class = 'P' AND state = 'active' AND (last_step IS NULL OR last_step < $2)
      RETURNING id`,
  ),

  // Pending second-factor enrollments.
  /** Replaces any earlier one (BR-P-04). $1 org, $2 principal, $3 id, $4 type, $5 seed, $6 expires. */
  upsertPending: sql(
    `INSERT INTO pending_second_factors (organization, principal, id, authenticator_type, seed, expires_at)
     VALUES ($1, $2, $3, $4, $5, $6)
     ON CONFLICT (organization, principal) DO UPDATE
       SET id = EXCLUDED.id, authenticator_type = EXCLUDED.authenticator_type,
           seed = EXCLUDED.seed, expires_at = EXCLUDED.expires_at`,
  ),
  pendingFor: sql(
    `SELECT id, authenticator_type, seed, expires_at FROM pending_second_factors
      WHERE organization = $1 AND principal = $2`,
  ),
  /** $1 org, $2 principal, $3 id. */
  removePendingById: sql(
    `DELETE FROM pending_second_factors
      WHERE organization = $1 AND principal = $2 AND id = $3
      RETURNING id`,
  ),
  removePending: sql(
    'DELETE FROM pending_second_factors WHERE organization = $1 AND principal = $2',
  ),

  // Sign-ins.
  /** $1 id, $2 org, $3 principal, $4 authenticated at, $5 classes, $6 expires. */
  insertSignIn: sql(
    `INSERT INTO sign_ins (id, organization, principal, authenticated_at, classes, expires_at, state)
     VALUES ($1, $2, $3, $4, $5, $6, 'live')`,
  ),
  /** The sign-in and its principal's state, for O3. $1 id, $2 org. */
  signInWithPrincipal: sql(
    `SELECT s.principal, s.state, s.authenticated_at, s.classes, p.state AS principal_state
       FROM sign_ins s
       JOIN principals p ON p.organization = s.organization AND p.principal = s.principal
      WHERE s.id = $1 AND s.organization = $2`,
  ),
  /** $1 id, $2 org, $3 expires. */
  renewSignIn: sql(
    `UPDATE sign_ins SET expires_at = $3
      WHERE id = $1 AND organization = $2 AND state = 'live'
      RETURNING id`,
  ),
  /** $1 id, $2 org, $3 at. */
  endSignIn: sql(
    `UPDATE sign_ins SET state = 'ended', ended_at = $3, ended_by = 'self'
      WHERE id = $1 AND organization = $2 AND state = 'live'
      RETURNING id`,
  ),
  /** Ends every live sign-in of a human (BR-MC-04). $1 org, $2 principal, $3 at. */
  endSignInsForMaterialChange: sql(
    `UPDATE sign_ins SET state = 'ended', ended_at = $3, ended_by = 'materialChange'
      WHERE organization = $1 AND principal = $2 AND state = 'live'
      RETURNING id`,
  ),
  /** $1 id, $2 org. */
  /** U2 amendment A7 (U4 D-EHA-02): the record, its expiry, and its principal's state. */
  signInStatus: sql(
    `SELECT s.state, s.expires_at, p.state AS principal_state
       FROM sign_ins s
       JOIN principals p ON p.organization = s.organization AND p.principal = s.principal
      WHERE s.id = $1 AND s.organization = $2`,
  ),

  // Retention (P-16).
  pruneLock: sql('SELECT pg_try_advisory_xact_lock($1::bigint) AS locked'),
  pruneFailedAttempts: sql('DELETE FROM failed_attempts WHERE at < $1 RETURNING id'),
  pruneSignIns: sql(
    `DELETE FROM sign_ins
      WHERE (state = 'ended' AND ended_at < $1) OR expires_at < $1
      RETURNING id`,
  ),
} as const;
