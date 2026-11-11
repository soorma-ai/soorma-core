// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/config (P9): loads and validates tenancy.yaml, the organization
// level's secrets, an environment's seal keys (U3 NP-02), and an environment's
// S2 part (U4 P-06).
export {
  ConfigurationError,
  DEFAULT_SECRETS_DIR,
  loadMigrator,
  loadOrganization,
  listSecrets,
  loadControlGateway,
  loadEnvironmentMigrator,
  loadSealKeys,
  loadSettings,
  type ControlGatewayConfiguration,
  type ControlGatewayNames,
  type Environment,
  type EnvironmentMigratorConfiguration,
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
