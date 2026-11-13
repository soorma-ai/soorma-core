-- SPDX-License-Identifier: FSL-1.1-ALv2
--
-- S4's role's privileges, and nothing more (U7 NP-ET-15; D-ID-ET-04; the
-- user's NFR Design Q3 A). soorma_env_ingest is created by env-roles.sql, as
-- the other environment roles are. S4 reads agent facts and the sponsor
-- (column-level SELECT on registrations, exactly the columns its statements
-- read), reads revocation state at both granularities, and appends
-- attribution records. Nothing on grants, credentials, agent_credentials,
-- registration_secrets, or schema_migrations; no UPDATE or DELETE anywhere.
GRANT SELECT (organization, project, environment, agent, autonomy_declared,
  re_broadening_declaration, standing_permissions, sponsor)
  ON registrations TO soorma_env_ingest;
GRANT SELECT ON credential_revocations, agent_revocations TO soorma_env_ingest;
GRANT INSERT ON attribution_records TO soorma_env_ingest;
