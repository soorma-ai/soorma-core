// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S4 event-ingest's start-up (NP-ET-01, 05, 17; logical-components §1):
// first the JSON.rawJSON self-check (no fallback); then configuration and
// secrets for its own environment only (P9's loadEventIngest); E's agent
// verify halves (P5's verify-only ring: no signing key); E's seal ring; the
// store as soorma_env_ingest (synchronous_commit asserted); then the edge and
// health listeners and the sweep. A failure in any step before listening
// stops start-up. S4 never calls the organization level: it has no client for
// it, and starts and serves with S1 stopped (D-ET-23).
//
// Shutdown (NFR-ET-11; BR-SM-08): the edge stops taking requests, every
// stream ends with `end` `unavailable`, the sockets get up to 5 seconds, then
// the store closes.
import type { NestFastifyApplication } from '@nestjs/platform-fastify';
import { ConfigurationError, loadEventIngest, type EventIngestConfiguration } from '@soorma/config';
import { loadSealKeyRing } from '@soorma/authority';
import { loadVerifyKeyRing } from '@soorma/credentials';
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
import { checkRawJson } from './raw-json-check.ts';
import { assembleRuntime, type Runtime } from './runtime.ts';
import { systemScheduler } from './scheduler.ts';
import { SecurityLog } from './security-log.ts';
import { PERMIT_WAIT_MS, REQUEST_PERMITS, RETRY_AFTER_SECONDS, SHUTDOWN_MS } from './settings.ts';

export const DEFAULT_CONFIG = '/etc/soorma/tenancy.yaml';

export interface Started {
  stop(): Promise<void>;
}

/** The store connection S4 opens: its own role, and the stack CA (TLS 1.3, verify-full). */
export function storeSettings(
  settings: EventIngestConfiguration['settings'],
  secrets: EventIngestConfiguration['secrets'],
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

const within = (ms: number, work: Promise<unknown>): Promise<unknown> =>
  Promise.race([work, new Promise((resolve) => setTimeout(resolve, ms).unref())]);

/**
 * Shutdown's order (NFR-ET-11; BR-SM-08): the edge stops taking requests,
 * every stream ends with `end` `unavailable`, the sockets get up to `waitMs`,
 * then the sweep stops.
 */
export async function drain(
  edge: NestFastifyApplication,
  runtime: Runtime,
  waitMs = SHUTDOWN_MS,
): Promise<void> {
  const closing = edge.close();
  runtime.streams.endAll('unavailable');
  await within(waitMs, closing);
  runtime.stop();
}

export async function start(options: {
  project: string;
  environment: string;
  configPath?: string;
  secretsDir?: string;
  log?: SecurityLog;
}): Promise<Started> {
  // Before anything else: no runtime that converts payload numbers runs S4.
  checkRawJson();
  const { settings, secrets }: EventIngestConfiguration = loadEventIngest(
    {
      configPath: options.configPath ?? DEFAULT_CONFIG,
      ...(options.secretsDir === undefined ? {} : { secretsDir: options.secretsDir }),
    },
    { project: options.project, environment: options.environment },
  );
  const log = options.log ?? new SecurityLog(undefined, settings.environment);
  const ring = loadVerifyKeyRing({
    verify: secrets.agentVerifyKeys.map((k) => ({ name: k.name, pem: asSecretBytes(k.pem) })),
  });
  const sealKeys = loadSealKeyRing({
    current: secrets.sealKeys.current,
    keys: secrets.sealKeys.keys,
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
    sealKeys,
    clock: systemClock,
    scheduler: systemScheduler,
    log,
    requests: new Semaphore({
      permits: REQUEST_PERMITS,
      waitMs: PERMIT_WAIT_MS,
      reason: 'requests',
      retryAfterSeconds: RETRY_AFTER_SECONDS,
    }),
  });

  const edge = await createEdgeApp(runtime, { pem: secrets.edgeTls });
  await edge.listen(settings.edge.port, '0.0.0.0');
  const health = await listenHealth(settings.health.port);
  runtime.start();
  log.notice('started');

  return {
    async stop() {
      log.notice('stopping');
      health.close();
      await drain(edge, runtime);
      await store.close();
    },
  };
}

/**
 * Start-up errors whose messages carry no secret, by construction. The seal
 * ring's error is known by name: S4 imports nothing of P3 but the allowlist
 * (NP-ET-03), and its message names key ids and sizes only.
 */
const SAFE_ERRORS = [ConfigurationError, KeyMaterialError];
const SAFE_NAMES = new Set(['SealKeyRingError']);

if (import.meta.main) {
  const project = process.env.SOORMA_PROJECT;
  const environment = process.env.SOORMA_ENVIRONMENT;
  if (!project || !environment) {
    console.error('SOORMA_PROJECT and SOORMA_ENVIRONMENT name the environment this S4 serves');
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
      const safe =
        SAFE_ERRORS.some((E) => error instanceof E) ||
        (error instanceof Error && SAFE_NAMES.has(error.name));
      console.error(safe ? (error as Error).message : 'start-up failed');
      process.exit(1);
    });
}
