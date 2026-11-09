// SPDX-License-Identifier: FSL-1.1-ALv2
//
// org-migrate (D-ID-OI-02; NFR-OI-18): a one-shot service that runs before
// S1, as the migrator role, under the migration advisory lock, and exits.
// It reads the migrator password and the CA only, never S1's secrets.
import { ConfigurationError, loadMigrator } from '@soorma/config';
import { MigrationError, runMigrations } from '@soorma/org-identity';

export async function migrateStore(options: {
  configPath: string;
  secretsDir?: string;
}): Promise<string[]> {
  const { settings, secrets } = loadMigrator(options);
  return runMigrations({
    host: settings.database.host,
    port: settings.database.port,
    database: settings.database.name,
    user: settings.migrator.user,
    password: secrets.databasePassword,
    ca: secrets.databaseCa,
  });
}

if (import.meta.main) {
  migrateStore({
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
