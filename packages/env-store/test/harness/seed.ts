// SPDX-License-Identifier: FSL-1.1-ALv2
//
// Test-only revocation seeding (U6 D-AC-16; NP-AC-06; D-CG-AC-10; M1-FR-07).
// Agent revocation has no product writer in M1 (PF FR-011 deferred), so tests
// write revocation state here, as the store's owner (soorma_env_migrator).
// This file is under test/, outside every package's src/, and never in an
// image. On the running stack, e2e/support.ts seeds the same rows through
// `docker compose exec` (Group 9).
import type pg from 'pg';

/** Revokes one credential lineage (its cid) in an environment. */
export async function seedCredentialRevocation(
  owner: pg.ClientBase,
  environment: readonly string[],
  credential: string,
  at: Date,
): Promise<void> {
  await owner.query(
    `INSERT INTO credential_revocations (organization, project, environment, credential, revoked_at)
     VALUES ($1, $2, $3, $4, $5)`,
    [...environment, credential, at],
  );
}

/** Revokes a logical agent, every instance present and future, in an environment. */
export async function seedAgentRevocation(
  owner: pg.ClientBase,
  environment: readonly string[],
  agent: string,
  at: Date,
): Promise<void> {
  await owner.query(
    `INSERT INTO agent_revocations (organization, project, environment, agent, revoked_at)
     VALUES ($1, $2, $3, $4, $5)`,
    [...environment, agent, at],
  );
}
