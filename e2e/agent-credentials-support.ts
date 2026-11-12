// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U6's e2e helpers (D-AC-31; D-CG-AC-10, 36): raw HTTPS calls to S3 through
// deploy/local/scripts/stack-client.ts (no SDK, no client library); the store
// read as its superuser over the container's local socket; and the test-only
// seeding, as the store's owner (soorma_env_migrator): a registration with a
// secret from U5's real generator, for U6's own e2e cases, and revocation,
// which has no product writer in M1 (PF FR-011 deferred). Never in an image.
import { generateRegistrationSecret } from '../packages/registry/src/index.ts';
import {
  agentCredentialOf,
  bootstrapAgent,
  COMPOSE,
  docker,
  dockerWithInput,
  renewAgent,
  type Reply,
} from '../deploy/local/scripts/stack-client.ts';

export { agentCredentialOf, bootstrapAgent, renewAgent, type Reply };

export type Env = 'e' | 'e2';
export const SPONSOR = 'h@example.com';

/** A token's claims, read without verifying (the test reads the stack's own tokens). */
export function claims(token: string): Record<string, unknown> {
  const payload = token.slice('soorma_ac_'.length).split('.')[1] ?? '';
  return JSON.parse(Buffer.from(payload, 'base64url').toString('utf8')) as Record<string, unknown>;
}

export const json = (r: Reply): unknown =>
  r.body.length > 0 ? (JSON.parse(r.body) as unknown) : undefined;

/** A literal for a value the test made itself (identifiers of base36 and dashes). */
const literal = (value: string): string => `'${value.replace(/'/g, "''")}'`;

/** psql in {env}-db as postgres over its local socket (peer); the statement on stdin. */
export function sql(env: Env, statement: string): string {
  const r = dockerWithInput(
    [
      ...COMPOSE,
      'exec',
      '-T',
      `${env}-db`,
      'psql',
      '-X',
      '-q',
      '-At',
      '-v',
      'ON_ERROR_STOP=1',
      '-U',
      'postgres',
      '-d',
      'soorma_env',
    ],
    statement,
  );
  if (r.status !== 0) throw new Error(`psql in ${env}-db: ${r.stderr}`);
  return r.stdout;
}

/** As the store's owner (soorma_env_migrator), in one transaction. */
const asOwner = (env: Env, statements: string): string =>
  sql(env, `BEGIN; SET LOCAL ROLE soorma_env_migrator; ${statements} COMMIT;`);

/**
 * Seeds a registration of `agent` in `env`, sponsored by H, with one active
 * secret from U5's generator; returns the secret's value (D-CG-AC-10, 36).
 */
export function seedRegistration(env: Env, agent: string): string {
  const s = generateRegistrationSecret();
  const scope = `'o1', 'p1', ${literal(env)}`;
  asOwner(
    env,
    `INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES (${scope}, ${literal(agent)}, ${literal(SPONSOR)}, '{}', '{}', '{}', true, now(), 'registered');
     INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES (${literal(s.id)}, ${scope}, ${literal(agent)}, ${literal(SPONSOR)},
       decode(${literal(s.digest.toString('hex'))}, 'hex'), now(), 'active');`,
  );
  return s.value;
}

/** Revokes one credential lineage (its cid), as the owner (D-AC-16; test-only). */
export function seedCredentialRevocation(env: Env, cid: string): void {
  asOwner(
    env,
    `INSERT INTO credential_revocations (organization, project, environment, credential, revoked_at)
     VALUES ('o1', 'p1', ${literal(env)}, ${literal(cid)}, now());`,
  );
}

/** Revokes a logical agent, as the owner (D-AC-16; test-only). */
export function seedAgentRevocation(env: Env, agent: string): void {
  asOwner(
    env,
    `INSERT INTO agent_revocations (organization, project, environment, agent, revoked_at)
     VALUES ('o1', 'p1', ${literal(env)}, ${literal(agent)}, now());`,
  );
}

/** S3's security events since `since`, from its JSON log. */
export function events(service: string, since: string): Record<string, unknown>[] {
  return docker([...COMPOSE, 'logs', '--no-color', '--no-log-prefix', '--since', since, service])
    .split('\n')
    .flatMap((line) => {
      try {
        const m = (JSON.parse(line) as { message?: Record<string, unknown> }).message;
        return m?.event ? [m] : [];
      } catch {
        return [];
      }
    });
}

export interface DoneWhenTwo {
  bootstraps: Reply[];
  renewals: Reply[];
  /** agent_credentials rows for the agents. */
  credentialRecords: number;
  /** Their attribution records for the two operations. */
  attribution: {
    operation: string;
    actor: string;
    registration: string;
    instance: string;
    sponsor: string;
    noChain: boolean;
  }[];
}

/**
 * *Done when* 2 (TC-AC-093; D-AC-31): each instance bootstraps at E's S3 with
 * its agent's registration secret, then renews, by raw calls; then the
 * records those calls wrote. The caller asserts.
 */
export async function doneWhenTwo(
  instances: readonly { agent: string; secret: string; instance: string }[],
): Promise<DoneWhenTwo> {
  const bootstraps: Reply[] = [];
  const renewals: Reply[] = [];
  for (const { agent, secret, instance } of instances) {
    const b = await bootstrapAgent('e', agent, secret, instance);
    bootstraps.push(b);
    renewals.push(await renewAgent('e', agentCredentialOf(b)));
  }
  const agents = instances.map((i) => literal(i.agent)).join(', ');
  const credentialRecords = Number(
    sql('e', `SELECT count(*) FROM agent_credentials WHERE agent IN (${agents});`),
  );
  const attribution = sql(
    'e',
    `SELECT operation, actor_kind, registration, instance, sponsor,
            (chain IS NULL AND origin IS NULL)::text
       FROM attribution_records
      WHERE registration IN (${agents})
        AND operation IN ('exchangeBootstrap', 'renewAgentCredential')
      ORDER BY registration, recorded_at;`,
  )
    .split('\n')
    .filter((l) => l.length > 0)
    .map((l) => {
      const [operation, actor, registration, instance, sponsor, noChain] = l.split('|');
      return {
        operation: operation!,
        actor: actor!,
        registration: registration!,
        instance: instance!,
        sponsor: sponsor!,
        noChain: noChain === 'true',
      };
    });
  return { bootstraps, renewals, credentialRecords, attribution };
}
