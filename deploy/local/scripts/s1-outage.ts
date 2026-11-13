// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The S1-stopped demonstration (U4 Infrastructure Design §11; P-09 as changed;
// O-13; TC-EHA-084, TC-EHA-085), run against a freshly started stack
// (`pnpm stack:init && pnpm stack:up`, before any smoke run: it makes the first
// authentication itself):
//
//  Case 1: S1 stops while E's S2 is running and holds the verify keys.
//    Issuance, renewal and grantToHuman answer 503 with Retry-After 5, and S2
//    logs orglevel.unavailable; ending succeeds; a live credential passes O1 to
//    O4 (it then fails at its S1 call); an ended or an E2 credential is refused
//    exactly as with S1 running. After S1 starts, issuance recovers as soon as
//    S1 answers: S2 kept its keys.
//  Case 2: E's S2 starts while S1 is stopped. Issuance answers 503 with
//    Retry-After 5 (no verify keys are loaded); a credential issued before the
//    restart still passes O1 to O4, and can be ended. After S1 starts,
//    issuance recovers on the next fetch, within the 30-second on-demand limit.
//  Case 3 (U6 D-ID-AC-15; TC-AC-017): S3 never needs S1. With S1 stopped, the
//    running e-data-gateway serves a bootstrap and a renewal; restarted while
//    S1 is stopped, it becomes healthy and serves both again.
//  Case 4 (U7 D-ID-ET-11; TC-ET-022): S4 never needs S1. With S1 stopped,
//    the running e-event-ingest serves a subscribe, a publish, and the
//    Delivery; restarted while S1 is stopped, it becomes healthy and serves
//    the round trip again. Its agents are registered through S2 before S1
//    stops, and bootstrapped at S3 after (not a done-when proof)
//
// It leaves S1, both S2s, both S3s, and both S4s running.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import {
  agentCredentialOf,
  bootstrapAgent,
  call,
  check,
  COMPOSE,
  docker,
  failed,
  PRINCIPAL,
  publishAt,
  registeredAgent,
  renewAgent,
  SECRETS,
  subscribeAt,
  type Reply,
} from './stack-client.ts';

const K = `outage ${Date.now().toString(36)} harbour lamp`;
const E = 8442;
const E2 = 8443;

const healthy = (service: string): boolean => {
  const id = docker([...COMPOSE, 'ps', '-q', service]);
  return id !== '' && docker(['inspect', '-f', '{{.State.Health.Status}}', id]) === 'healthy';
};

async function waitHealthy(service: string, seconds: number): Promise<boolean> {
  for (let i = 0; i < seconds; i += 1) {
    if (healthy(service)) return true;
    await sleep(1000);
  }
  return false;
}

/** S2's log lines since `since`, as events. */
function events(
  service: string,
  since: string,
): { event: string; code?: string; requestId?: string }[] {
  return docker([...COMPOSE, 'logs', '--no-color', '--no-log-prefix', '--since', since, service])
    .split('\n')
    .flatMap((line) => {
      try {
        const m = (
          JSON.parse(line) as { message?: { event?: string; code?: string; requestId?: string } }
        ).message;
        return m?.event
          ? [
              {
                event: m.event,
                ...(m.code ? { code: m.code } : {}),
                ...(m.requestId ? { requestId: m.requestId } : {}),
              },
            ]
          : [];
      } catch {
        return [];
      }
    });
}

const unavailable = (r: Reply): boolean => r.status === 503 && r.retryAfter === '5';
const shown = (r: Reply): string => `${r.status}, Retry-After ${r.retryAfter ?? 'none'}`;

async function signIn(): Promise<string> {
  const r = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  return r.status === 200 ? (JSON.parse(r.body) as { signIn: { token: string } }).signIn.token : '';
}

async function issue(signInToken: string, port: number): Promise<Reply> {
  return call('/environment-credentials', { token: signInToken, port });
}

const credentialOf = (r: Reply): string =>
  r.status === 200 ? (JSON.parse(r.body) as { credential: string }).credential : '';

const renew = (credential: string, port = E): Promise<Reply> =>
  call('/environment-credentials/current/renewal', { token: credential, port });
const end = (credential: string, port = E): Promise<Reply> =>
  call('/environment-credentials/current/end', { token: credential, port });
const grant = (credential: string): Promise<Reply> =>
  call('/grants', {
    token: credential,
    port: E,
    body: { target: PRINCIPAL, permissions: ['agent:register'] },
  });

