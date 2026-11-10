// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/config (P9): loads and validates tenancy.yaml, the organization
// level's secrets, and an environment's seal keys (U3 NP-02).
export {
  ConfigurationError,
  DEFAULT_SECRETS_DIR,
  loadMigrator,
  loadOrganization,
  listSecrets,
  loadSealKeys,
  loadSettings,
  type Environment,
  type FirstAdmin,
  type GatewaySecrets,
  type LoadOptions,
  type MigratorSecrets,
  type OrganizationSettings,
  type Project,
  type SealKeyNames,
  type SealKeys,
  type SecretNames,
} from './tenancy.ts';
