// SPDX-License-Identifier: FSL-1.1-ALv2
//
// @soorma/config (P9, organization half): loads and validates tenancy.yaml and
// the organization level's secrets.
export {
  ConfigurationError,
  DEFAULT_SECRETS_DIR,
  loadMigrator,
  loadOrganization,
  listSecrets,
  loadSettings,
  type Environment,
  type FirstAdmin,
  type GatewaySecrets,
  type LoadOptions,
  type MigratorSecrets,
  type OrganizationSettings,
  type Project,
  type SecretNames,
} from './tenancy.ts';
