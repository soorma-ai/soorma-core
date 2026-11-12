// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Every SQL statement of the abuse bound (D-CG-OI-04). Times are bound as
// epoch milliseconds from the injected Clock, never the database's now(), so
// tests control them (P-14). Window entries are `{ id, at }` in the slot's
// `entries` array; an entry is live while `at` is within the last 15 minutes.
import { statement } from '@soorma/service-kit';

export const SQL = {
  /**
   * Admission (P-04), one statement under the slot row's lock: insert the slot
   * with this entry, or, on conflict, append the entry to the live entries,
   * but only while fewer than 10 are live and the backoff has passed. No row
   * returned means refused.
   * $1 slot, $2 entry id, $3 now (ms), $4 window (ms), $5 max live entries.
   */
  admit: statement(
    `INSERT INTO attempt_slots AS s (slot, entries)
     VALUES ($1, jsonb_build_array(jsonb_build_object('id', $2::text, 'at', $3::bigint)))
     ON CONFLICT (slot) DO UPDATE SET entries = (
       SELECT coalesce(jsonb_agg(e ORDER BY (e ->> 'at')::bigint), '[]'::jsonb)
         FROM jsonb_array_elements(s.entries) AS e
        WHERE (e ->> 'at')::bigint > $3::bigint - $4::bigint
     ) || jsonb_build_array(jsonb_build_object('id', $2::text, 'at', $3::bigint))
     WHERE (
       SELECT count(*) FROM jsonb_array_elements(s.entries) AS e
        WHERE (e ->> 'at')::bigint > $3::bigint - $4::bigint
     ) < $5::int
       AND (s.next_allowed_at IS NULL OR s.next_allowed_at <= to_timestamp($3::bigint / 1000.0))
     RETURNING slot`,
  ),

  /** The slot's state, to compute Retry-After after a refusal (P-05). */
  slotState: statement(
    `SELECT entries, (extract(epoch FROM next_allowed_at) * 1000)::bigint AS next_allowed_ms
       FROM attempt_slots WHERE slot = $1`,
  ),

  /**
   * A failure keeps its entry; the consecutive count rises, and from the 5th
   * the next attempt waits 2^(n-5) seconds, capped at 900 (NFR-OI-03).
   * $1 slot, $2 now (ms), $3 backoff start, $4 cap (s).
   */
  settleFailure: statement(
    `UPDATE attempt_slots
        SET consecutive = consecutive + 1,
            next_allowed_at = CASE
              WHEN consecutive + 1 >= $3::int
              THEN to_timestamp($2::bigint / 1000.0)
                   + make_interval(secs => least(power(2, consecutive + 1 - $3::int), $4::int))
              ELSE next_allowed_at
            END
      WHERE slot = $1`,
  ),

  /**
   * A success removes exactly its own entry, never another's, and resets the
   * backoff only (NFR-OI-02, 03). $1 slot, $2 entry id.
   */
  settleSuccess: statement(
    `UPDATE attempt_slots
        SET entries = (
              SELECT coalesce(jsonb_agg(e ORDER BY (e ->> 'at')::bigint), '[]'::jsonb)
                FROM jsonb_array_elements(entries) AS e
               WHERE e ->> 'id' <> $2::text
            ),
            consecutive = 0,
            next_allowed_at = NULL
      WHERE slot = $1`,
  ),

  /** A batch of Failed Attempt records (P-11). */
  insertFailedAttempts: statement(
    `INSERT INTO failed_attempts (organization, principal, surface, at, refused_by_bound)
     SELECT * FROM unnest($1::text[], $2::text[], $3::text[], $4::timestamptz[], $5::boolean[])`,
  ),

  /**
   * U6's failed bootstrap attempts (NP-AC-07; BR-FA-01, 02): a batch, joined to
   * registrations, so an attempt on an agent that does not exist in E writes
   * nothing: the statement decides existence, off the response path. Run by
   * S3 as soorma_env_data (TC-AC-080 runs this object).
   * $1 to $3 the environments, $4 agents, $5 times, $6 refused-by-bound, $7 reasons.
   */
  insertFailedBootstrapAttempts: statement(
    `INSERT INTO failed_bootstrap_attempts
       (organization, project, environment, agent, at, refused_by_bound, reason)
     SELECT u.organization, u.project, u.environment, u.agent, u.at, u.refused_by_bound, u.reason
       FROM unnest($1::text[], $2::text[], $3::text[], $4::text[], $5::timestamptz[],
                   $6::boolean[], $7::text[])
            AS u(organization, project, environment, agent, at, refused_by_bound, reason)
       JOIN registrations r
         ON r.organization = u.organization AND r.project = u.project
        AND r.environment = u.environment AND r.agent = u.agent`,
  ),
} as const;
