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
//  9. environments E and E2 (U4; TC-EHA-086): e-migrate and e2-migrate
//     completed, each S2 healthy; over TLS 1.3 on 127.0.0.1:8442, a
//     credential issued from a live sign-in, renewed, used for a self-grant,
//     and ended; E's credential refused at E2 (8443); each S2 published on its
//     own loopback port only, its store nowhere; S2 and its store hardened,
//     each seeing only its own secrets; S2 holds no migrator password
// 10. what reaches E (U4; TC-EHA-050, TC-EHA-067): E's store name does not
//     resolve from E2's S2, nor E2's from E's, and E2's app password does not
//     open E's store (E's own does); from inside network e, a credential
//     resolves the same actor as from the host, and from org-internal-e, no
//     credential is credential_refused
// 11. S3 in E and E2 (U6; TC-AC-092, 090, 020, 031): each data-gateway
//     healthy, published on its own loopback port only (8444, 8445), hardened,
//     seeing exactly its own five secrets; an agent registered through S2
//     bootstraps and renews at its environment's S3 over TLS 1.3, its
//     credential naming that environment; E's agent credential is refused at
//     E2's S3; the data role exists with U4's attributes, and S3's session runs
//     as soorma_env_data over TLS 1.3 while S2's runs as soorma_env_app
// 12. S4 in E and E2 (U7 D-ID-ET-10; TC-ET-085), at S3's depth: each
//     event-ingest healthy, published on its own loopback port only (8446,
//     8447), hardened, seeing exactly its own five secrets; a refused publish
//     is a Problem; an agent registered through S2 with event:publish and
//     event:subscribe and autonomy declared, bootstrapped at S3, subscribes and
//     publishes at its environment's S4 over TLS 1.3 and receives its own
//     Delivery, scoped to that environment and sealed; the ingest role exists
//     with U4's attributes and S4's session runs as soorma_env_ingest over TLS
//     1.3; E's agent credential is refused at E2's S4
// The enrollment material is read from the handover file into the request
// body only; it is never printed.
import { readFileSync } from 'node:fs';
import { connect } from 'node:net';
import { join } from 'node:path';
import {
  agentCredentialOf,
  bootstrapAgent,
  call,
  check,
  COMPOSE,
  DATA_GATEWAY,
  docker,
  EVENT_INGEST,
  dockerWithInput,
  failed,
  PRINCIPAL,
  publishAt,
  registeredAgent,
  renewAgent,
  SECRETS,
  subscribeAt,
} from './stack-client.ts';

const K = `smoke ${Date.now().toString(36)} lantern garden`;

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
    // Each environment's caller PUBLIC key (U4 Infrastructure Design §3).
    'e-caller-public-key',
    'e2-caller-public-key',
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

  // 9. Environments E and E2 (U4).
  const secrets = await environments();

  // 10. What reaches E (U4).
  secrets.push(...(await reach()));

  // 11. S3 in E and E2 (U6).
  secrets.push(...(await dataGateways()));

  // 12. S4 in E and E2 (U7).
  secrets.push(...(await eventIngests()));

  // 7. The logs.
  const logs = docker([
    ...COMPOSE,
    'logs',
    '--no-color',
    'org-gateway',
    'org-migrate',
    'e-control-gateway',
    'e2-control-gateway',
    'e-migrate',
    'e2-migrate',
    'e-data-gateway',
    'e2-data-gateway',
    'e-event-ingest',
    'e2-event-ingest',
  ]);
  const leaked = [PRINCIPAL.principal, material, K, token, ...secrets].filter(
    (s) => s.length > 0 && logs.includes(s),
  );
  check('the logs carry no identifier and no secret', leaked.length === 0);

  if (failed() > 0) {
    console.error(`${failed()} smoke check(s) failed.`);
    process.exitCode = 1;
  } else {
    console.log('Stack smoke test passed.');
  }
}

