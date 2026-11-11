-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- An environment store (U4 logical-components §3; NFR-EHA-09 to 14). Run once,
-- in {env}-migrate, as soorma_env_migrator, which owns every table. The grants
-- at the end are the app role's only privileges (Infrastructure Design §6):
-- column-level UPDATE where a row changes, no DELETE anywhere, so the database
-- itself enforces that grants and attribution records are written once and
-- that nothing is pruned in M1 (BR-AT-08; NFR-EHA-21).
--
-- Every table carries its environment as three columns, and every statement
-- constrains on them (D-EHA-29), beside the store being one per environment.
-- U5 and U6 add their tables to this sequence, in their own migrations.

-- Human environment credentials (NP-EHA-01, 09). The record, not the token,
-- governs liveness: ending it refuses every token minted for it.
CREATE TABLE credentials (
  id text PRIMARY KEY,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  principal text NOT NULL,
  issued_from text NOT NULL,
  issued_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  state text NOT NULL,
  ended_at timestamptz,
  ended_by text,
  CONSTRAINT credentials_expiry_after_issue CHECK (expires_at > issued_at),
  CONSTRAINT credentials_state CHECK (state IN ('live', 'ended')),
  CONSTRAINT credentials_ended_by CHECK (ended_by IN ('self')),
  CONSTRAINT credentials_ended_fields CHECK (
    (state = 'ended') = (ended_at IS NOT NULL AND ended_by IS NOT NULL)
  )
);

-- Grants to human principals (NP-EHA-08, 10). Permissions are a sorted,
-- de-duplicated set, written once; the held set is their union.
CREATE TABLE grants (
  id text PRIMARY KEY,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  principal text NOT NULL,
  permissions text[] NOT NULL,
  granted_by_kind text NOT NULL,
  granted_by_principal text,
  granted_by_credential text,
  self_grant boolean NOT NULL,
  granted_at timestamptz NOT NULL,
  CONSTRAINT grants_permissions_not_empty CHECK (cardinality(permissions) > 0),
  CONSTRAINT grants_granted_by_kind CHECK (granted_by_kind IN ('principal', 'configuration')),
  CONSTRAINT grants_granted_by_fields CHECK (
    (granted_by_kind = 'principal')
      = (granted_by_principal IS NOT NULL AND granted_by_credential IS NOT NULL)
    AND (granted_by_kind = 'configuration')
      = (granted_by_principal IS NULL AND granted_by_credential IS NULL)
  ),
  CONSTRAINT grants_self_grant CHECK (
    self_grant = (granted_by_kind = 'principal' AND granted_by_principal = principal)
  )
);

-- P4's human GrantSource and holdsAnyGrant read through this index (NP-EHA-10).
CREATE INDEX grants_by_principal ON grants (organization, project, environment, principal);

-- At most one configuration grant per principal in the environment, so
-- concurrent start-ups write the first grant once (NP-EHA-08; BR-FG-02).
CREATE UNIQUE INDEX grants_one_configuration_grant
  ON grants (organization, project, environment, principal)
  WHERE granted_by_kind = 'configuration';

-- Attribution records (NP-EHA-07). Typed columns; the CHECK constraints repeat
-- BR-AT-05, so an inconsistent record is refused by the writer and by the
-- store. U6 and U7 write agent records here. No read surface in M1, so no
-- index beyond the primary key.
CREATE TABLE attribution_records (
  id text PRIMARY KEY,
  recorded_at timestamptz NOT NULL,
  request_id text,
  organization text NOT NULL,
  project text NOT NULL,
  environment text NOT NULL,
  operation text NOT NULL,
  actor_kind text NOT NULL,
  principal text,
  credential_kind text,
  credential_id text,
  registration text,
  instance text,
  sponsor text,
  target_kind text,
  target_id text,
  self_grant boolean NOT NULL DEFAULT false,
  chain jsonb,
  origin jsonb,
  rebroadening_load_bearing boolean,
  rebroadening_hop integer,
  CONSTRAINT attribution_actor_kind CHECK (actor_kind IN ('human', 'configuration', 'agent')),
  CONSTRAINT attribution_human_actor CHECK (
    actor_kind <> 'human'
    OR (
      principal IS NOT NULL
      AND credential_kind IN ('signIn', 'environmentCredential')
      AND credential_id IS NOT NULL
      AND registration IS NULL
      AND instance IS NULL
      AND sponsor IS NULL
    )
  ),
  CONSTRAINT attribution_configuration_actor CHECK (
    actor_kind <> 'configuration'
    OR (
      principal IS NULL
      AND credential_kind IS NULL
      AND credential_id IS NULL
      AND registration IS NULL
      AND instance IS NULL
      AND sponsor IS NULL
    )
  ),
  CONSTRAINT attribution_agent_actor CHECK (
    actor_kind <> 'agent'
    OR (registration IS NOT NULL AND instance IS NOT NULL AND sponsor IS NOT NULL)
  ),
  CONSTRAINT attribution_envelope_all_or_none CHECK (
    (chain IS NULL AND origin IS NULL AND rebroadening_load_bearing IS NULL)
    OR (chain IS NOT NULL AND origin IS NOT NULL AND rebroadening_load_bearing IS NOT NULL)
  ),
  CONSTRAINT attribution_envelope_agent_only CHECK (chain IS NULL OR actor_kind = 'agent'),
  CONSTRAINT attribution_chain_array CHECK (chain IS NULL OR jsonb_typeof(chain) = 'array'),
  CONSTRAINT attribution_hop_when_load_bearing CHECK (
    rebroadening_hop IS NULL
    OR (
      rebroadening_load_bearing IS TRUE
      AND rebroadening_hop >= 0
      AND rebroadening_hop < jsonb_array_length(chain)
    )
  ),
  CONSTRAINT attribution_load_bearing_has_hop CHECK (
    rebroadening_load_bearing IS NOT TRUE OR rebroadening_hop IS NOT NULL
  )
);

-- The app role's privileges, and nothing more (Infrastructure Design §6).
REVOKE ALL ON credentials, grants, attribution_records FROM PUBLIC;
GRANT SELECT, INSERT ON credentials TO soorma_env_app;
GRANT UPDATE (expires_at, state, ended_at, ended_by) ON credentials TO soorma_env_app;
GRANT SELECT, INSERT ON grants TO soorma_env_app;
GRANT SELECT, INSERT ON attribution_records TO soorma_env_app;
