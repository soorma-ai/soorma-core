// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The stack smoke test (TC-OI-056; TC-OI-057's stack half; D-ID-OI-06), run
// by CI and at the local smoke run against a stack started with
// `pnpm stack:init && pnpm stack:up`:
//
//   pnpm stack:smoke
//
//  1. org-migrate completed; org-gateway is healthy
//  2. over TLS 1.3, with the local CA passed explicitly (never the system
//     trust store): first authentication from the handover file, sign-in,
//     renewal, the logout, and a refused renewal after it
//  3. TLS 1.2 is refused; a client without the CA is refused
//  4. only the edge is published, on the host's loopback; not 9443, not 5432
//  5. the org store refuses a connection without TLS
//  6. every container runs non-root, read-only, with all capabilities
//     dropped; S1 holds no migrator password
//  7. S1's logs carry no human identifier and no secret
//  8. secrets (Q-CG-4 B): org-secrets-init completed, with only its three
//     capabilities and no network; each service sees only its own secrets,
//     owned by its user, mode 0400
// The enrollment material is read from the handover file into the request
// body only; it is never printed.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { request } from 'node:https';
import { connect } from 'node:net';
import { join, resolve } from 'node:path';

const LOCAL = resolve(import.meta.dirname, '..');
const SECRETS = join(LOCAL, '.secrets');
const COMPOSE = ['compose', '-f', join(LOCAL, 'compose.yaml')];
const PRINCIPAL = { organization: 'o1', principal: 'h@example.com' };
const K = `smoke ${Date.now().toString(36)} lantern garden`;

let failures = 0;
function check(name: string, ok: boolean, detail = ''): void {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures += 1;
}

