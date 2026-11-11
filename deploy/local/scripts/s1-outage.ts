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
//
// It leaves S1 and both S2s running.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import {
  call,
  check,
  COMPOSE,
  docker,
  failed,
  PRINCIPAL,
  SECRETS,
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
