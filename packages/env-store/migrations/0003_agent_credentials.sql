-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- Agent credentials, revocation state, and the bootstrap bound (U6
-- agent-credentials; NFR Design NP-AC-03 to 07). Run in {env}-migrate as
-- soorma_env_migrator, after 0002. 0001 and 0002 are not changed.
--
-- Every table carries its environment as three columns, and every statement
-- constrains on them (D-EHA-29). The grants at the end are S3's role's only
-- privileges on these tables (soorma_env_data, D-ID-AC-07, the user's
-- decision): S2's soorma_env_app gets nothing here. No DELETE anywhere:
-- nothing is pruned in M1 (NFR-AC-24).

-- One row per lineage: bootstrap writes it, renewal moves its expiry, and the
-- cid never changes, so a credential revocation reaches every renewal of it
-- (D-AC-14). Times are whole seconds, so a token's exp and the row agree.
CREATE TABLE agent_credentials (
  id text PRIMARY KEY,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  instance text NOT NULL,
  secret text NOT NULL,
  issued_at timestamptz NOT NULL,
  lineage_ends_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  CONSTRAINT agent_credentials_registration_fkey
    FOREIGN KEY (organization, project, environment, agent)
    REFERENCES registrations (organization, project, environment, agent),
  CONSTRAINT agent_credentials_secret_fkey
    FOREIGN KEY (secret) REFERENCES registration_secrets (id),
  CONSTRAINT agent_credentials_instance_length CHECK (char_length(instance) BETWEEN 1 AND 128),
  CONSTRAINT agent_credentials_expiry_after_issue CHECK (expires_at > issued_at),
  CONSTRAINT agent_credentials_lineage_after_issue CHECK (lineage_ends_at > issued_at),
  -- M in the store, beside S3's own cap (D-AC-02).
  CONSTRAINT agent_credentials_expiry_within_lineage CHECK (expires_at <= lineage_ends_at)
);

-- Revocation state, one table per granularity (Q5 A). Terminal: only the owner
-- writes (the test-only seeding; no product writer in M1, D-AC-16). Each
-- target must exist in E, so a revocation never names another environment's
-- credential or agent (I1).
CREATE TABLE credential_revocations (
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  credential text NOT NULL,
  revoked_at timestamptz NOT NULL,
  CONSTRAINT credential_revocations_pkey
    PRIMARY KEY (organization, project, environment, credential),
  CONSTRAINT credential_revocations_credential_fkey
    FOREIGN KEY (credential) REFERENCES agent_credentials (id)
);

CREATE TABLE agent_revocations (
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  revoked_at timestamptz NOT NULL,
  CONSTRAINT agent_revocations_pkey PRIMARY KEY (organization, project, environment, agent),
  CONSTRAINT agent_revocations_registration_fkey
    FOREIGN KEY (organization, project, environment, agent)
    REFERENCES registrations (organization, project, environment, agent)
);

-- The bootstrap bound's slots: U2's org-store table, the same name and
-- columns, so P8's statements run in either store (NP-AC-07). One table per
-- environment (one store per environment).
CREATE TABLE attempt_slots (
  slot integer PRIMARY KEY CHECK (slot BETWEEN 0 AND 1048575),
  entries jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(entries) = 'array'),
  consecutive integer NOT NULL DEFAULT 0 CHECK (consecutive >= 0),
  next_allowed_at timestamptz
);

-- Failed bootstrap attempts, recorded against an existing registration only
-- (PF FR-027; BR-FA-01): the batch insert joins registrations, so the writer,
-- off the response path, decides existence. Nothing presented is recorded.
CREATE TABLE failed_bootstrap_attempts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  at timestamptz NOT NULL,
  refused_by_bound boolean NOT NULL,
  reason text NOT NULL CHECK (reason IN ('bound_refused', 'unsupported_material',
    'malformed_secret', 'unknown_secret', 'secret_not_active', 'secret_mismatch',
    'registration_not_registered', 'agent_revoked', 'store_unavailable')),
  CONSTRAINT failed_bootstrap_attempts_registration_fkey
    FOREIGN KEY (organization, project, environment, agent)
    REFERENCES registrations (organization, project, environment, agent)
);

-- S3's role's privileges, and nothing more (D-ID-AC-07; NP-AC-06 as corrected).
REVOKE ALL ON agent_credentials, credential_revocations, agent_revocations,
  attempt_slots, failed_bootstrap_attempts FROM PUBLIC;
-- Bootstrap reads the registration and the one secret record; both operations
-- read revocation state.
GRANT SELECT ON registrations, registration_secrets, credential_revocations, agent_revocations
  TO soorma_env_data;
GRANT SELECT, INSERT ON agent_credentials TO soorma_env_data;
GRANT UPDATE (expires_at) ON agent_credentials TO soorma_env_data;
GRANT INSERT ON attribution_records, failed_bootstrap_attempts TO soorma_env_data;
GRANT USAGE ON SEQUENCE failed_bootstrap_attempts_id_seq TO soorma_env_data;
-- Exactly P8's statements: admission (INSERT ... ON CONFLICT DO UPDATE ...
-- RETURNING), the slot's state (SELECT), and settling (UPDATE). The slot
-- number is never updated.
GRANT SELECT ON attempt_slots TO soorma_env_data;
GRANT INSERT (slot, entries) ON attempt_slots TO soorma_env_data;
GRANT UPDATE (entries, consecutive, next_allowed_at) ON attempt_slots TO soorma_env_data;