const docker = (args: string[]): string =>
  execFileSync('docker', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();

interface Reply {
  status: number;
  body: string;
  protocol: string | null;
}

function call(
  path: string,
  options: {
    body?: unknown;
    token?: string;
    ca?: Buffer | null;
    maxVersion?: 'TLSv1.2';
  } = {},
): Promise<Reply> {
  const ca = options.ca === undefined ? readFileSync(join(SECRETS, 'stack-ca.pem')) : options.ca;
  return new Promise((done, fail) => {
    const req = request(
      {
        host: 'localhost',
        port: 8441,
        path,
        method: 'POST',
        agent: false,
        ...(ca ? { ca } : {}),
        ...(options.maxVersion ? { maxVersion: options.maxVersion } : {}),
        headers: {
          'soorma-contract-version': '0.1.0',
          ...(options.body === undefined ? {} : { 'content-type': 'application/json' }),
          ...(options.token ? { authorization: `Bearer ${options.token}` } : {}),
        },
      },
      (res) => {
        const protocol =
          (res.socket as { getProtocol?: () => string | null }).getProtocol?.() ?? null;
        let body = '';
        res.on('data', (c: Buffer) => (body += c.toString()));
        res.on('end', () => done({ status: res.statusCode ?? 0, body, protocol }));
      },
    );
    req.on('error', fail);
    req.end(options.body === undefined ? undefined : JSON.stringify(options.body));
  });
}

const refused = async (p: Promise<unknown>): Promise<boolean> =>
  p.then(
    () => false,
    () => true,
  );

function listening(port: number): Promise<boolean> {
  return new Promise((done) => {
    const socket = connect({ host: '127.0.0.1', port });
    socket.setTimeout(1500);
    socket.on('connect', () => {
      socket.destroy();
      done(true);
    });
    socket.on('timeout', () => {
      socket.destroy();
      done(false);
    });
    socket.on('error', () => done(false));
  });
}

async function main(): Promise<void> {
  // 1. The services.
  const migrate = docker([
    ...COMPOSE,
    'ps',
    '-a',
    '--format',
    '{{.State}} {{.ExitCode}}',
    'org-migrate',
  ]);
  check('org-migrate completed', migrate === 'exited 0', migrate);
  const gatewayId = docker([...COMPOSE, 'ps', '-q', 'org-gateway']);
  const dbId = docker([...COMPOSE, 'ps', '-q', 'org-db']);
  check(
    'org-gateway is healthy',
    docker(['inspect', '-f', '{{.State.Health.Status}}', gatewayId]) === 'healthy',
  );

  // 2. The flows over TLS 1.3.
  const handover = readFileSync(join(SECRETS, 'handover', 'first-admin-1.txt'), 'utf8');
  const material = /enrollmentMaterial: (\S+)/.exec(handover)?.[1] ?? '';
  const first = await call('/first-authentication', {
    body: { principal: PRINCIPAL, enrollmentMaterial: material, newSecret: K },
  });
  check(
    'first authentication, over TLS 1.3',
    first.status === 200 && first.protocol === 'TLSv1.3',
    `${first.status} ${first.protocol}`,
  );
  const signIn = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  check('sign-in', signIn.status === 200, String(signIn.status));
  const token =
    signIn.status === 200
      ? (JSON.parse(signIn.body) as { signIn: { token: string } }).signIn.token
      : '';
  check('renewal', (await call('/sign-ins/current/renewal', { token })).status === 200);
  check('the logout', (await call('/sign-ins/current/end', { token })).status === 204);
  check(
    'renewal after the logout is refused',
    (await call('/sign-ins/current/renewal', { token })).status === 401,
  );
  const reused = await call('/first-authentication', {
    body: { principal: PRINCIPAL, enrollmentMaterial: material, newSecret: `${K} again` },
  });
  check('the enrollment material is single use', reused.status === 403, String(reused.status));

  // 3. TLS.
  check(
    'TLS 1.2 is refused',
    await refused(call('/sign-ins', { body: {}, maxVersion: 'TLSv1.2' })),
  );
  check(
    'a client without the CA is refused',
    await refused(call('/sign-ins', { body: {}, ca: null })),
  );

  // 4. What is published.
  const ports = docker(['inspect', '-f', '{{json .HostConfig.PortBindings}}', gatewayId]);
  check(
    'the edge is published on 127.0.0.1:8441 only',
    ports === '{"8443/tcp":[{"HostIp":"127.0.0.1","HostPort":"8441"}]}',
    ports,
  );
  check('the internal port is not published', !(await listening(9443)));
  check(
    'the org store is not published',
    docker(['inspect', '-f', '{{json .HostConfig.PortBindings}}', dbId]) === '{}',
  );

  // 5. TLS to the org store.
  let plain = '';
  try {
    docker([
      ...COMPOSE,
      'exec',
      '-T',
      'org-db',
      'psql',
      'host=127.0.0.1 dbname=soorma_org user=soorma_org_app sslmode=disable',
      '-c',
      'SELECT 1',
    ]);
  } catch (error) {
    const stderr = (error as { stderr?: string | Buffer }).stderr;
    plain = stderr === undefined ? '' : stderr.toString();
  }
  check(
    'the org store refuses a connection without TLS',
    /no pg_hba\.conf entry|no encryption/.test(plain),
  );

  // 6. Hardening, and no migrator password in S1.
  for (const [name, id] of [
    ['org-gateway', gatewayId],
    ['org-db', dbId],
  ] as const) {
    const h = docker([
      'inspect',
      '-f',
      '{{.Config.User}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.CapDrop}}|{{.HostConfig.SecurityOpt}}',
      id,
    ]);
    const [user, ro, caps, opts] = h.split('|');
    check(
      `${name} is hardened`,
      !!user &&
        user !== 'root' &&
        user !== '0' &&
        ro === 'true' &&
        caps === '[ALL]' &&
        opts === '[no-new-privileges:true]',
      h,
    );
  }
  const holds = docker([
    'exec',
    gatewayId,
    '/nodejs/bin/node',
    '-e',
    "console.log(require('fs').existsSync('/run/secrets/org-db-migrator-password'))",
  ]);
  check('S1 holds no migrator password', holds === 'false');

  // 8. Secrets: the init container, and each service's own directory.
  const initId = docker([...COMPOSE, 'ps', '-a', '-q', 'org-secrets-init']);
  const init = docker([
    'inspect',
    '-f',
    '{{.State.Status}} {{.State.ExitCode}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.CapDrop}}|{{.HostConfig.CapAdd}}|{{.HostConfig.NetworkMode}}',
    initId,
  ]);
  check(
    'org-secrets-init completed: read-only, only CHOWN, DAC_OVERRIDE, FOWNER, no network',
    // Docker reports capabilities with or without the CAP_ prefix, by version.
    init.replace(/CAP_/g, '') === 'exited 0|true|[ALL]|[CHOWN DAC_OVERRIDE FOWNER]|none',
    init,
  );
  const listing = (id: string): string =>
    docker([
      'exec',
      id,
      '/nodejs/bin/node',
      '-e',
      "const fs=require('fs');console.log(fs.readdirSync('/run/secrets').sort().map(n=>{const s=fs.statSync('/run/secrets/'+n);return n+':'+s.uid+':'+(s.mode&0o777).toString(8)}).join(' '))",
    ]);
  const gatewaySecrets = listing(gatewayId);
  const expectedGateway = [
    'org-counter-secret',
    'org-db-app-password',
    'org-enrollment-1',
    'org-gateway-tls',
    'org-log-pseudonym-key',
    'org-seed-key',
    'org-signing-key',
    'stack-ca-cert',
  ]
    .map((n) => `${n}:65532:400`)
    .join(' ');
  check(
    'org-gateway sees exactly its own secrets, 65532, 0400',
    gatewaySecrets === expectedGateway,
    gatewaySecrets,
  );
  const dbSecrets = docker([
    'exec',
    dbId,
    'sh',
    '-c',
    'cd /run/secrets && for f in *; do echo "$f:$(stat -c %u:%a "$f")"; done | sort | tr "\\n" " "',
  ]).trim();
  check(
    'org-db sees exactly its own secrets, 999, 0400',
    dbSecrets ===
      'org-db-app-password:999:400 org-db-migrator-password:999:400 org-db-superuser-password:999:400 org-db-tls:999:400',
    dbSecrets,
  );
  const writable = docker([
    'exec',
    gatewayId,
    '/nodejs/bin/node',
    '-e',
    "try{require('fs').writeFileSync('/run/secrets/x','x');console.log('writable')}catch{console.log('read-only')}",
  ]);
  check("a service's secrets mount is read-only", writable === 'read-only');

  // 7. The logs.
  const logs = docker([...COMPOSE, 'logs', '--no-color', 'org-gateway', 'org-migrate']);
  const leaked = [PRINCIPAL.principal, material, K, token].filter(
    (s) => s.length > 0 && logs.includes(s),
  );
  check('the logs carry no identifier and no secret', leaked.length === 0);

  if (failures > 0) {
    console.error(`${failures} smoke check(s) failed.`);
    process.exitCode = 1;
  } else {
    console.log('Stack smoke test passed.');
  }
}

if (import.meta.main) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
