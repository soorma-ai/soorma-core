// SPDX-License-Identifier: FSL-1.1-ALv2
//
// {env}-migrate (NFR-EHA-14): a one-shot service that runs before its
// environment's S2, as soorma_env_migrator, under the environment's own
// migration advisory lock, and exits. It reads the migrator password and the
// CA only, never S2's secrets.
import { ConfigurationError, loadEnvironmentMigrator } from '@soorma/config';
import { runMigrations } from '@soorma/env-store';
import { MigrationError } from '@soorma/service-kit';

export async function migrateStore(options: {
  project: string;
  environment: string;
  configPath: string;
  secretsDir?: string;
}): Promise<string[]> {
  const m = loadEnvironmentMigrator(
    {
      configPath: options.configPath,
      ...(options.secretsDir === undefined ? {} : { secretsDir: options.secretsDir }),
    },
    { project: options.project, environment: options.environment },
  );
  return runMigrations({
    host: m.database.host,
    port: m.database.port,
    database: m.database.name,
    user: m.database.user,
    password: m.databasePassword,
    ca: m.databaseCa,
  });
}

if (import.meta.main) {
  const project = process.env.SOORMA_PROJECT;
  const environment = process.env.SOORMA_ENVIRONMENT;
  if (!project || !environment) {
    console.error('SOORMA_PROJECT and SOORMA_ENVIRONMENT name the environment to migrate');
    process.exit(1);
  }
  migrateStore({
    project,
    environment,
    configPath: process.env.SOORMA_CONFIG ?? '/etc/soorma/tenancy.yaml',
    ...(process.env.SOORMA_SECRETS_DIR ? { secretsDir: process.env.SOORMA_SECRETS_DIR } : {}),
  })
    .then((applied) => {
      console.log(JSON.stringify({ notice: 'migrations.applied', count: applied.length }));
    })
    .catch((error: unknown) => {
      const safe = error instanceof ConfigurationError || error instanceof MigrationError;
      console.error(safe ? error.message : 'migration failed');
      process.exit(1);
    });
}
