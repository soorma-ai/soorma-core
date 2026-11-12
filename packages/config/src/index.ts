// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/config (P9): loads and validates tenancy.yaml, the organization
// level's secrets, an environment's seal keys (U3 NP-02), and an environment's
// S2 part (U4 P-06), and its S3 part (U6 D-ID-AC-10).
export {
  ConfigurationError,
  DEFAULT_SECRETS_DIR,
  loadMigrator,
  loadOrganization,
  listSecrets,
  loadControlGateway,
  loadDataGateway,
  loadEnvironmentMigrator,
  loadSealKeys,
  loadSettings,
  type ControlGatewayConfiguration,
  type ControlGatewayNames,
  type DataGatewayConfiguration,
  type DataGatewayNames,
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
