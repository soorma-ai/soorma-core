// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S3 data-gateway's start-up (U6; NFR Design logical-components §7; as S2's,
// D-CG-AC-08): configuration and secrets for its own environment only (P9;
// D-ID-AC-09, 10), E's agent key ring (D-AC-03), the store as soorma_env_data
// (D-ID-AC-07; synchronous_commit asserted), the Failed Bootstrap Attempt
// writer, then the edge and health listeners. A failure in any step before
// listening stops start-up. S3 never calls the organization level: it has no
// client for it, and starts and serves with S1 stopped (D-AC-11).
import { loadDataGateway, ConfigurationError, type DataGatewayConfiguration } from '@soorma/config';
import { loadEnvironmentKeyRing } from '@soorma/credentials';
import { connectEnvStore, SQL } from '@soorma/env-store';
import {
  asSecretBytes,
  KeyMaterialError,
  type ConnectionSettings,
  listenHealth,
  Semaphore,
  systemClock,
} from '@soorma/service-kit';
import { createEdgeApp } from './apps.ts';
import { ContractValidator } from './contract-validator.ts';
import { assembleRuntime } from './runtime.ts';
import { SecurityLog } from './security-log.ts';
import { PERMIT_WAIT_MS, REQUEST_PERMITS, RETRY_AFTER_SECONDS } from './settings.ts';

export const DEFAULT_CONFIG = '/etc/soorma/tenancy.yaml';

export interface Started {
  stop(): Promise<void>;
}

/**
 * The store connection S3 opens (D-ID-AC-07; NFR-AC-21): its own role, and the
 * stack CA, so service-kit's pool connects with TLS 1.3, verify-full.
 */
export function storeSettings(
  settings: DataGatewayConfiguration['settings'],
  secrets: DataGatewayConfiguration['secrets'],
): ConnectionSettings {
  return {
    host: settings.database.host,
    port: settings.database.port,
    database: settings.database.name,
    user: settings.database.user,
    password: secrets.databasePassword,
    ca: secrets.databaseCa,
  };
}

export async function start(options: {
  project: string;
  environment: string;
  configPath?: string;
  secretsDir?: string;
  log?: SecurityLog;
}): Promise<Started> {
  const { settings, secrets }: DataGatewayConfiguration = loadDataGateway(
    {
      configPath: options.configPath ?? DEFAULT_CONFIG,
      ...(options.secretsDir === undefined ? {} : { secretsDir: options.secretsDir }),
    },
    { project: options.project, environment: options.environment },
  );
  const log = options.log ?? new SecurityLog(undefined, settings.environment);
  const ring = loadEnvironmentKeyRing({
    signing: secrets.signing,
    verify: secrets.verifyKeys.map((k) => ({ name: k.name, pem: asSecretBytes(k.pem) })),
  });
  const store = connectEnvStore(storeSettings(settings, secrets));
  const [commit] = await store.query<{ synchronous_commit: string }>(SQL.synchronousCommit);
  if (commit?.synchronous_commit !== 'on')
    throw new ConfigurationError(['the environment store must run with synchronous_commit = on']);

  const runtime = assembleRuntime({
    environment: {
      organization: settings.organization,
      project: settings.project,
      environment: settings.environment,
    },
    store,
    ring,
    counterSecret: asSecretBytes(secrets.counterSecret),
    clock: systemClock,
    log,
    validator: new ContractValidator(),
    requests: new Semaphore({
      permits: REQUEST_PERMITS,
      waitMs: PERMIT_WAIT_MS,
      reason: 'requests',
      retryAfterSeconds: RETRY_AFTER_SECONDS,
    }),
  });
  runtime.attempts.start();

  const edge = await createEdgeApp(runtime, { pem: secrets.edgeTls });
  await edge.listen(settings.edge.port, '0.0.0.0');
  const health = await listenHealth(settings.health.port);
  log.notice('started');

  return {
    async stop() {
      log.notice('stopping');
      health.close();
      await edge.close();
      await runtime.attempts.stop();
      await store.close();
    },
  };
}

/** Start-up errors whose messages carry no secret, by construction. */
const SAFE_ERRORS = [ConfigurationError, KeyMaterialError];

if (import.meta.main) {
  const project = process.env.SOORMA_PROJECT;
  const environment = process.env.SOORMA_ENVIRONMENT;
  if (!project || !environment) {
    console.error('SOORMA_PROJECT and SOORMA_ENVIRONMENT name the environment this S3 serves');
    process.exit(1);
  }
  start({
    project,
    environment,
    ...(process.env.SOORMA_CONFIG ? { configPath: process.env.SOORMA_CONFIG } : {}),
    ...(process.env.SOORMA_SECRETS_DIR ? { secretsDir: process.env.SOORMA_SECRETS_DIR } : {}),
  })
    .then((started) => {
      let stopping = false;
      const stop = (): void => {
        if (stopping) return;
        stopping = true;
        started.stop().then(
          () => process.exit(0),
          () => process.exit(1),
        );
      };
      process.once('SIGTERM', stop);
      process.once('SIGINT', stop);
    })
    .catch((error: unknown) => {
      const safe = SAFE_ERRORS.some((E) => error instanceof E);
      console.error(safe ? (error as Error).message : 'start-up failed');
      process.exit(1);
    });
}
