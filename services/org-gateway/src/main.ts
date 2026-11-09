// SPDX-License-Identifier: FSL-1.1-ALv2
//
// S1 org-gateway's entry point (business-logic-model §2.1; P-07):
//   1. load the configuration and S1's secrets; any error stops start-up
//      (BR-CFG-08). S1 never reads the migrator password (D-ID-OI-02)
//   2. build the key ring, the store (app role, TLS verify-full), the hasher
//      and its decoy, and the breached list (digest-checked)
//   3. register any absent first Admin; log ignored material by pseudonym only
//      (BR-CFG-04), and drop the plain enrollment material (BR-CFG-09)
//   4. start the edge, internal, and health listeners, the Failed Attempt
//      writer, and the pruner; on SIGTERM or SIGINT, stop them and flush
//
// Paths, not secrets, come from the environment: SOORMA_CONFIG (tenancy.yaml),
// SOORMA_SECRETS_DIR (default /run/secrets), SOORMA_BREACHED_DIR.
import { AbuseBound, FailedAttemptWriter } from '@soorma/abuse-bound';
import { ConfigurationError, loadOrganization } from '@soorma/config';
import { StoreIdentityResolver } from '@soorma/identity-resolution';
import {
  asSecretText,
  BreachedList,
  BreachedListError,
  defaultPermits,
  FirstAdminError,
  HashSemaphore,
  KeyMaterialError,
  KeyRing,
  Lifetimes,
  OrgIdentity,
  Pruner,
  SecretHasher,
  SecretPolicy,
  SQL,
  Store,
  systemClock,
} from '@soorma/org-identity';
import { createEdgeApp, createInternalApp } from './apps.ts';
import { ContractValidator } from './contract-validator.ts';
import { listenHealth } from './health.ts';
import { assembleRuntime } from './runtime.ts';
import { SecurityLog } from './security-log.ts';

export const DEFAULT_CONFIG = '/etc/soorma/tenancy.yaml';
export const DEFAULT_BREACHED_DIR = '/app/data/breached';

/**
 * S1's hasher: NFR-OI-11's Argon2id parameters, never overridden, behind the
 * semaphore sized by configuration or by P-09's default.
 */
export function productionHasher(hashing: { budgetMiB: number; permits?: number }): SecretHasher {
  return new SecretHasher(new HashSemaphore(hashing.permits ?? defaultPermits(hashing.budgetMiB)));
}

export interface Started {
  stop(): Promise<void>;
}

export async function start(
  options: {
    configPath?: string;
    secretsDir?: string;
    breachedDir?: string;
    log?: SecurityLog;
  } = {},
): Promise<Started> {
  const log = options.log ?? new SecurityLog();
  const { settings, secrets } = loadOrganization({
    configPath: options.configPath ?? DEFAULT_CONFIG,
    ...(options.secretsDir === undefined ? {} : { secretsDir: options.secretsDir }),
  });
  const keys = KeyRing.fromConfiguration(secrets);
  const store = Store.connect({
    ...settings.database,
    database: settings.database.name,
    password: secrets.databasePassword,
    ca: secrets.databaseCa,
  });
  const [commit] = await store.query<{ synchronous_commit: string }>(SQL.synchronousCommit);
  if (commit?.synchronous_commit !== 'on')
    throw new ConfigurationError(['the org store must run with synchronous_commit = on']);

  const hasher = productionHasher(settings.hashing);
  await hasher.prepareDecoy();
  const breached = BreachedList.load(options.breachedDir ?? DEFAULT_BREACHED_DIR);
  const clock = systemClock;
  const writer = new FailedAttemptWriter(store, {
    onDropped: (count) => log.event('failed_attempt.dropped', undefined, { count }),
  });
  const identity = new OrgIdentity({
    organization: settings.organization,
    secondFactorRequired: settings.secondFactorRequired,
    store,
    bound: new AbuseBound(store, keys.counterSecret, clock),
    failures: writer,
    resolver: new StoreIdentityResolver(store, hasher, keys, clock),
    hasher,
    policy: new SecretPolicy(breached),
    keys,
    lifetimes: new Lifetimes(clock),
    clock,
  });
  const runtime = assembleRuntime({
    organization: settings.organization,
    identity,
    keys,
    clock,
    log,
    validator: new ContractValidator(),
  });

  const firstAdmins = await identity.ensureFirstAdmin(
    settings.firstAdmins,
    secrets.enrollment.map((e) => ({ principal: e.principal, material: asSecretText(e.material) })),
  );
  secrets.enrollment.length = 0; // BR-CFG-09: only the one-way form is kept
  for (const reference of firstAdmins.ignored)
    log.event('config.enrollment_ignored', undefined, { pseudonym: runtime.pseudonym(reference) });
  log.notice('first_admin.registered', { count: firstAdmins.registered.length });

  const edge = await createEdgeApp(runtime, { pem: secrets.edgeTls });
  const internal = await createInternalApp(runtime, { pem: secrets.internalTls });
  await edge.listen(settings.edge.port, '0.0.0.0');
  await internal.listen(settings.internal.port, '0.0.0.0');
  const health = await listenHealth(settings.health.port);
  const pruner = new Pruner(store, clock);
  writer.start();
  pruner.start();
  log.notice('started');

  return {
    async stop() {
      log.notice('stopping');
      health.close();
      await edge.close();
      await internal.close();
      pruner.stop();
      await writer.stop();
      await store.close();
    },
  };
}

/** Start-up errors whose messages carry no secret, by construction. */
const SAFE_ERRORS = [ConfigurationError, KeyMaterialError, FirstAdminError, BreachedListError];

if (import.meta.main) {
  const log = new SecurityLog();
  start({
    ...(process.env.SOORMA_CONFIG ? { configPath: process.env.SOORMA_CONFIG } : {}),
    ...(process.env.SOORMA_SECRETS_DIR ? { secretsDir: process.env.SOORMA_SECRETS_DIR } : {}),
    ...(process.env.SOORMA_BREACHED_DIR ? { breachedDir: process.env.SOORMA_BREACHED_DIR } : {}),
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
      if (SAFE_ERRORS.some((E) => error instanceof E)) console.error((error as Error).message);
      else log.error(undefined, error instanceof Error ? error.name : 'start_failed');
      process.exit(1);
    });
}
