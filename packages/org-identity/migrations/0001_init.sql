-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- The org store (logical-components §3; NFR-OI-15 to 18). Run once, in
-- org-migrate, as soorma_org_migrator, which owns every table. The grants at
-- the end are the app role's only privileges (Infrastructure Design §5;
-- D-CG-OI-15): no DELETE on principals or materials, so the database itself
-- enforces "never deleted, never pruned" (BR-HP-03), and no DDL.

-- Human principals: never deleted (ID FR-001).
CREATE TABLE principals (
  organization text NOT NULL,
  principal text NOT NULL,
  state text NOT NULL CHECK (state IN ('pending', 'active')),
  registered_at timestamptz NOT NULL,
  registered_by_environment text NOT NULL,
  activated_at timestamptz,
  PRIMARY KEY (organization, principal),
  CHECK ((state = 'active') = (activated_at IS NOT NULL))
);

-- Authentication material: one record per material value; never deleted. The
-- verifier (K) or the encrypted seed (P) is destroyed on retirement.
CREATE TABLE materials (
  id text PRIMARY KEY,
  organization text NOT NULL,
  principal text NOT NULL,
  class text NOT NULL CHECK (class IN ('K', 'P')),
  state text NOT NULL CHECK (state IN ('enrollment', 'active', 'retired')),
  authenticator_type text,
  verifier text,
  seed jsonb,
  last_step bigint,
  enrolled_at timestamptz,
  enrolled_by text CHECK (enrolled_by = 'configuration'),
  established_at timestamptz,
  established_by_organization text,
  established_by_principal text,
  retired_at timestamptz,
  FOREIGN KEY (organization, principal) REFERENCES principals (organization, principal),
  -- Enrollment material is class K, configured, and has no establishment yet.
  CHECK (state <> 'enrollment' OR (class = 'K' AND enrolled_by IS NOT NULL AND established_at IS NULL)),
  -- K holds a verifier; P holds an authenticator type and an encrypted seed.
  CHECK (class <> 'K' OR (authenticator_type IS NULL AND seed IS NULL AND last_step IS NULL)),
  CHECK (class <> 'P' OR (authenticator_type IS NOT NULL AND verifier IS NULL)),
  CHECK (state = 'retired' OR class <> 'K' OR verifier IS NOT NULL),
  CHECK (state = 'retired' OR class <> 'P' OR seed IS NOT NULL),
  -- Retirement destroys the verifier and the seed, and is recorded.
  CHECK ((state = 'retired') = (retired_at IS NOT NULL)),
  CHECK (state <> 'retired' OR (verifier IS NULL AND seed IS NULL)),
  -- Active and retired material was established by a human; enrollment material
  -- was not (it becomes active at first authentication, never retired as such).
  CHECK ((state = 'enrollment') = (established_at IS NULL)),
  CHECK ((established_at IS NULL) = (established_by_principal IS NULL)),
  CHECK ((established_at IS NULL) = (established_by_organization IS NULL))
);

-- At most one record of each class in enrollment or active, per principal.
CREATE UNIQUE INDEX materials_one_current_per_class
  ON materials (organization, principal, class)
  WHERE state <> 'retired';

-- A pending second-factor enrollment: at most one per principal.
CREATE TABLE pending_second_factors (
  organization text NOT NULL,
  principal text NOT NULL,
  id text NOT NULL UNIQUE,
  authenticator_type text NOT NULL,
  seed jsonb NOT NULL,
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (organization, principal),
  FOREIGN KEY (organization, principal) REFERENCES principals (organization, principal)
);

-- Organization sign-ins. Pruned 90 days after ending or expiry (P-16).
CREATE TABLE sign_ins (
  id text PRIMARY KEY,
  organization text NOT NULL,
  principal text NOT NULL,
  authenticated_at timestamptz NOT NULL,
  classes text[] NOT NULL CHECK (classes <@ ARRAY['K', 'P'] AND 'K' = ANY (classes)),
  expires_at timestamptz NOT NULL,
  state text NOT NULL CHECK (state IN ('live', 'ended')),
  ended_at timestamptz,
  ended_by text CHECK (ended_by IN ('self', 'materialChange')),
  FOREIGN KEY (organization, principal) REFERENCES principals (organization, principal),
  CHECK ((state = 'ended') = (ended_at IS NOT NULL AND ended_by IS NOT NULL))
);

CREATE INDEX sign_ins_live_by_principal
  ON sign_ins (organization, principal)
  WHERE state = 'live';

CREATE INDEX sign_ins_prunable ON sign_ins (expires_at);

-- Failed attempts, written only for an existing principal (D-OI-16), off the
-- response path (D-OI-27). Nothing presented is recorded. Pruned at 90 days.
CREATE TABLE failed_attempts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  organization text NOT NULL,
  principal text NOT NULL,
  surface text NOT NULL CHECK (surface IN ('authenticate', 'firstAuthenticate', 'changeMaterial')),
  at timestamptz NOT NULL,
  refused_by_bound boolean NOT NULL,
  FOREIGN KEY (organization, principal) REFERENCES principals (organization, principal)
);

CREATE INDEX failed_attempts_at ON failed_attempts (at);

-- The abuse bound's slots (P-04): a fixed table of at most 2^20 rows, keyed
-- by HMAC-SHA-256 of the presented reference. Never pruned.
CREATE TABLE attempt_slots (
  slot integer PRIMARY KEY CHECK (slot BETWEEN 0 AND 1048575),
  entries jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(entries) = 'array'),
  consecutive integer NOT NULL DEFAULT 0 CHECK (consecutive >= 0),
  next_allowed_at timestamptz
);

-- The app role's privileges: exactly these (Infrastructure Design §5).
GRANT SELECT, INSERT, UPDATE
  ON principals, materials, pending_second_factors, sign_ins, failed_attempts, attempt_slots
  TO soorma_org_app;
GRANT DELETE ON failed_attempts, sign_ins, pending_second_factors TO soorma_org_app;
-- The one identity column's sequence (amendment 2).
GRANT USAGE ON SEQUENCE failed_attempts_id_seq TO soorma_org_app;