async function main(): Promise<void> {
  // Set-up: the first authentication, a sign-in, and the credentials.
  const handover = readFileSync(join(SECRETS, 'handover', 'first-admin-1.txt'), 'utf8');
  const material = /enrollmentMaterial: (\S+)/.exec(handover)?.[1] ?? '';
  const first = await call('/first-authentication', {
    body: { principal: PRINCIPAL, enrollmentMaterial: material, newSecret: K },
  });
  check('set-up: the first authentication', first.status === 200, String(first.status));
  const token = await signIn();
  check('set-up: a sign-in', token !== '');
  const live = credentialOf(await issue(token, E));
  const toEnd = credentialOf(await issue(token, E));
  const ended = credentialOf(await issue(token, E));
  const fromE2 = credentialOf(await issue(token, E2));
  check(
    'set-up: three credentials for E and one for E2',
    [live, toEnd, ended, fromE2].every((c) => c !== ''),
  );
  check('set-up: one E credential ended', (await end(ended)).status === 204);

  // ---- Case 1: S1 stops under a running S2 (TC-EHA-084). ----
  console.log("Case 1: S1 stops while E's S2 holds the verify keys");
  const since1 = new Date().toISOString();
  docker([...COMPOSE, 'stop', 'org-gateway']);
  const issued1 = await issue(token, E);
  check('issuance: 503, Retry-After 5', unavailable(issued1), shown(issued1));
  const renewed1 = await renew(live);
  check(
    'renewal of a live credential: past O1 to O4, then 503, Retry-After 5',
    unavailable(renewed1),
    shown(renewed1),
  );
  const granted1 = await grant(live);
  check(
    'grantToHuman with a live credential: past O1 to O4, then 503, Retry-After 5',
    unavailable(granted1),
    shown(granted1),
  );
  check(
    'S2 logs orglevel.unavailable',
    events('e-control-gateway', since1).some((e) => e.event === 'orglevel.unavailable'),
  );
  check('ending a credential succeeds (no S1 call)', (await end(toEnd)).status === 204);
  const endedRenewal = await renew(ended);
  check(
    'an ended credential is refused, as with S1 running',
    endedRenewal.status === 401,
    shown(endedRenewal),
  );
  const e2Renewal = await renew(fromE2);
  check(
    "E2's credential is refused at E, as with S1 running",
    e2Renewal.status === 401,
    shown(e2Renewal),
  );
  const e2Grant = await grant(fromE2);
  check("E2's credential is refused at grantToHuman", e2Grant.status === 401, shown(e2Grant));

  docker([...COMPOSE, 'start', 'org-gateway']);
  check('S1 is healthy again', await waitHealthy('org-gateway', 120));
  const recovered1 = await issue(token, E);
  check(
    'issuance recovers as soon as S1 answers (S2 kept its keys)',
    recovered1.status === 200,
    String(recovered1.status),
  );

  // ---- Case 2: E's S2 starts while S1 is stopped (TC-EHA-085). ----
  console.log("Case 2: E's S2 starts while S1 is stopped");
  const before = credentialOf(recovered1);
  docker([...COMPOSE, 'stop', 'org-gateway']);
  docker([...COMPOSE, 'restart', 'e-control-gateway']);
  check("E's S2 starts and is healthy without S1", await waitHealthy('e-control-gateway', 120));
  const since2 = new Date().toISOString();
  const issued2 = await issue(token, E);
  check(
    'issuance: 503, Retry-After 5 (no verify keys loaded)',
    unavailable(issued2),
    shown(issued2),
  );
  check(
    "that request's event is orglevel.unavailable, verify_keys",
    events('e-control-gateway', since2).some(
      (e) => e.event === 'orglevel.unavailable' && e.code === 'verify_keys' && !!e.requestId,
    ),
  );
  const granted2 = await grant(before);
  check(
    'a credential issued before the restart passes O1 to O4 (grantToHuman then 503 at its S1 call)',
    unavailable(granted2),
    shown(granted2),
  );
  check('it can be ended', (await end(before)).status === 204);

  docker([...COMPOSE, 'start', 'org-gateway']);
  check('S1 is healthy again', await waitHealthy('org-gateway', 120));
  // The on-demand fetch is limited to one per 30 seconds; the issuance above
  // used it, so recovery comes within that limit (or at the scheduled refresh).
  const started = Date.now();
  let recovered2: Reply | undefined;
  while (Date.now() - started < 45_000) {
    recovered2 = await issue(token, E);
    if (recovered2.status === 200) break;
    await sleep(2000);
  }
  check(
    'issuance recovers on the next fetch, within the 30-second on-demand limit',
    recovered2?.status === 200,
    `${recovered2?.status ?? 'none'} after ${Math.round((Date.now() - started) / 1000)} s`,
  );

  // ---- Case 3: S3 with S1 stopped (U6 TC-AC-017). ----
  console.log('Case 3: S3 serves bootstrap and renewal while S1 is stopped');
  const admin = credentialOf(await issue(token, E));
  check('set-up: agent:register granted', (await grant(admin)).status === 200);
  const agent = `outage-${Date.now().toString(36)}`;
  const secret = await registeredAgent(admin, 'e', agent);
  check('set-up: an agent of E with a registration secret', secret !== '');
  docker([...COMPOSE, 'stop', 'org-gateway']);
  const booted3a = await bootstrapAgent('e', agent, secret, 'i-1');
  check('(a) the running S3 serves a bootstrap', booted3a.status === 200, shown(booted3a));
  const renewed3a = await renewAgent('e', agentCredentialOf(booted3a));
  check('(a) and a renewal', renewed3a.status === 200, shown(renewed3a));
  docker([...COMPOSE, 'restart', 'e-data-gateway']);
  check('(b) S3 restarted without S1 is healthy', await waitHealthy('e-data-gateway', 120));
  const booted3b = await bootstrapAgent('e', agent, secret, 'i-2');
  check('(b) it serves a bootstrap', booted3b.status === 200, shown(booted3b));
  const renewed3b = await renewAgent('e', agentCredentialOf(booted3b));
  check('(b) and a renewal', renewed3b.status === 200, shown(renewed3b));
  docker([...COMPOSE, 'start', 'org-gateway']);
  check('S1 is healthy again', await waitHealthy('org-gateway', 120));

  // ---- Case 4: S4 with S1 stopped (U7 D-ID-ET-11; TC-ET-022). ----
  console.log('Case 4: S4 serves publish, subscribe, and delivery while S1 is stopped');
  const admin4 = credentialOf(await issue(token, E));
  const eventGrant = await call('/grants', {
    token: admin4,
    port: E,
    body: { target: PRINCIPAL, permissions: ['event:publish', 'event:subscribe'] },
  });
  check('set-up: event:publish and event:subscribe granted', eventGrant.status === 200);
  const pubAgent = `outage-a-${Date.now().toString(36)}`;
  const subAgent = `outage-b-${Date.now().toString(36)}`;
  const pubSecret = await registeredAgent(admin4, 'e', pubAgent, {
    standingPermissions: ['event:publish'],
    autonomyDeclared: true,
  });
  const subSecret = await registeredAgent(admin4, 'e', subAgent, {
    standingPermissions: ['event:subscribe'],
    autonomyDeclared: true,
  });
  check(
    'set-up: A (publish) and B (subscribe) registered in E',
    pubSecret !== '' && subSecret !== '',
  );
  docker([...COMPOSE, 'stop', 'org-gateway']);
  // The credentials come from S3, which never needs S1 (Case 3).
  const a = agentCredentialOf(await bootstrapAgent('e', pubAgent, pubSecret, 'i-1'));
  const b = agentCredentialOf(await bootstrapAgent('e', subAgent, subSecret, 'i-1'));
  check('set-up: A and B bootstrapped at S3 with S1 stopped', a !== '' && b !== '');
  const roundTrip = async (label: string): Promise<void> => {
    const stream = await subscribeAt('e', b);
    check(`${label} B subscribes`, stream.status === 200, String(stream.status));
    const marker = `outage-${label}-${Date.now().toString(36)}`;
    const published = await publishAt('e', a, { marker });
    check(`${label} A publishes`, published.status === 202, shown(published));
    const arrived = await stream.until(() =>
      stream.events.some((e) => e.event === 'delivery' && e.data.includes(marker)),
    );
    stream.close();
    check(`${label} B receives the Delivery`, arrived);
  };
  await roundTrip('(a)');
  docker([...COMPOSE, 'restart', 'e-event-ingest']);
  check('(b) S4 restarted without S1 is healthy', await waitHealthy('e-event-ingest', 120));
  await roundTrip('(b)');
  docker([...COMPOSE, 'start', 'org-gateway']);
  check('S1 is healthy again', await waitHealthy('org-gateway', 120));

  if (failed() > 0) {
    console.error(`${failed()} outage check(s) failed.`);
    process.exitCode = 1;
  } else {
    console.log('S1-stopped demonstration passed.');
  }
}

if (import.meta.main) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
