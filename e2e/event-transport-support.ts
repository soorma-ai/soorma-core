// SPDX-License-Identifier: FSL-1.1-ALv2
//
// U7's e2e helpers (D-ET-34; NP-ET-18): raw HTTPS publish and subscribe at
// each environment's S4 through deploy/local/scripts/stack-client.ts (no SDK,
// no client library), an SSE reader of `delivery` and `end` events, and
// seeding for U7's own e2e file only, as the store's owner: a registration
// with its standing set, declaration, and autonomy, and a secret from U5's
// real generator; an instance's credential then comes from that environment's
// S3. Never in an image. Done when 3, 4, 6, 7 use none of the seeding: they
// chain from U5's and U6's real registrations and credentials.
import { readFileSync } from 'node:fs';
import { request } from 'node:https';
import { join } from 'node:path';
import { canonicalize } from '../packages/jcs/src/index.ts';
import { createSealer, loadSealKeyRing } from '../packages/envelope/src/index.ts';
import { generateRegistrationSecret } from '../packages/registry/src/index.ts';
import {
  agentCredentialOf,
  bootstrapAgent,
  draft,
  EVENT_INGEST,
  publishAt,
  SECRETS,
  subscribeAt,
  type EventStream,
  type Reply,
} from '../deploy/local/scripts/stack-client.ts';
import { claims, sql, SPONSOR, type Env } from './agent-credentials-support.ts';

export { draft, EVENT_INGEST, publishAt, subscribeAt, type EventStream, type Reply };

/** A literal for a value the test made itself (identifiers of base36 and dashes). */
const literal = (value: string): string => `'${value.replace(/'/g, "''")}'`;
const array = (xs: readonly string[]): string => `ARRAY[${xs.map(literal).join(', ')}]::text[]`;

/** What a seeded registration holds (U5's columns). */
export interface Seed {
  standing: string[];
  declaration?: string[];
  autonomy?: boolean;
}

/**
 * Seeds a registration of `agent` in `env`, sponsored by H, as the store's
 * owner, with one active secret from U5's generator; returns the secret's value.
 */
export function seedAgent(env: Env, agent: string, seed: Seed): string {
  const s = generateRegistrationSecret();
  const scope = `'o1', 'p1', ${literal(env)}`;
  sql(
    env,
    `BEGIN; SET LOCAL ROLE soorma_env_migrator;
     INSERT INTO registrations (organization, project, environment, agent, sponsor,
       ceiling_snapshot, standing_permissions, re_broadening_declaration, autonomy_declared,
       registered_at, state)
     VALUES (${scope}, ${literal(agent)}, ${literal(SPONSOR)}, ${array(seed.standing)},
       ${array(seed.standing)}, ${array(seed.declaration ?? [])}, ${seed.autonomy ?? true}, now(),
       'registered');
     INSERT INTO registration_secrets (id, organization, project, environment, registration,
       issuer, digest, issued_at, state)
     VALUES (${literal(s.id)}, ${scope}, ${literal(agent)}, ${literal(SPONSOR)},
       decode(${literal(s.digest.toString('hex'))}, 'hex'), now(), 'active');
     COMMIT;`,
  );
  return s.value;
}

/** An instance's agent credential from `env`'s S3, and its lineage. */
export interface Instance {
  agent: string;
  instance: string;
  token: string;
  cid: string;
}

export async function instanceOf(
  env: Env,
  agent: string,
  secret: string,
  instance = 'i-1',
): Promise<Instance> {
  const token = agentCredentialOf(await bootstrapAgent(env, agent, secret, instance));
  if (!token) throw new Error(`bootstrap of ${agent} in ${env}`);
  return { agent, instance, token, cid: String(claims(token).cid) };
}

/** A seeded agent with one instance's credential. */
export async function seededInstance(
  env: Env,
  agent: string,
  seed: Seed,
  instance = 'i-1',
): Promise<Instance> {
  return instanceOf(env, agent, seedAgent(env, agent, seed), instance);
}

/** A Delivery as read off a stream. */
export interface ReadDelivery {
  envelope: Record<string, unknown> & {
    scope: Record<string, unknown>;
    actorChain: unknown[];
    originMode: unknown;
  };
  seal: string;
  payload: unknown;
  raw: string;
}

export function deliveries(stream: EventStream): ReadDelivery[] {
  return stream.events
    .filter((e) => e.event === 'delivery')
    .map((e) => ({ ...(JSON.parse(e.data) as Omit<ReadDelivery, 'raw'>), raw: e.data }));
}

export function ended(stream: EventStream): { code: string } | undefined {
  const end = stream.events.find((e) => e.event === 'end');
  return end ? (JSON.parse(end.data) as { code: string }) : undefined;
}

/** A publish whose body is the given text exactly (numbers, duplicates, spacing as written). */
export function publishRaw(env: Env, token: string, text: string): Promise<Reply> {
  const ca = readFileSync(join(SECRETS, 'stack-ca.pem'));
  return new Promise((done, fail) => {
    const req = request(
      {
        host: 'localhost',
        port: EVENT_INGEST[env],
        path: '/events',
        method: 'POST',
        agent: false,
        ca,
        headers: {
          'soorma-contract-version': '0.1.0',
          'content-type': 'application/json',
          'content-length': Buffer.byteLength(text),
          authorization: `Bearer ${token}`,
        },
      },
      (res) => {
        let body = '';
        res.on('data', (c: Buffer) => (body += c.toString()));
        res.on('end', () =>
          done({
            status: res.statusCode ?? 0,
            body,
            protocol: (res.socket as { getProtocol?: () => string | null }).getProtocol?.() ?? null,
            retryAfter: undefined,
            headers: res.headers,
          }),
        );
      },
    );
    req.on('error', fail);
    req.end(text);
  });
}

/** A forwarding draft: `inbound` from a Delivery. */
export const forwarding = (d: { envelope: unknown; seal: string }): Record<string, unknown> => ({
  ...draft(),
  inbound: { envelope: d.envelope, seal: d.seal },
});

/**
 * Seals an envelope with `env`'s own seal key, read from the stack's secrets
 * directory, as S4 would (test-only: the local stack's throwaway key). Used
 * where a case needs a forwarded envelope S4 could not have produced: an
 * unknown field at its top level, or a chain at maxChainDepth.
 */
export function sealAs(env: Env, envelope: Record<string, unknown>): string {
  const key = Buffer.from(
    readFileSync(join(SECRETS, `${env}-seal-key-1`), 'utf8').trim(),
    'base64url',
  );
  const sealer = createSealer(loadSealKeyRing({ current: 's1', keys: [{ id: 's1', key }] }));
  return sealer.seal(canonicalize(envelope).bytes);
}

/** The attribution rows of one agent in `env`, oldest first, as JSON objects. */
/** One attribution_records row, as JSON. */
export interface AttributionRow {
  [column: string]: unknown;
  operation: string;
  registration: string;
  instance: string;
  credential_id: string;
}

export function records(env: Env, agent: string, operation?: string): AttributionRow[] {
  const where = operation === undefined ? '' : ` AND operation = ${literal(operation)}`;
  const text = sql(
    env,
    `SELECT coalesce(json_agg(r ORDER BY recorded_at, id), '[]') FROM attribution_records r
     WHERE registration = ${literal(agent)}${where};`,
  );
  return JSON.parse(text) as AttributionRow[];
}

/** S4's records of one agent (publish and subscribe): its S3 bootstrap's record left out. */
export const ingestRecords = (env: Env, agent: string): AttributionRow[] =>
  records(env, agent).filter((r) => r.operation === 'publish' || r.operation === 'subscribe');