/** Section 9: E and E2. Returns the tokens it saw, for the log check. */
async function environments(): Promise<string[]> {
  for (const env of ['e', 'e2']) {
    const migrate = docker([
      ...COMPOSE,
      'ps',
      '-a',
      '--format',
      '{{.State}} {{.ExitCode}}',
      `${env}-migrate`,
    ]);
    check(`${env}-migrate completed`, migrate === 'exited 0', migrate);
    const id = docker([...COMPOSE, 'ps', '-q', `${env}-control-gateway`]);
    check(
      `${env}-control-gateway is healthy`,
      docker(['inspect', '-f', '{{.State.Health.Status}}', id]) === 'healthy',
    );
  }
  const signIn = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  const signInToken =
    signIn.status === 200
      ? (JSON.parse(signIn.body) as { signIn: { token: string } }).signIn.token
      : '';
  const issued = await call('/environment-credentials', { token: signInToken, port: 8442 });
  check(
    "E's credential is issued from a live sign-in, over TLS 1.3",
    issued.status === 200 && issued.protocol === 'TLSv1.3',
    `${issued.status} ${issued.protocol}`,
  );
  const credential =
    issued.status === 200 ? (JSON.parse(issued.body) as { credential: string }).credential : '';
  const renewed = await call('/environment-credentials/current/renewal', {
    token: credential,
    port: 8442,
  });
  check("E's credential renews", renewed.status === 200, String(renewed.status));
  const granted = await call('/grants', {
    token: credential,
    port: 8442,
    body: { target: PRINCIPAL, permissions: ['agent:register'] },
  });
  check(
    'a self-grant at E',
    granted.status === 200 &&
      (JSON.parse(granted.body) as { selfGrant?: boolean }).selfGrant === true,
    String(granted.status),
  );
  check(
    "E's credential is refused at E2",
    (await call('/environment-credentials/current/renewal', { token: credential, port: 8443 }))
      .status === 401,
  );
  check(
    'ending at E',
    (await call('/environment-credentials/current/end', { token: credential, port: 8442 }))
      .status === 204,
  );
  check(
    'an ended credential is refused',
    (await call('/environment-credentials/current/renewal', { token: credential, port: 8442 }))
      .status === 401,
  );

  const id = (service: string): string => docker([...COMPOSE, 'ps', '-q', service]);
  for (const [env, port] of [
    ['e', '8442'],
    ['e2', '8443'],
  ] as const) {
    const s2 = id(`${env}-control-gateway`);
    const db = id(`${env}-db`);
    const ports = docker(['inspect', '-f', '{{json .HostConfig.PortBindings}}', s2]);
    check(
      `${env}-control-gateway is published on 127.0.0.1:${port} only`,
      ports === `{"8443/tcp":[{"HostIp":"127.0.0.1","HostPort":"${port}"}]}`,
      ports,
    );
    check(
      `${env}-db is not published`,
      docker(['inspect', '-f', '{{json .HostConfig.PortBindings}}', db]) === '{}',
    );
    for (const [name, cid] of [
      [`${env}-control-gateway`, s2],
      [`${env}-db`, db],
    ] as const) {
      const h = docker([
        'inspect',
        '-f',
        '{{.Config.User}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.CapDrop}}|{{.HostConfig.SecurityOpt}}',
        cid,
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
    const listing = docker([
      'exec',
      s2,
      '/nodejs/bin/node',
      '-e',
      "const fs=require('fs');console.log(fs.readdirSync('/run/secrets').sort().map(n=>{const s=fs.statSync('/run/secrets/'+n);return n+':'+s.uid+':'+(s.mode&0o777).toString(8)}).join(' '))",
    ]);
    const expected = [
      `${env}-caller-key`,
      `${env}-control-gateway-tls`,
      `${env}-db-app-password`,
      `${env}-log-pseudonym-key`,
      `${env}-signing-key-1`,
      'stack-ca-cert',
    ]
      .map((n) => `${n}:65532:400`)
      .join(' ');
    check(
      `${env}-control-gateway sees exactly its own secrets (no migrator password), 65532, 0400`,
      listing === expected,
      listing,
    );
    const initId = docker([...COMPOSE, 'ps', '-a', '-q', `${env}-secrets-init`]);
    const init = docker([
      'inspect',
      '-f',
      '{{.State.Status}} {{.State.ExitCode}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.CapDrop}}|{{.HostConfig.CapAdd}}|{{.HostConfig.NetworkMode}}',
      initId,
    ]);
    check(
      `${env}-secrets-init completed: read-only, only CHOWN, DAC_OVERRIDE, FOWNER, no network`,
      init.replace(/CAP_/g, '') === 'exited 0|true|[ALL]|[CHOWN DAC_OVERRIDE FOWNER]|none',
      init,
    );
  }
  return [signInToken, credential].filter((t) => t.length > 0);
}

/** Section 10: what reaches E. Returns the tokens it used, for the log check. */
async function reach(): Promise<string[]> {
  // TC-EHA-067 step 1: no store name resolves across environments.
  const resolves = (service: string, name: string): string =>
    dockerWithInput(
      [
        ...COMPOSE,
        'exec',
        '-T',
        service,
        '/nodejs/bin/node',
        '-e',
        "require('dns').lookup(require('fs').readFileSync(0,'utf8').trim(),(e)=>console.log(e?e.code:'resolved'))",
      ],
      name,
    ).stdout;
  check(
    "E's store name resolves from E's S2",
    resolves('e-control-gateway', 'env-db.e.soorma.internal') === 'resolved',
  );
  for (const [service, name] of [
    ['e-control-gateway', 'env-db.e2.soorma.internal'],
    ['e2-control-gateway', 'env-db.e.soorma.internal'],
  ] as const) {
    const answer = resolves(service, name);
    check(`${name} does not resolve from ${service}`, answer !== 'resolved', answer);
  }

  // TC-EHA-067 step 2: E2's app password does not open E's store.
  const connect = (password: string) =>
    dockerWithInput(
      [
        ...COMPOSE,
        'exec',
        '-T',
        'e-db',
        'sh',
        '-c',
        'read -r PGPASSWORD; export PGPASSWORD; psql -X -q -t "host=127.0.0.1 dbname=soorma_env user=soorma_env_app sslmode=require" -c "SELECT 1"',
      ],
      password,
    );
  const own = connect(readFileSync(join(SECRETS, 'e-db-app-password'), 'utf8').trim());
  check("E's app password opens E's store (the control)", own.status === 0, own.stderr);
  const other = connect(readFileSync(join(SECRETS, 'e2-db-app-password'), 'utf8').trim());
  check(
    "E2's app password does not open E's store",
    other.status !== 0 && /password authentication failed/.test(other.stderr),
    other.stderr.split('\n')[0] ?? '',
  );

  // TC-EHA-050: identity from the credential alone, never the network.
  const signIn = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  const signInToken =
    signIn.status === 200
      ? (JSON.parse(signIn.body) as { signIn: { token: string } }).signIn.token
      : '';
  const issued = await call('/environment-credentials', { token: signInToken, port: 8442 });
  const credential =
    issued.status === 200 ? (JSON.parse(issued.body) as { credential: string }).credential : '';
  const body = { target: PRINCIPAL, permissions: ['agent:register'] };
  const fromHost = await call('/grants', { token: credential, port: 8442, body });
  const ca = readFileSync(join(SECRETS, 'stack-ca.pem'), 'utf8');
  // A one-off container on one of the stack's networks, calling E's S2 by its
  // network name; the CA and the credential arrive on stdin.
  const inside = (
    network: string,
    host: string,
    token: string,
  ): { status: number; selfGrant?: boolean } => {
    const r = dockerWithInput(
      [
        'run',
        '--rm',
        '-i',
        '--network',
        `soorma-local_${network}`,
        '--read-only',
        '--cap-drop',
        'ALL',
        '--security-opt',
        'no-new-privileges:true',
        '--entrypoint',
        '/nodejs/bin/node',
        'soorma/control-gateway:local',
        '-e',
        `const {ca,host,token,body}=JSON.parse(require('fs').readFileSync(0,'utf8'));
const r=require('https').request({host,servername:'control-gateway.e.soorma.internal',port:8443,path:'/grants',method:'POST',ca,
headers:{'soorma-contract-version':'0.1.0','content-type':'application/json',...(token?{authorization:'Bearer '+token}:{})}},
(res)=>{let b='';res.on('data',(c)=>b+=c);res.on('end',()=>{let j={};try{j=JSON.parse(b)}catch{}console.log(JSON.stringify({status:res.statusCode,selfGrant:j.selfGrant,code:j.code}))})});
r.on('error',(e)=>console.log(JSON.stringify({status:0,code:e.code})));r.end(JSON.stringify(body));`,
      ],
      JSON.stringify({ ca, host, token, body }),
    );
    try {
      return JSON.parse(r.stdout) as { status: number; selfGrant?: boolean };
    } catch {
      return { status: -1 };
    }
  };
  const fromE = inside('e', 'control-gateway.e.soorma.internal', credential);
  check(
    'from inside network e, the credential resolves the same actor as from the host',
    fromHost.status === 200 &&
      fromE.status === 200 &&
      (JSON.parse(fromHost.body) as { selfGrant?: boolean }).selfGrant === true &&
      fromE.selfGrant === true,
    `${fromHost.status} ${fromE.status}`,
  );
  // On org-internal-e, S2 has no alias: it is reached by its service name.
  const fromInternal = inside('org-internal-e', 'e-control-gateway', '');
  check(
    'from org-internal-e, no credential is credential_refused',
    fromInternal.status === 401 &&
      (fromInternal as { code?: string }).code === 'credential_refused',
    JSON.stringify(fromInternal),
  );
  check(
    'ending the credential',
    (await call('/environment-credentials/current/end', { token: credential, port: 8442 }))
      .status === 204,
  );
  return [signInToken, credential].filter((t) => t.length > 0);
}

if (import.meta.main) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}

/** Section 11: S3 in E and E2 (U6). Returns the secrets and tokens it saw, for the log check. */
async function dataGateways(): Promise<string[]> {
  const seen: string[] = [];
  const id = (service: string): string => docker([...COMPOSE, 'ps', '-q', service]);
  for (const env of ['e', 'e2'] as const) {
    const s3 = id(`${env}-data-gateway`);
    check(
      `${env}-data-gateway is healthy`,
      docker(['inspect', '-f', '{{.State.Health.Status}}', s3]) === 'healthy',
    );
    const ports = docker(['inspect', '-f', '{{json .HostConfig.PortBindings}}', s3]);
    check(
      `${env}-data-gateway is published on 127.0.0.1:${DATA_GATEWAY[env]} only`,
      ports === `{"8443/tcp":[{"HostIp":"127.0.0.1","HostPort":"${DATA_GATEWAY[env]}"}]}`,
      ports,
    );
    const h = docker([
      'inspect',
      '-f',
      '{{.Config.User}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.CapDrop}}|{{.HostConfig.SecurityOpt}}',
      s3,
    ]);
    const [user, ro, caps, opts] = h.split('|');
    check(
      `${env}-data-gateway is hardened`,
      !!user &&
        user !== 'root' &&
        user !== '0' &&
        ro === 'true' &&
        caps === '[ALL]' &&
        opts === '[no-new-privileges:true]',
      h,
    );
    const listing = docker([
      'exec',
      s3,
      '/nodejs/bin/node',
      '-e',
      "const fs=require('fs');console.log(fs.readdirSync('/run/secrets').sort().map(n=>{const s=fs.statSync('/run/secrets/'+n);return n+':'+s.uid+':'+(s.mode&0o777).toString(8)}).join(' '))",
    ]);
    const expected = [
      `${env}-agent-signing-key-1`,
      `${env}-bootstrap-counter-secret`,
      `${env}-data-gateway-tls`,
      `${env}-db-data-password`,
      'stack-ca-cert',
    ]
      .map((n) => `${n}:65532:400`)
      .join(' ');
    check(
      `${env}-data-gateway sees exactly its own five secrets (no app or migrator password, no human ring), 65532, 0400`,
      listing === expected,
      listing,
    );
  }

  // An agent per environment, registered through that environment's S2.
  const signIn = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  const signInToken =
    signIn.status === 200
      ? (JSON.parse(signIn.body) as { signIn: { token: string } }).signIn.token
      : '';
  const tokens: Record<'e' | 'e2', string> = { e: '', e2: '' };
  for (const env of ['e', 'e2'] as const) {
    const port = env === 'e' ? 8442 : 8443;
    const issued = await call('/environment-credentials', { token: signInToken, port });
    const credential =
      issued.status === 200 ? (JSON.parse(issued.body) as { credential: string }).credential : '';
    await call('/grants', {
      token: credential,
      port,
      body: { target: PRINCIPAL, permissions: ['agent:register'] },
    });
    const agent = `smoke-${env}-${Date.now().toString(36)}`;
    const secret = await registeredAgent(credential, env, agent);
    check(`set-up: an agent registered in ${env}, with a secret`, secret !== '');
    const booted = await bootstrapAgent(env, agent, secret);
    const body =
      booted.status === 200
        ? (JSON.parse(booted.body) as { environment: { environment: string }; agent: string })
        : undefined;
    check(
      `a bootstrap at ${env}'s S3, over TLS 1.3, naming ${env}`,
      booted.status === 200 &&
        booted.protocol === 'TLSv1.3' &&
        body?.agent === agent &&
        body.environment.environment === env,
      `${booted.status} ${booted.protocol}`,
    );
    const token = agentCredentialOf(booted);
    const renewed = await renewAgent(env, token);
    check(`a renewal at ${env}'s S3`, renewed.status === 200, String(renewed.status));
    tokens[env] = agentCredentialOf(renewed) || token;
    seen.push(credential, secret, token, tokens[env]);
    // TC-AC-090, right after the calls, while each pool holds a session (idle
    // sessions close after 10 seconds).
    const sql = (query: string): string =>
      dockerWithInput(
        [
          ...COMPOSE,
          'exec',
          '-T',
          `${env}-db`,
          'psql',
          '-X',
          '-q',
          '-At',
          '-U',
          'postgres',
          '-d',
          'soorma_env',
        ],
        query,
      ).stdout;
    check(
      `${env}: soorma_env_data exists with U4's attributes`,
      sql(
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = 'soorma_env_data';",
      ) === 't|f|f|f|f|f|f',
    );
    const sessions = (service: string): string => {
      const ip = docker([
        'inspect',
        '-f',
        `{{(index .NetworkSettings.Networks "soorma-local_${env}").IPAddress}}`,
        id(`${env}-${service}`),
      ]);
      return sql(
        `SELECT DISTINCT a.usename || ':' || s.version FROM pg_stat_activity a JOIN pg_stat_ssl s USING (pid) WHERE a.client_addr = '${ip}' AND s.ssl;`,
      );
    };
    check(
      `${env}'s S3 connects as soorma_env_data over TLS 1.3`,
      sessions('data-gateway') === 'soorma_env_data:TLSv1.3',
      sessions('data-gateway'),
    );
    check(
      `${env}'s S2 connects as soorma_env_app over TLS 1.3`,
      sessions('control-gateway') === 'soorma_env_app:TLSv1.3',
      sessions('control-gateway'),
    );
  }
  const crossed = await renewAgent('e2', tokens.e);
  check(
    "E's agent credential is refused at E2's S3",
    crossed.status === 401,
    String(crossed.status),
  );

  return seen.filter((x) => x.length > 0);
}

/** Section 12: S4 in E and E2 (U7). Returns the secrets, tokens, and seals it saw, for the log check. */
async function eventIngests(): Promise<string[]> {
  const seen: string[] = [];
  const id = (service: string): string => docker([...COMPOSE, 'ps', '-q', service]);
  const sql = (env: 'e' | 'e2', query: string): string =>
    dockerWithInput(
      [
        ...COMPOSE,
        'exec',
        '-T',
        `${env}-db`,
        'psql',
        '-X',
        '-q',
        '-At',
        '-U',
        'postgres',
        '-d',
        'soorma_env',
      ],
      query,
    ).stdout;
  const sessions = (env: 'e' | 'e2', service: string): string => {
    const ip = docker([
      'inspect',
      '-f',
      `{{(index .NetworkSettings.Networks "soorma-local_${env}").IPAddress}}`,
      id(`${env}-${service}`),
    ]);
    return sql(
      env,
      `SELECT DISTINCT a.usename || ':' || s.version FROM pg_stat_activity a JOIN pg_stat_ssl s USING (pid) WHERE a.client_addr = '${ip}' AND s.ssl;`,
    );
  };

  for (const env of ['e', 'e2'] as const) {
    const s4 = id(`${env}-event-ingest`);
    check(
      `${env}-event-ingest is healthy`,
      docker(['inspect', '-f', '{{.State.Health.Status}}', s4]) === 'healthy',
    );
    const ports = docker(['inspect', '-f', '{{json .HostConfig.PortBindings}}', s4]);
    check(
      `${env}-event-ingest is published on 127.0.0.1:${EVENT_INGEST[env]} only`,
      ports === `{"8443/tcp":[{"HostIp":"127.0.0.1","HostPort":"${EVENT_INGEST[env]}"}]}`,
      ports,
    );
    const h = docker([
      'inspect',
      '-f',
      '{{.Config.User}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.CapDrop}}|{{.HostConfig.SecurityOpt}}|{{.HostConfig.Memory}}',
      s4,
    ]);
    const [user, ro, caps, opts, memory] = h.split('|');
    check(
      `${env}-event-ingest is hardened, with its 512m memory limit`,
      !!user &&
        user !== 'root' &&
        user !== '0' &&
        ro === 'true' &&
        caps === '[ALL]' &&
        opts === '[no-new-privileges:true]' &&
        memory === String(512 * 1024 * 1024),
      h,
    );
    const listing = docker([
      'exec',
      s4,
      '/nodejs/bin/node',
      '-e',
      "const fs=require('fs');console.log(fs.readdirSync('/run/secrets').sort().map(n=>{const s=fs.statSync('/run/secrets/'+n);return n+':'+s.uid+':'+(s.mode&0o777).toString(8)}).join(' '))",
    ]);
    const expected = [
      `${env}-agent-verify-key-1`,
      `${env}-db-ingest-password`,
      `${env}-event-ingest-tls`,
      `${env}-seal-key-1`,
      'stack-ca-cert',
    ]
      .map((n) => `${n}:65532:400`)
      .join(' ');
    check(
      `${env}-event-ingest sees exactly its own five secrets (no signing key, no other role's password), 65532, 0400`,
      listing === expected,
      listing,
    );
    check(
      `${env}'s S4 refuses TLS 1.2`,
      await refused(call('/events', { port: EVENT_INGEST[env], maxVersion: 'TLSv1.2' })),
    );
    const anonymous = await publishAt(env, '', { smoke: true });
    let problem: { code?: unknown; instance?: unknown } = {};
    try {
      problem = JSON.parse(anonymous.body) as typeof problem;
    } catch {
      // checked below
    }
    check(
      `a publish with no credential at ${env}'s S4 is 401 credential_refused, a Problem with the Soorma headers, over TLS 1.3`,
      anonymous.status === 401 &&
        anonymous.protocol === 'TLSv1.3' &&
        problem.code === 'credential_refused' &&
        anonymous.headers['soorma-contract-version'] === '0.1.0' &&
        typeof anonymous.headers['soorma-request-id'] === 'string' &&
        problem.instance === `urn:soorma:request:${String(anonymous.headers['soorma-request-id'])}`,
      `${anonymous.status} ${anonymous.protocol}`,
    );
  }

  // An agent per environment with event:publish and event:subscribe, autonomy declared.
  const signIn = await call('/sign-ins', { body: { principal: PRINCIPAL, secret: K } });
  const signInToken =
    signIn.status === 200
      ? (JSON.parse(signIn.body) as { signIn: { token: string } }).signIn.token
      : '';
  const tokens: Record<'e' | 'e2', string> = { e: '', e2: '' };
  for (const env of ['e', 'e2'] as const) {
    const port = env === 'e' ? 8442 : 8443;
    const issued = await call('/environment-credentials', { token: signInToken, port });
    const credential =
      issued.status === 200 ? (JSON.parse(issued.body) as { credential: string }).credential : '';
    const granted = await call('/grants', {
      token: credential,
      port,
      body: { target: PRINCIPAL, permissions: ['event:publish', 'event:subscribe'] },
    });
    check(`set-up: event:publish and event:subscribe granted in ${env}`, granted.status === 200);
    const agent = `smoke-ei-${env}-${Date.now().toString(36)}`;
    const secret = await registeredAgent(credential, env, agent, {
      standingPermissions: ['event:publish', 'event:subscribe'],
      autonomyDeclared: true,
    });
    check(
      `set-up: an agent registered in ${env} with event permissions and autonomy`,
      secret !== '',
    );
    const booted = await bootstrapAgent(env, agent, secret);
    check(`set-up: bootstrapped at ${env}'s S3`, booted.status === 200, String(booted.status));
    const token = agentCredentialOf(booted);
    tokens[env] = token;
    seen.push(credential, secret, token);

    // The round trip at this environment's S4.
    const stream = await subscribeAt(env, token);
    check(
      `a subscribe at ${env}'s S4 opens a stream, over TLS 1.3`,
      stream.status === 200 &&
        stream.protocol === 'TLSv1.3' &&
        stream.contentType === 'text/event-stream; charset=utf-8',
      `${stream.status} ${stream.protocol} ${stream.contentType}`,
    );
    const marker = `smoke-payload-${env}-${Date.now().toString(36)}`;
    const published = await publishAt(env, token, { marker });
    check(
      `a publish at ${env}'s S4 is 202, with no body`,
      published.status === 202 && published.body === '',
      String(published.status),
    );
    const arrived = await stream.until(() => stream.events.some((e) => e.event === 'delivery'));
    stream.close();
    const delivery = arrived
      ? (JSON.parse(stream.events.find((e) => e.event === 'delivery')!.data) as {
          envelope: { scope: Record<string, string>; actorChain: { agent: string }[] };
          seal: string;
          payload: { marker?: string };
        })
      : undefined;
    check(
      `the agent receives its own Delivery at ${env}'s S4`,
      delivery?.payload.marker === marker,
    );
    check(
      `the Delivery is scoped to ${env} and sealed`,
      delivery?.envelope.scope.organization === 'o1' &&
        delivery.envelope.scope.project === 'p1' &&
        delivery.envelope.scope.environment === env &&
        delivery.envelope.actorChain[0]?.agent === agent &&
        typeof delivery.seal === 'string' &&
        delivery.seal.length > 0,
    );
    seen.push(marker, delivery?.seal ?? '');

    // The role, right after the round trip, while S4's pool holds a session.
    check(
      `${env}: soorma_env_ingest exists with U4's attributes`,
      sql(
        env,
        "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolreplication, rolbypassrls FROM pg_roles WHERE rolname = 'soorma_env_ingest';",
      ) === 't|f|f|f|f|f|f',
    );
    check(
      `${env}'s S4 connects as soorma_env_ingest over TLS 1.3`,
      sessions(env, 'event-ingest') === 'soorma_env_ingest:TLSv1.3',
      sessions(env, 'event-ingest'),
    );
    // §11 checks S3's and S2's roles strictly; here, any session either holds
    // (idle sessions close after 10 seconds) is still its own role, never S4's.
    const s3 = sessions(env, 'data-gateway');
    const s2 = sessions(env, 'control-gateway');
    check(
      `${env}'s S3 still connects as soorma_env_data, and S2 as soorma_env_app`,
      ['', 'soorma_env_data:TLSv1.3'].includes(s3) && ['', 'soorma_env_app:TLSv1.3'].includes(s2),
      `${s3} ${s2}`,
    );
  }
  const crossed = await publishAt('e2', tokens.e, { crossed: true });
  check(
    "E's agent credential is refused at E2's S4",
    crossed.status === 401,
    String(crossed.status),
  );

  return seen.filter((x) => x.length > 0);
}
