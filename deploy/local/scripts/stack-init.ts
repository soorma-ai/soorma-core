// SPDX-License-Identifier: FSL-1.1-ALv2
//
// pnpm stack:init (Infrastructure Design §3; M1-TECH-06): generates every
// secret the local stack's tenancy.yaml names, into deploy/local/.secrets/,
// each mode 0600, and never overwrites one that exists.
//
// - Enrollment material: soorma_em_ + 256 random bits, written to its secret
//   and to a one-time handover file, .secrets/handover/first-admin-{n}.txt,
//   named by index in tenancy.yaml's order. It prints the file's path, never
//   the material. The human uses it at first authentication and deletes it;
//   once used the material never verifies again, so a leftover file holds
//   nothing usable
// - The signing key: an Ed25519 private key (PEM)
// - Symmetric keys and passwords: 256 random bits, base64url
// - TLS: the local CA (if absent) and each service certificate (stack-certs);
//   the CA certificate is also written under the secret name tenancy.yaml
//   gives it
// - Each environment's secrets (U4 Infrastructure Design §3): its Ed25519
//   keys (signing and verify, and its caller key), its passwords and
//   log-pseudonym key, its database superuser password; and its caller key's
//   PUBLIC half, derived as SPKI PEM, for org-gateway's internalCallers. A
//   derived public key that no longer matches its private key refuses the run
// Secrets never pass through environment variables or arguments.
import { createPrivateKey, createPublicKey, generateKeyPairSync, randomBytes } from 'node:crypto';
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { listSecrets } from '@soorma/config';
import { CA_CERT, ensureCertificates, SECRETS_DIR } from './stack-certs.ts';

export const CONFIG = resolve(import.meta.dirname, '../config/tenancy.yaml');
/** Secrets the stack needs that tenancy.yaml does not name: the database's own. */
export const STACK_ONLY = ['org-db-superuser-password'] as const;

const key256 = (): string => randomBytes(32).toString('base64url');

export interface InitResult {
  created: string[];
  kept: string[];
  handover: string[];
}

export function stackInit(options: { configPath?: string; dir?: string } = {}): InitResult {
  const dir = options.dir ?? SECRETS_DIR;
  mkdirSync(join(dir, 'handover'), { recursive: true, mode: 0o700 });
  const names = listSecrets({ configPath: options.configPath ?? CONFIG });
  const result: InitResult = { created: [], kept: [], handover: [] };

  /** Writes a secret unless it exists; true when written. */
  const write = (name: string, content: string | Buffer): boolean => {
    const path = join(dir, name);
    if (existsSync(path)) {
      result.kept.push(name);
      return false;
    }
    writeFileSync(path, content, { mode: 0o600, flag: 'wx' });
    chmodSync(path, 0o600);
    result.created.push(name);
    return true;
  };

  result.created.push(...ensureCertificates({ dir }));
  write(names.ca, readFileSync(join(dir, CA_CERT)));

  for (const [index, entry] of names.enrollment.entries()) {
    const material = `soorma_em_${key256()}`;
    if (!write(entry.secret, `${material}\n`)) continue;
    const file = join(dir, 'handover', `first-admin-${index + 1}.txt`);
    writeFileSync(
      file,
      `principal: ${entry.principal}\nenrollmentMaterial: ${material}\n` +
        '# Use once at first authentication, then delete this file.\n',
      { mode: 0o600 },
    );
    result.handover.push(file);
  }

  // Each environment's secrets (U4): Ed25519 keys first, then the derived
  // public halves, then the passwords and keys of 256 bits.
  const ed25519 = (): string =>
    generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' });
  const environmentNames = new Set<string>();
  for (const env of names.environments) {
    for (const name of env.ed25519) write(name, ed25519());
    const caller = env.caller;
    const spki = createPublicKey(createPrivateKey(readFileSync(join(dir, caller)))).export({
      format: 'pem',
      type: 'spki',
    });
    for (const name of env.callerPublic) {
      if (!write(name, spki) && readFileSync(join(dir, name), 'utf8') !== spki)
        throw new Error(`${name} does not match ${caller}: remove it and run stack:init again`);
    }
    const superuser = `${env.environment}-db-superuser-password`;
    for (const name of [env.logPseudonym, env.databasePassword, env.migratorPassword, superuser])
      write(name, `${key256()}\n`);
    for (const name of [...env.controlGateway, ...env.migrator, ...env.callerPublic, superuser])
      environmentNames.add(name);
  }

  const handled = new Set([
    ...names.tls,
    names.ca,
    ...names.enrollment.map((e) => e.secret),
    ...environmentNames,
  ]);
  for (const name of new Set([...names.gateway, ...names.migrator, ...STACK_ONLY])) {
    if (handled.has(name)) continue;
    write(
      name,
      name === names.signing
        ? generateKeyPairSync('ed25519').privateKey.export({ format: 'pem', type: 'pkcs8' })
        : `${key256()}\n`,
    );
  }
  return result;
}

if (import.meta.main) {
  const result = stackInit();
  console.log(`Created: ${result.created.join(', ') || 'nothing'}`);
  console.log(`Kept (never overwritten): ${result.kept.join(', ') || 'nothing'}`);
  for (const file of result.handover)
    console.log(`First Admin handover (use once, then delete): ${relative(process.cwd(), file)}`);
}
