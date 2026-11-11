// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S2 control-gateway's start-up (logical-components §1): configuration and
// secrets for its own environment only (P9), E's key ring (NP-EHA-02), the
// store as the app role (synchronous_commit asserted), the configured first
// grant (NP-EHA-08), the verify-key cache started without blocking
// (NP-EHA-03), then the edge and health listeners. A failure in any step
// before listening stops start-up (D-EHA-28). S2 does not wait for the
// organization level: until a verify-key fetch succeeds, only issuance is
// unavailable (BR-IS-02).
import { createPrivateKey, type KeyObject } from 'node:crypto';
import {
  ConfigurationError,
  loadControlGateway,
  type ControlGatewayConfiguration,
} from '@soorma/config';
import { loadEnvironmentKeyRing } from '@soorma/credentials';
import { connectEnvStore, SQL } from '@soorma/env-store';
import {
  asSecretBytes,
  globalTimers,
  KeyMaterialError,
  listenHealth,
  Semaphore,
  systemClock,
} from '@soorma/service-kit';
import { createEdgeApp } from './apps.ts';
import { ContractValidator } from './contract-validator.ts';
import { applyConfiguredFirstGrant } from './first-grant.ts';
import { OrgLevelClient } from './org-level.ts';
import { assembleRuntime } from './runtime.ts';
import { SecurityLog } from './security-log.ts';
import {
  PERMIT_WAIT_MS,
  REQUEST_PERMITS,
  RETRY_AFTER_SECONDS,
  S1_CALL_PERMITS,
} from './settings.ts';
import { VerifyKeyCache } from './verify-keys.ts';

export const DEFAULT_CONFIG = '/etc/soorma/tenancy.yaml';

export interface Started {
  stop(): Promise<void>;
}

/** E's caller key: an Ed25519 private key, or start-up stops. */
function callerKey(pem: Buffer): KeyObject {
  let key: KeyObject;
  try {
    key = createPrivateKey(asSecretBytes(pem));
  } catch {
    throw new KeyMaterialError(['the caller key is not a PEM private key']);
  }
  if (key.asymmetricKeyType !== 'ed25519')
    throw new KeyMaterialError(['the caller key is not an Ed25519 key']);
  return key;
}

export async function start(options: {
  project: string;
  environment: string;
  configPath?: string;
  secretsDir?: string;
  log?: SecurityLog;
}): Promise<Started> {
  const log = options.log ?? new SecurityLog();
  const { settings, secrets }: ControlGatewayConfiguration = loadControlGateway(
    {
      configPath: options.configPath ?? DEFAULT_CONFIG,
      ...(options.secretsDir === undefined ? {} : { secretsDir: options.secretsDir }),
    },
    { project: options.project, environment: options.environment },
  );
  const ring = loadEnvironmentKeyRing({
    signing: secrets.signing,
    verify: secrets.verifyKeys.map((k) => ({ name: k.name, pem: asSecretBytes(k.pem) })),
  });
  const caller = callerKey(secrets.callerKey);
  const store = connectEnvStore({
    host: settings.database.host,
    port: settings.database.port,
    database: settings.database.name,
    user: settings.database.user,
    password: secrets.databasePassword,
    ca: secrets.databaseCa,
  });
  const [commit] = await store.query<{ synchronous_commit: string }>(SQL.synchronousCommit);
  if (commit?.synchronous_commit !== 'on')
    throw new ConfigurationError(['the environment store must run with synchronous_commit = on']);

  const clock = systemClock;
  const reason = (name: string) => ({ reason: name, retryAfterSeconds: RETRY_AFTER_SECONDS });
  const requests = new Semaphore({
    permits: REQUEST_PERMITS,
    waitMs: PERMIT_WAIT_MS,
    ...reason('requests'),
  });
  const calls = new Semaphore({
    permits: S1_CALL_PERMITS,
    waitMs: PERMIT_WAIT_MS,
    ...reason('s1_calls'),
  });
  const orgLevel = new OrgLevelClient({
    environment: settings.environment,
    organization: settings.organization,
    host: settings.organizationLevel.host,
    port: settings.organizationLevel.port,
    ca: secrets.organizationCa,
    callerKey: caller,
    clock,
    calls,
    timers: globalTimers,
  });
  const keys = new VerifyKeyCache({ fetch: () => orgLevel.verifyKeys(), clock, log });
  const runtime = assembleRuntime({
    environment: {
      organization: settings.organization,
      project: settings.project,
      environment: settings.environment,
    },
    store,
    ring,
    orgLevel,
    keys,
    clock,
    log,
    validator: new ContractValidator(),
    requests,
    logPseudonymKey: asSecretBytes(secrets.logPseudonymKey),
  });

  await applyConfiguredFirstGrant(runtime, settings.firstAdmin);
  keys.start();

  const edge = await createEdgeApp(runtime, { pem: secrets.edgeTls });
  await edge.listen(settings.edge.port, '0.0.0.0');
  const health = await listenHealth(settings.health.port);
  log.notice('started');

  return {
    async stop() {
      log.notice('stopping');
      keys.stop();
      health.close();
      await edge.close();
      orgLevel.close();
      await store.close();
    },
  };
}

/** Start-up errors whose messages carry no secret, by construction. */
const SAFE_ERRORS = [ConfigurationError, KeyMaterialError];

if (import.meta.main) {
  const log = new SecurityLog();
  const project = process.env.SOORMA_PROJECT;
  const environment = process.env.SOORMA_ENVIRONMENT;
  if (!project || !environment) {
    console.error('SOORMA_PROJECT and SOORMA_ENVIRONMENT name the environment this S2 serves');
    process.exit(1);
  }
  start({
    project,
    environment,
    ...(process.env.SOORMA_CONFIG ? { configPath: process.env.SOORMA_CONFIG } : {}),
    ...(process.env.SOORMA_SECRETS_DIR ? { secretsDir: process.env.SOORMA_SECRETS_DIR } : {}),
    log,
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
