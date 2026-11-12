-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- Logical agent registrations and registration secrets (U5 NP-AR-01;
-- logical-components §3). Run in {env}-migrate as soorma_env_migrator, after
-- 0001. Both tables are written once and never updated or deleted in M1: the
-- app role holds SELECT and INSERT only (D-AR-15; NFR-AR-23). A registration
-- is a resolution target (PF FR-013), so nothing may remove one.
--
-- Every table carries its environment as three columns, and every statement
-- constrains on them (D-EHA-29).

-- One row per logical agent in E (PF §7a, all eight attributes and its state).
-- The registration is also the agent's grant (D-AR-06): principal = agent,
-- set = standing_permissions, granted-at = registered_at, granted-by = sponsor.
CREATE TABLE registrations (
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  agent text NOT NULL,
  sponsor text NOT NULL,
  ceiling_snapshot text[] NOT NULL,
  standing_permissions text[] NOT NULL,
  re_broadening_declaration text[] NOT NULL,
  autonomy_declared boolean NOT NULL,
  registered_at timestamptz NOT NULL,
  state text NOT NULL,
  -- The client-chosen identifier, unique within E (D-AR-02). P4 maps a
  -- violation of this constraint, and only this one, to registration_exists.
  CONSTRAINT registrations_pkey PRIMARY KEY (organization, project, environment, agent),
  CONSTRAINT registrations_standing_bound CHECK (cardinality(standing_permissions) <= 32),
  CONSTRAINT registrations_declaration_bound CHECK (cardinality(re_broadening_declaration) <= 32),
  -- Defence in depth for the sponsor ceiling and the declaration (Q5 A). They
  -- assume flat-set containment, PF FR-018's minimal model; P3 decides, through
  -- the seam. If Access Policy's model ever makes containment richer (PF
  -- FR-019), a migration removes these two constraints. The human-only class
  -- is deliberately not repeated here: it has one definition, in
  -- packages/authority (D-AE-03).
  CONSTRAINT registrations_standing_within_snapshot
    CHECK (standing_permissions <@ ceiling_snapshot),
  CONSTRAINT registrations_declaration_within_standing
    CHECK (re_broadening_declaration <@ standing_permissions),
  -- Suspend, resume, and retire are absent from M1; a migration widens this.
  CONSTRAINT registrations_state CHECK (state = 'registered')
);

-- One row per issued secret. Several may be active per registration, up to the
-- cap of 10 (D-AR-04; NFR-AR-06). Only the verifier is stored: a 32-byte,
-- domain-separated SHA-256 of the secret's 256 random bits (NFR-AR-02).
CREATE TABLE registration_secrets (
  id text PRIMARY KEY,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  registration text NOT NULL,
  issuer text NOT NULL,
  digest bytea NOT NULL,
  issued_at timestamptz NOT NULL,
  state text NOT NULL,
  -- A secret names a registration of its own environment, or none at all (I1).
  CONSTRAINT registration_secrets_registration_fkey
    FOREIGN KEY (organization, project, environment, registration)
    REFERENCES registrations (organization, project, environment, agent),
  CONSTRAINT registration_secrets_digest_length CHECK (octet_length(digest) = 32),
  -- Retirement is absent from M1; a migration widens this.
  CONSTRAINT registration_secrets_state CHECK (state = 'active')
);

-- The cap's count, under the per-registration advisory lock (NP-AR-03).
CREATE INDEX registration_secrets_by_registration
  ON registration_secrets (organization, project, environment, registration);

-- The app role's privileges on U5's tables, and nothing more.
REVOKE ALL ON registrations, registration_secrets FROM PUBLIC;
GRANT SELECT, INSERT ON registrations TO soorma_env_app;
GRANT SELECT, INSERT ON registration_secrets TO soorma_env_app;
