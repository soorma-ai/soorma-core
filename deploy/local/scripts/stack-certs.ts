// SPDX-License-Identifier: FSL-1.1-ALv2
//
// The local CA and the service certificates (Infrastructure Design §4), with
// the OpenSSL CLI, a documented prerequisite:
//
//   pnpm stack:certs     create the CA if absent; reissue every leaf certificate
//
// - The CA: ECDSA P-256, basicConstraints CA with pathlen:0, keyCertSign and
//   cRLSign, valid one year, with CRITICAL name constraints: DNS localhost,
//   DNS soorma.internal (and its subdomains), IP 127.0.0.1/32 and ::1/128,
//   nothing else. Its key stays in deploy/local/.secrets/ (0600), never in a
//   container, so U4 to U7 can issue their own certificates from it
// - Leaves: ECDSA P-256, serverAuth, valid 90 days, one PEM per service
//   holding its key and certificate
// - Callers pass the CA explicitly (curl --cacert deploy/local/.secrets/
//   stack-ca.pem); it is never installed in the system trust store
import { execFileSync } from 'node:child_process';
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

export const SECRETS_DIR = resolve(import.meta.dirname, '../.secrets');
export const CA_KEY = 'stack-ca.key';
export const CA_CERT = 'stack-ca.pem';

/** Each service certificate: the secret it is written to, and its names. */
export const LEAVES: readonly { secret: string; names: string[]; ips: string[] }[] = [
  {
    secret: 'org-gateway-tls',
    names: ['org-gateway.soorma.internal', 'localhost'],
    ips: ['127.0.0.1'],
  },
  { secret: 'org-db-tls', names: ['org-db.soorma.internal'], ips: [] },
  // Each environment's S2 and store (U4 Infrastructure Design §5).
  ...['e', 'e2'].flatMap((env) => [
    {
      secret: `${env}-control-gateway-tls`,
      names: [`control-gateway.${env}.soorma.internal`, 'localhost'],
      ips: ['127.0.0.1'],
    },
    { secret: `${env}-db-tls`, names: [`env-db.${env}.soorma.internal`], ips: [] },
  ]),
];

function openssl(args: string[]): void {
  execFileSync('openssl', args, { stdio: ['ignore', 'ignore', 'pipe'] });
}

function writeSecret(dir: string, name: string, content: string | Buffer): void {
  writeFileSync(join(dir, name), content, { mode: 0o600 });
  chmodSync(join(dir, name), 0o600);
}

export function ensureCa(dir: string = SECRETS_DIR): boolean {
  if (existsSync(join(dir, CA_KEY)) && existsSync(join(dir, CA_CERT))) return false;
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  const work = mkdtempSync(join(tmpdir(), 'soorma-ca-'));
  try {
    writeFileSync(
      join(work, 'ca.cnf'),
      [
        '[req]',
        'distinguished_name = dn',
        'prompt = no',
        'x509_extensions = ca',
        '[dn]',
        'CN = soorma local stack CA',
        '[ca]',
        'basicConstraints = critical, CA:true, pathlen:0',
        'keyUsage = critical, keyCertSign, cRLSign',
        'subjectKeyIdentifier = hash',
        'nameConstraints = critical, permitted;DNS:localhost, permitted;DNS:soorma.internal, ' +
          'permitted;IP:127.0.0.1/255.255.255.255, ' +
          'permitted;IP:0:0:0:0:0:0:0:1/FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF',
      ].join('\n'),
    );
    openssl(['ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', join(work, 'ca.key')]);
    openssl([
      'req',
      '-new',
      '-x509',
      '-key',
      join(work, 'ca.key'),
      '-config',
      join(work, 'ca.cnf'),
      '-days',
      '365',
      '-sha256',
      '-out',
      join(work, 'ca.pem'),
    ]);
    writeSecret(dir, CA_KEY, readFileSync(join(work, 'ca.key')));
    writeSecret(dir, CA_CERT, readFileSync(join(work, 'ca.pem')));
    return true;
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
}

/** Issues one leaf certificate from the CA, into `dir`/`secret` (key, then certificate). */
export function issueLeaf(
  leaf: { secret: string; names: string[]; ips: string[] },
  dir: string = SECRETS_DIR,
): void {
  const work = mkdtempSync(join(tmpdir(), 'soorma-leaf-'));
  try {
    const san = [...leaf.names.map((n) => `DNS:${n}`), ...leaf.ips.map((ip) => `IP:${ip}`)].join(
      ', ',
    );
    writeFileSync(
      join(work, 'leaf.cnf'),
      [
        '[ext]',
        'basicConstraints = critical, CA:false',
        'keyUsage = critical, digitalSignature',
        'extendedKeyUsage = serverAuth',
        `subjectAltName = ${san}`,
      ].join('\n'),
    );
    openssl([
      'ecparam',
      '-name',
      'prime256v1',
      '-genkey',
      '-noout',
      '-out',
      join(work, 'leaf.key'),
    ]);
    openssl([
      'req',
      '-new',
      '-key',
      join(work, 'leaf.key'),
      '-subj',
      `/CN=${leaf.names[0]!}`,
      '-out',
      join(work, 'leaf.csr'),
    ]);
    openssl([
      'x509',
      '-req',
      '-in',
      join(work, 'leaf.csr'),
      '-CA',
      join(dir, CA_CERT),
      '-CAkey',
      join(dir, CA_KEY),
      '-CAserial',
      join(work, 'ca.srl'),
      '-CAcreateserial',
      '-days',
      '90',
      '-sha256',
      '-extfile',
      join(work, 'leaf.cnf'),
      '-extensions',
      'ext',
      '-out',
      join(work, 'leaf.pem'),
    ]);
    writeSecret(
      dir,
      leaf.secret,
      Buffer.concat([readFileSync(join(work, 'leaf.key')), readFileSync(join(work, 'leaf.pem'))]),
    );
  } finally {
    rmSync(work, { recursive: true, force: true });
  }
}

/** The CA if absent, and each leaf: every one when `reissue`, else only the missing ones. */
export function ensureCertificates(options: { reissue?: boolean; dir?: string } = {}): string[] {
  const dir = options.dir ?? SECRETS_DIR;
  const done: string[] = [];
  if (ensureCa(dir)) done.push(CA_CERT);
  for (const leaf of LEAVES) {
    if (!options.reissue && existsSync(join(dir, leaf.secret))) continue;
    issueLeaf(leaf, dir);
    done.push(leaf.secret);
  }
  return done;
}

if (import.meta.main) {
  const issued = ensureCertificates({ reissue: true });
  console.log(`Wrote ${issued.join(', ')} in deploy/local/.secrets/`);
}
